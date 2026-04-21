"""
This file contains all the database operations related to update different statistics.
"""
from loguru import logger
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_sections import ProjectTakeOffSheetSections
from models.opening_schedules import OpeningSchedules
from models.project_raw_materials import ProjectRawMaterials
from models.hardware_groups import HardwareGroups
from models.hardware_group_materials import HardwareGroupMaterials
from models.project_materials import ProjectMaterials
from models.raw_materials import RawMaterials
from models.section_raw_materials import SectionRawMaterials
from models.sections import Sections
from sqlalchemy import or_, and_, update, func, text, case
from repositories.material_repositories import update_material_charges


def convert_margin_to_markup(margin: float):
    return round(margin / (1-margin), 2)

def convert_markup_to_margin(markup: float):
    return round(markup / (1+markup), 2)


async def calulate_adons(total_amount, amount, type="FLAT"):
    try:
        total_amount = total_amount if total_amount is not None else 0
        amount = amount if amount is not None else 0
        if type == "FLAT":
            return amount
        elif type == "PERCENTAGE":
            return total_amount * amount
        elif type == "MULTIPLIER":
            return total_amount * (1 - amount)
        else:
            return 0.0
    except Exception as error:
        print(error)
        raise error

async def update_opening_schedule_stats(db, hardware_group_id=None):
    """
    Update statistics for either a hardware group
    by calculating and updating the total cost, quantity, and amount for each opening
    associated with the hardware group.

    The function first fetches the data for the hardware group.
    Then it calculates the total cost, quantity, and amount for each opening associated
    with the hardware group by summing up the costs, quantities, and
    amounts of each opening.

    After that, it updates the hardware group data with the calculated
    values and also updates the opening data associated with the hardware group with the calculated values.

    The function catches and handles any exceptions that may occur while executing the
    code and rolls back any database transactions in case of an error.

    **Args:**
    - db: Database session object.
    - hardware_group_id (optional): ID of the hardware group to update statistics for.
    """
    try:
        # Initialize variables for later use
        project_take_off_sheet_section_area_item_ids = []
        # Update stats based on hardware group if provided
        if hardware_group_id:
            # Fetch hardware group data
            hw_group_data = db.query(HardwareGroups).get(hardware_group_id)
            # Fetch all hardware materials associated with the hardware group
            hardware_group_materials = db.query(HardwareGroupMaterials).filter(HardwareGroupMaterials.hardware_group_id == hardware_group_id).all()

            # Calculate total item count, total quantity, and total amount for the Hardware group
            total_item = 0
            total_quantity = 0
            sum_total_amount = 0
            sum_total_sell_amount = 0
            sum_total_base_amount = 0
            sum_total_extended_sell_amount = 0
            for hardware_group_material in hardware_group_materials:
                total_item += 1
                total_quantity += hardware_group_material.quantity
                sum_total_amount += hardware_group_material.final_amount
                sum_total_sell_amount += hardware_group_material.final_sell_amount
                sum_total_base_amount += hardware_group_material.final_base_amount
                sum_total_extended_sell_amount += hardware_group_material.final_extended_sell_amount

            # Update hardware group data with calculated values of hardware materials
            hw_group_data.item_count = total_item
            hw_group_data.quantity = total_quantity
            hw_group_data.total_amount = sum_total_amount
            hw_group_data.total_sell_amount = sum_total_sell_amount
            hw_group_data.total_base_amount = sum_total_base_amount
            hw_group_data.total_extended_sell_amount = sum_total_extended_sell_amount
            db.add(hw_group_data)
            db.flush()

            # Update opening data associated with the hardware group
            opening_data = db.query(OpeningSchedules).filter(OpeningSchedules.hardware_group_id == hardware_group_id, OpeningSchedules.component == "HARDWARE").all()
            for opening in opening_data:
                # Update opening data with hardware group data
                opening.total_amount = hw_group_data.total_amount
                opening.total_base_amount = hw_group_data.total_base_amount
                opening.total_sell_amount = hw_group_data.total_sell_amount
                opening.total_extended_sell_amount = hw_group_data.total_extended_sell_amount
                opening.quantity = hw_group_data.quantity
                opening.final_amount = hw_group_data.total_amount
                opening.final_base_amount = hw_group_data.total_base_amount
                opening.final_sell_amount = hw_group_data.total_sell_amount
                opening.final_extended_sell_amount = hw_group_data.total_extended_sell_amount
                project_take_off_sheet_section_area_item_ids.append(opening.project_take_off_sheet_section_area_item_id)
                db.add(opening)
                db.flush()
            return list(set(project_take_off_sheet_section_area_item_ids))
        else:
            return project_take_off_sheet_section_area_item_ids
    except Exception as error:
        # Handle the error appropriately
        print("update_opening_schedule_stats:: An error occurred:", error)
        raise error


async def update_area_item_stats(db, project_take_off_sheet_section_area_item_id):
    """
    Update statistics related to an take off sheet area item stats
 
    This function updates the statistics related to a take off sheet area item. It does this by summing up the final amounts
    from all the opening schedules associated with the take off sheet area item. It then updates the take off sheet area item
    with the calculated values.

    Args:
        db: Database session object.
        project_take_off_sheet_section_area_item_id (str): ID of opening for which we have to update statistics.
    """
    try:
        # Update opening data associated with the hardware group
        opening_data = db.query(OpeningSchedules).filter(
            OpeningSchedules.project_take_off_sheet_section_area_item_id == project_take_off_sheet_section_area_item_id,
            OpeningSchedules.component != "OTHER"
        ).all()
        take_off_sheet_item = db.query(ProjectTakeOffSheetSectionAreaItems).filter(ProjectTakeOffSheetSectionAreaItems.id == project_take_off_sheet_section_area_item_id, ProjectTakeOffSheetSectionAreaItems.is_deleted == False).first()
        # calculate the opening total price
        take_off_sheet_section_id = take_off_sheet_item.project_take_off_sheet_section_id
        opening_quantity = take_off_sheet_item.quantity
        opening_total_amount = sum(opening_met.final_amount if opening_met.final_amount is not None else 0 for opening_met in opening_data) if len(opening_data) > 0 else 0
        opening_final_amount = opening_total_amount * opening_quantity
        opening_total_sell_amount = sum(opening_met.final_sell_amount if opening_met.final_sell_amount is not None else 0 for opening_met in opening_data) if len(opening_data) > 0 else 0
        opening_final_sell_amount = opening_total_sell_amount * opening_quantity
        opening_total_base_amount = sum(opening_met.final_base_amount if opening_met.final_base_amount is not None else 0 for opening_met in opening_data) if len(opening_data) > 0 else 0
        opening_final_base_amount = opening_total_base_amount * opening_quantity
        opening_total_extended_sell_amount = sum(opening_met.final_extended_sell_amount if opening_met.final_extended_sell_amount is not None else 0 for opening_met in opening_data) if len(opening_data) > 0 else 0
        opening_final_extended_sell_amount = opening_total_extended_sell_amount * opening_quantity

        # Update the total amount and final amount
        take_off_sheet_item.total_amount = opening_total_amount
        take_off_sheet_item.final_amount = opening_final_amount
        take_off_sheet_item.total_sell_amount = opening_total_sell_amount
        take_off_sheet_item.final_sell_amount = opening_final_sell_amount
        take_off_sheet_item.total_base_amount = opening_total_base_amount
        take_off_sheet_item.final_base_amount = opening_final_base_amount
        take_off_sheet_item.total_extended_sell_amount = opening_total_extended_sell_amount
        take_off_sheet_item.final_extended_sell_amount = opening_final_extended_sell_amount
        db.add(take_off_sheet_item)
        db.flush()

        return take_off_sheet_section_id
    except Exception as error:
        logger.exception(f"update_area_item_stats:: An unexpected error occurred: {error}")
        raise error


async def update_section_stats(db, project_take_off_sheet_section_id):
    """
    Update the total amount for a given take-off sheet section based on the sum of final amounts 
    from associated section area items.

    Args:
        db: Database session object.
        project_take_off_sheet_section_id: ID of the take-off sheet section to update.

    Returns:
        None
    """
    try:
        # Fetch the take-off sheet section item
        take_off_sheet_section_item = (
            db.query(ProjectTakeOffSheetSections)
            .filter(ProjectTakeOffSheetSections.id == project_take_off_sheet_section_id, ProjectTakeOffSheetSections.is_deleted == False)
            .first()
            )
        project_take_off_sheet_id = take_off_sheet_section_item.project_take_off_sheet_id

        # Fetch all section area items associated with the given section
        take_off_sheet_opening_sections = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_id == project_take_off_sheet_section_id,
                    ProjectTakeOffSheetSectionAreaItems.is_deleted == False)
            .all()
            )
        
        # Calculate the total amount by summing up the final amounts of all section area items
        sum_total_amount = 0
        sum_total_sell_amount = 0
        sum_total_base_amount = 0
        sum_total_extended_sell_amount = 0
        for take_off_sheet_opening_section in take_off_sheet_opening_sections:
            sum_total_amount = sum_total_amount + (take_off_sheet_opening_section.final_amount if take_off_sheet_opening_section.final_amount is not None else 0)
            sum_total_sell_amount = sum_total_sell_amount + (take_off_sheet_opening_section.final_sell_amount if take_off_sheet_opening_section.final_sell_amount is not None else 0)
            sum_total_base_amount = sum_total_base_amount + (take_off_sheet_opening_section.final_base_amount if take_off_sheet_opening_section.final_base_amount is not None else 0)
            sum_total_extended_sell_amount = sum_total_extended_sell_amount + (take_off_sheet_opening_section.final_extended_sell_amount if take_off_sheet_opening_section.final_extended_sell_amount is not None else 0)

        # Update the total amount for the take-off sheet section
        take_off_sheet_section_item.total_amount = sum_total_amount
        take_off_sheet_section_item.total_sell_amount = sum_total_sell_amount
        take_off_sheet_section_item.total_base_amount = sum_total_base_amount
        take_off_sheet_section_item.total_extended_sell_amount = sum_total_extended_sell_amount
        db.add(take_off_sheet_section_item)
        db.flush()

        # Fetch the take-off sheet section item
        take_off_sheet_section_item = (
            db.query(ProjectTakeOffSheetSections)
            .filter(ProjectTakeOffSheetSections.id == project_take_off_sheet_section_id, ProjectTakeOffSheetSections.is_deleted == False)
            .first()
            )
        return project_take_off_sheet_id
    except Exception as error:
        # Handle the error appropriately
        print("An error occurred:", error)
        raise error


async def update_take_off_sheet_stats(db, project_take_off_sheet_id):
    """
    Update statistics related to a take of sheet

    Args:
        db: Database session object.
        project_take_off_sheet_id (str): ID of Project Take off sheet for which we have to update statistics.
    """
    try:
        project_take_off_sheet_sections = db.query(ProjectTakeOffSheetSections).filter(ProjectTakeOffSheetSections.project_take_off_sheet_id == project_take_off_sheet_id).all()
        take_off_sheet = db.query(ProjectTakeOffSheets).filter(ProjectTakeOffSheets.id == project_take_off_sheet_id, ProjectTakeOffSheets.is_deleted == False).first()
        if take_off_sheet:    
            project_id = take_off_sheet.project_id
            # calculate the sheet total price
            sheet_total_sell_amount = sum(take_off_sheet_met.total_sell_amount if take_off_sheet_met.total_sell_amount is not None else 0 for take_off_sheet_met in project_take_off_sheet_sections) if len(project_take_off_sheet_sections) > 0 else 0
            sheet_total_base_amount = sum(take_off_sheet_met.total_base_amount if take_off_sheet_met.total_base_amount is not None else 0 for take_off_sheet_met in project_take_off_sheet_sections) if len(project_take_off_sheet_sections) > 0 else 0
            sheet_total_extended_sell_amount = sum(take_off_sheet_met.total_extended_sell_amount if take_off_sheet_met.total_extended_sell_amount is not None else 0 for take_off_sheet_met in project_take_off_sheet_sections) if len(project_take_off_sheet_sections) > 0 else 0

            # Update the total amount and final amount
            take_off_sheet.total_sell_amount = sheet_total_sell_amount
            take_off_sheet.total_base_amount = sheet_total_base_amount
            take_off_sheet.total_extended_sell_amount = sheet_total_extended_sell_amount
            db.add(take_off_sheet)
            db.flush()
            return project_id
        else:
            take_off_sheet_data = (
                db.query(ProjectTakeOffSheets)
                .filter(
                    ProjectTakeOffSheets.id == project_take_off_sheet_id
                )
                .first()
            )
            return take_off_sheet_data.project_id
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_installation_adon_charges(db, project_id):
    try:

        inst_raw_material_data = (
            db.query(RawMaterials)
            .filter(
                RawMaterials.code == "INST"
            )
            .first()
        )
        [take_off_sheet_id] = (
            db.query(ProjectTakeOffSheets.id)
            .filter(
                ProjectTakeOffSheets.project_id == project_id,
                ProjectTakeOffSheets.is_deleted == False
            )
            .first()
        )
        summary_data = (
            db.query(
                func.sum(ProjectTakeOffSheetSectionAreaItems.installation_charge).label("charge"),
                func.count(ProjectTakeOffSheetSectionAreaItems.id).label("quantity")
            )
            .filter(
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_sheet_id,
                ProjectTakeOffSheetSectionAreaItems.installation_charge != None,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .first()
        )
        # print("summary_data:: ",summary_data)
        if summary_data[0] is None:
            # If there is last record for a project then the record will be deleted
            (
                db.query(ProjectRawMaterials)
                .filter(
                    ProjectRawMaterials.project_id == project_id,
                    ProjectRawMaterials.raw_material_id == inst_raw_material_data.id,
                )
                .delete()
            ) 
            db.flush()
            install_summary_data = None
        else:
            install_summary_data = (
                db.query(ProjectRawMaterials)
                .filter(
                    ProjectRawMaterials.raw_material_id == inst_raw_material_data.id,
                    ProjectRawMaterials.project_id == project_id
                )
                .first()
            )
        section_id = None
        name = None
        raw_material_id = None
        surcharge_type = None
        markup = None
        surcharge = None
        margin = None
        if install_summary_data:
            surcharge_type = (
                install_summary_data.surcharge_type.value
                if install_summary_data.surcharge_type is not None and hasattr(install_summary_data.surcharge_type, "value")
                else install_summary_data.surcharge_type
            )
            markup = install_summary_data.markup
            surcharge = install_summary_data.surcharge
            margin =install_summary_data.margin
            section_id = install_summary_data.section_id
            name = install_summary_data.name
            raw_material_id = install_summary_data.raw_material_id
        else:
            section_data = (
                db.query(Sections.id, Sections.name)
                .filter(
                    Sections.code == "INST"
                )
                .first()
            )
            if section_data:
                section_id = section_data[0]
                name = section_data[1]
            raw_mat_data = (
                db.query(RawMaterials.id)
                .filter(
                    RawMaterials.code == "INST"
                )
                .first()
            )
            if raw_mat_data:
                raw_material_id = raw_mat_data[0]
        charge = summary_data[0]
        quantity = summary_data[1]
        total_base_amount = charge
        markup_charge = round(
            await calulate_adons(
                total_base_amount,
                markup,
                "PERCENTAGE"
            ),
            2
        )
        total_sell_amount = (
            (total_base_amount + markup_charge) if total_base_amount is not None else None
        )
        surcharge_charge = round(
            await calulate_adons(
                total_sell_amount,
                surcharge,
                surcharge_type
            ),
            2
        )
        total_extended_sell_amount = (
            (total_sell_amount + surcharge_charge) if total_sell_amount is not None else None
        )
        discount_type = None
        discount = None
        if charge is None:
            return None
        else:
            data = {
                "id": raw_material_id,
                "discount_type": None if discount_type is None else discount_type if isinstance(discount_type, str) else discount_type.value,
                "discount": discount,
                "section_id": section_id,
                "project_id": project_id,
                "name": name,
                "code": "INST",
                "margin": margin,
                "markup": markup,
                "surcharge_type": None if surcharge_type is None else surcharge_type if isinstance(surcharge_type, str) else surcharge_type.value,
                "surcharge": surcharge,
                "final_amount": charge,
                "final_base_amount": total_base_amount,
                "final_sell_amount": total_sell_amount,
                "final_extended_sell_amount": total_extended_sell_amount,
                "quantity": quantity,
            }
            return data
    except Exception as error:
        print(error)
        raise error

async def get_project_summary(db, project_id):
    try:
        data = []
        # Building the query for non HWD raw materials
        non_hwd_summary_qry_text = f"""
        SELECT
            rm.id AS id,
            srm.section_id AS section_id,
            rm.name AS name,
            rm.code AS code,
            os.project_id AS project_id,
            SUM(os.final_amount) AS final_amount,
            SUM(os.final_base_amount) AS final_base_amount,
            SUM(os.final_sell_amount) AS final_sell_amount,
            SUM(os.final_extended_sell_amount) AS final_extended_sell_amount,
            SUM(os.quantity) AS quantity,
            GROUP_CONCAT(DISTINCT(pm.surcharge_type)) AS surcharge_type,
            ROUND(AVG(IFNULL(pm.surcharge, 0)), 3) AS surcharge,
            GROUP_CONCAT(DISTINCT(pm.discount_type)) AS discount_type,
            ROUND(AVG(IFNULL(pm.discount, 0)), 3) AS discount,
            ROUND(AVG(IFNULL(pm.margin, 0)), 3) AS margin,
            ROUND(AVG(IFNULL(pm.markup, 0)), 3) AS markup,
            ROUND(SUM(
                CASE
                    WHEN pm.surcharge_type = 'PERCENTAGE' THEN pm.surcharge * pm.total_sell_amount
                    WHEN pm.surcharge_type = 'MULTIPLIER' THEN pm.surcharge * pm.total_sell_amount
                    ELSE 0
                END
            ), 3) AS surcharge_amount,
            ROUND(SUM(
                CASE
                    WHEN pm.discount_type = 'PERCENTAGE' THEN pm.discount * pm.total_amount
                    WHEN pm.discount_type = 'MULTIPLIER' THEN pm.discount * pm.total_amount
                    ELSE 0
                END
            ), 3) AS discount_amount
        FROM
            raw_materials AS rm
        LEFT JOIN section_raw_materials AS srm ON rm.id = srm.raw_material_id
        INNER JOIN sections as sec on sec.id = srm.section_id AND sec.code != "MXD"
        LEFT JOIN opening_schedules AS os ON rm.id = os.raw_material_id
        LEFT JOIN project_materials AS pm ON os.project_material_id = pm.id
        WHERE
            os.project_id = '{project_id}'
            AND rm.code NOT IN ('HWD', 'INST', 'OTHER')
        GROUP BY
            rm.id, rm.name, os.project_id, srm.section_id;
        """
        result = db.execute(text(non_hwd_summary_qry_text)).fetchall()
        print("result:: ",result)
        for row in result:
            data.append({
                "id": row.id,
                "name": row.name,
                "code": row.code,
                "section_id": row.section_id,
                "project_id": row.project_id,
                "final_amount": row.final_amount,
                "final_base_amount": row.final_base_amount,
                "final_sell_amount": row.final_sell_amount,
                "final_extended_sell_amount": row.final_extended_sell_amount,
                "quantity": row.quantity,
                "margin": row.margin,
                "markup": row.markup,
                "surcharge": row.surcharge,
                "surcharge_amount": row.surcharge_amount,
                "surcharge_type": row.surcharge_type,
                "discount": row.discount,
                "discount_amount": row.discount_amount,
                "discount_type": row.discount_type,
            })
        # Building the query for HWD raw materials
        hwd_summary_query_txt = f"""
        SELECT 
            id,
            section_id,
            name,
            code,
            project_id,
            SUM(final_amount) AS final_amount,
            SUM(final_base_amount) AS final_base_amount,
            SUM(final_sell_amount) AS final_sell_amount,
            SUM(final_extended_sell_amount) AS final_extended_sell_amount,
            SUM(quantity) AS quantity,
            AVG(margin) AS margin,
            AVG(markup) AS markup,
			ROUND(AVG(IFNULL(discount_amount, 0)), 3) AS discount_amount,
			ROUND(SUM(IFNULL(surcharge_amount, 0)), 3) AS surcharge_amount,
			GROUP_CONCAT(DISTINCT(surcharge_type)) AS surcharge_type,
			ROUND(AVG(IFNULL(surcharge, 0)), 3) AS surcharge,
			GROUP_CONCAT(DISTINCT(discount_type)) AS discount_type,
			ROUND(AVG(IFNULL(discount, 0)), 3) AS discount
        FROM (
            -- Detailed selection and calculations for each material
            SELECT
                rm.id AS id,
                srm.section_id AS section_id,
                rm.name AS name,
                rm.code AS code,
                os.project_id AS project_id,
                pts.id AS area_item_id,
                MAX(os.final_amount) AS final_amount,
                MAX(os.final_base_amount) AS final_base_amount,
                MAX(os.final_sell_amount) AS final_sell_amount,
                MAX(os.final_extended_sell_amount) AS final_extended_sell_amount,
                MAX(os.quantity) AS quantity,
				GROUP_CONCAT(DISTINCT(pm.surcharge_type)) AS surcharge_type,
				ROUND(AVG(IFNULL(pm.surcharge, 0)), 3) AS surcharge,
				GROUP_CONCAT(DISTINCT(pm.discount_type)) AS discount_type,
				ROUND(AVG(IFNULL(pm.discount, 0)), 3) AS discount,
                ROUND(AVG(IFNULL(pm.margin, 0)), 2) AS margin,
                ROUND(AVG(IFNULL(pm.markup, 0)), 2) AS markup,
                ROUND(MAX(
                    CASE
                        WHEN pm.surcharge_type = 'PERCENTAGE' THEN pm.surcharge * pm.total_sell_amount
                        WHEN pm.surcharge_type = 'MULTIPLIER' THEN pm.surcharge * pm.total_sell_amount
                        ELSE 0
                    END
                ), 2) AS surcharge_amount,
                ROUND(MAX(
                    CASE
                        WHEN pm.discount_type = 'PERCENTAGE' THEN pm.discount * pm.total_amount
                        WHEN pm.discount_type = 'MULTIPLIER' THEN pm.discount * pm.total_amount
                        ELSE 0
                    END
                ), 2) AS discount_amount
            FROM
                project_take_off_sheet_section_area_items pts
            JOIN opening_schedules os ON os.project_take_off_sheet_section_area_item_id = pts.id
            JOIN hardware_group_materials hgm ON os.hardware_group_id = hgm.hardware_group_id
            JOIN project_materials pm ON hgm.project_material_id = pm.id
            JOIN raw_materials rm ON rm.id = pm.raw_material_id
            JOIN section_raw_materials srm ON rm.id = srm.raw_material_id
            WHERE
                pts.is_active = TRUE
                AND pts.is_deleted = FALSE
                AND os.project_id = '{project_id}'
                AND rm.code IN ('HWD')
            GROUP BY
                rm.id, rm.name, os.project_id, srm.section_id, pts.id
            ) AS temp_view
        GROUP BY
            id, name, project_id, section_id;
        """

        results = db.execute(text(hwd_summary_query_txt)).fetchall()

        # Process the results into the format you need
        for row in results:
            data.append({
                "id": row.id,
                "name": row.name,
                "code": row.code,
                "section_id": row.section_id,
                "project_id": row.project_id,
                "final_amount": row.final_amount,
                "final_base_amount": row.final_base_amount,
                "final_sell_amount": row.final_sell_amount,
                "final_extended_sell_amount": row.final_extended_sell_amount,
                "quantity": row.quantity,
                "margin": row.margin,
                "markup": row.markup,
                "surcharge": row.surcharge,
                "surcharge_amount": row.surcharge_amount,
                "surcharge_type": row.surcharge_type,
                "discount": row.discount,
                "discount_amount": row.discount_amount,
                "discount_type": row.discount_type,
            })
        # Building the query for INST raw materials
        installation_charge = await get_installation_adon_charges(db, project_id)
        # print("installation_charge:: ",installation_charge)
        if installation_charge is not None:
            data.append(installation_charge)
        return data
    except Exception as error:
        print(error)
        raise error

async def update_raw_material_stats(db, project_id=None):
    """
    Update statistics related to hardware groups or project materials.
    It updates each opening's `total_amount`, `final_amount`, `total_base_amount`, `total_sell_amount`, `final_base_amount`, `final_sell_amount`, `item_count`:
        By summing up all the projectMaterials and/or hardwareMaterials in the respective opening.

    **Args:**
    - db: Database session object.
    - hardware_group_id (optional): ID of the hardware group to update statistics for.
    - project_material_id (optional): ID of the project material to update statistics for.
    """
    try:
        mixed_section = (
            db.query(Sections)
            .filter(Sections.code == "MXD")
            .first()
        )
        if mixed_section:
            take_off_data = (
                db.query(ProjectTakeOffSheets)
                .filter(ProjectTakeOffSheets.project_id == project_id)
                .first()
            )
            if take_off_data:
                    take_off_item_data = (
                        db.query(ProjectTakeOffSheetSectionAreaItems)
                        .filter(
                            ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_data.id,
                            ProjectTakeOffSheetSectionAreaItems.is_deleted == False
                        )
                        .first()
                    )
                    if take_off_item_data:
                        results = await get_project_summary(db, project_id)
                        # print("---------------------------")
                        # print("results:: ",results)
                        # print("---------------------------")
                        if len(results) > 0:
                            found_project_material_ids = []
                            for project_raw_material in results:
                                found_project_material_ids.append(project_raw_material["id"])
                                if project_raw_material["code"] == "INST":
                                    adon_data = await get_installation_adon_charges(db, project_id)
                                    if adon_data is not None:
                                        project_raw_material["markup"] = adon_data["markup"]
                                        project_raw_material["margin"] = adon_data["margin"]
                                        project_raw_material["surcharge"] = adon_data["surcharge"]
                                        project_raw_material["discount"] = adon_data["discount"]
                                        project_raw_material["discount_type"] = adon_data["discount_type"]
                                        project_raw_material["surcharge_type"] = adon_data["surcharge_type"]
                                        project_raw_material["final_amount"] = adon_data["final_amount"]
                                        project_raw_material["final_base_amount"] = adon_data["final_base_amount"]
                                        project_raw_material["final_sell_amount"] = adon_data["final_sell_amount"]
                                        project_raw_material["final_extended_sell_amount"] = adon_data["final_extended_sell_amount"]
                                        project_raw_material["id"] = adon_data["id"]
                                    else:
                                        continue
                                existing_record = db.query(ProjectRawMaterials).filter_by(raw_material_id=project_raw_material["id"], project_id=project_id).first()
                                if existing_record:
                                    # If the record exists, update it
                                    existing_record.name = project_raw_material["name"]
                                    existing_record.section_id = project_raw_material["section_id"]
                                    existing_record.final_amount = project_raw_material["final_amount"]
                                    existing_record.final_base_amount = project_raw_material["final_base_amount"]
                                    existing_record.final_sell_amount = project_raw_material["final_sell_amount"]
                                    existing_record.final_extended_sell_amount = project_raw_material["final_extended_sell_amount"]
                                    existing_record.quantity = project_raw_material["quantity"]
                                    existing_record.margin = project_raw_material["margin"]
                                    existing_record.markup = project_raw_material["markup"]
                                    existing_record.surcharge = project_raw_material["surcharge"]
                                    existing_record.discount = project_raw_material["discount"]
                                    if "surcharge_amount" in project_raw_material:
                                        existing_record.surcharge_amount = project_raw_material["surcharge_amount"]
                                    if "surcharge_type" in project_raw_material:
                                        existing_record.surcharge_type = project_raw_material["surcharge_type"]
                                    if "discount_amount" in project_raw_material:
                                        existing_record.discount_amount = project_raw_material["discount_amount"]
                                    if "discount_type" in project_raw_material:
                                        existing_record.discount_type = project_raw_material["discount_type"]
                                    db.add(existing_record)
                                    db.flush()
                                else:
                                    if "surcharge_type" in project_raw_material:
                                        surcharge_type = project_raw_material["surcharge_type"]
                                    else:
                                        surcharge_type = None
                                    if "discount_type" in project_raw_material:
                                        discount_type = project_raw_material["discount_type"]
                                    else:
                                        discount_type = None
                                    if "discount_amount" in project_raw_material:
                                        discount_amount = project_raw_material["discount_amount"]
                                    else:
                                        discount_amount = 0
                                    if "surcharge_amount" in project_raw_material:
                                        surcharge_amount = project_raw_material["surcharge_amount"]
                                    else:
                                        surcharge_amount = 0
                                    if "surcharge" in project_raw_material:
                                        surcharge = project_raw_material["surcharge"]
                                    else:
                                        surcharge = 0
                                    if "discount" in project_raw_material:
                                        discount = project_raw_material["discount"]
                                    else:
                                        discount = 0
                                    new_project_raw_material = ProjectRawMaterials(
                                        section_id=project_raw_material["section_id"],
                                        raw_material_id=project_raw_material["id"],
                                        name=project_raw_material["name"],
                                        project_id=project_raw_material["project_id"],
                                        final_amount=project_raw_material["final_amount"],
                                        final_base_amount=project_raw_material["final_base_amount"],
                                        final_sell_amount=project_raw_material["final_sell_amount"],
                                        final_extended_sell_amount=project_raw_material["final_extended_sell_amount"],
                                        quantity=project_raw_material["quantity"],
                                        margin=project_raw_material["margin"],
                                        markup=project_raw_material["markup"],
                                        surcharge=surcharge,
                                        discount=discount,
                                        surcharge_amount=surcharge_amount,
                                        discount_amount=discount_amount,
                                        surcharge_type=surcharge_type,
                                        discount_type=discount_type,
                                    )
                                    # If the record doesn't exist, insert it
                                    db.add(new_project_raw_material)
                                    db.flush()
                            # Delete those raw materials if those are not in use
                            db.query(ProjectRawMaterials).filter( ProjectRawMaterials.raw_material_id.notin_(found_project_material_ids),ProjectRawMaterials.project_id == project_id).delete() 
                        else:
                            # If there is last record for a project then the record will be deleted
                            db.query(ProjectRawMaterials).filter(ProjectRawMaterials.project_id == project_id).delete() 
                    else:  
                        # If there is last record for a project then the record will be deleted
                        db.query(ProjectRawMaterials).filter(ProjectRawMaterials.project_id == project_id).delete() 
            else:
                # If there is last record for a project then the record will be deleted
                db.query(ProjectRawMaterials).filter(ProjectRawMaterials.project_id == project_id).delete()


    except Exception as error:
        # Handle the error appropriately
        print("An error occurred:", error)
        raise error



async def update_project_stats(db, project_maretials_data):
    """
    Adds a discount to a project quote.
 
    Args:
        db: Database session object.
        project_maretials_data (dict): Project materials data that has to be updated for updated price information and
        its affected stats throughout the porject.
    """
    try:
        project_material_updated_hw_ids = []
        project_material_updated_non_hw_area_item_ids = []
        for row in project_maretials_data:
            updated_values = await update_material_charges(db, row.id, return_updated_values=True)
            row = db.query(ProjectMaterials).get(row.id)
            if row.material_type.value == "HARDWARE":
                hw_group_material_datas = db.query(HardwareGroupMaterials).filter(HardwareGroupMaterials.project_material_id == row.id).all()
                if len(hw_group_material_datas) > 0:
                    for hw_group_material_data in hw_group_material_datas:
                        hw_group_material_data.total_amount = updated_values["total_amount"]
                        hw_group_material_data.total_sell_amount = updated_values["total_sell_amount"]
                        hw_group_material_data.total_base_amount = updated_values["total_base_amount"]
                        hw_group_material_data.total_extended_sell_amount = updated_values["total_extended_sell_amount"]
                        hw_group_material_data.final_amount = hw_group_material_data.quantity * updated_values["total_amount"]
                        hw_group_material_data.final_sell_amount = hw_group_material_data.quantity * updated_values["total_sell_amount"]
                        hw_group_material_data.final_base_amount = hw_group_material_data.quantity * updated_values["total_base_amount"]
                        hw_group_material_data.final_extended_sell_amount = hw_group_material_data.quantity * updated_values["total_extended_sell_amount"]
                        db.add(hw_group_material_data)
                        db.flush()
                    project_material_updated_hw_ids.append(row.id)
            else:
                opening_data = db.query(OpeningSchedules).filter(OpeningSchedules.project_material_id == row.id).first()
                if opening_data:
                    opening_data.total_amount = updated_values["total_amount"]
                    opening_data.total_sell_amount = updated_values["total_sell_amount"]
                    opening_data.total_base_amount = updated_values["total_base_amount"]
                    opening_data.total_extended_sell_amount = updated_values["total_extended_sell_amount"]
                    opening_data.final_amount = opening_data.quantity * updated_values["total_amount"]
                    opening_data.final_sell_amount = opening_data.quantity * updated_values["total_sell_amount"]
                    opening_data.final_base_amount = opening_data.quantity * updated_values["total_base_amount"]
                    opening_data.final_extended_sell_amount = opening_data.quantity * updated_values["total_extended_sell_amount"]
                    db.add(opening_data)
                    db.flush()
                    project_material_updated_non_hw_area_item_ids.append(opening_data.project_take_off_sheet_section_area_item_id)

        project_material_updated_non_hw_area_item_ids = list(set(project_material_updated_non_hw_area_item_ids))
        # print("project_material_updated_hw_ids:: ",project_material_updated_hw_ids)
        # list affected hardware groups
        affected_hw_groups = (
            db.query(HardwareGroupMaterials)
            .filter(
                HardwareGroupMaterials.project_material_id.in_(project_material_updated_hw_ids)
            )
        )
        affected_hw_group_ids = []
        for hw_group in affected_hw_groups:
            affected_hw_group_ids.append(hw_group.hardware_group_id)
        affected_hw_group_ids = list(set(affected_hw_group_ids))

        # update stats of all affected hw groups
        for hw_group_id in affected_hw_group_ids:
            # Update opening scedule statistics related to the hardware group
            take_off_sheet_section_area_item_ids = await update_opening_schedule_stats(
                db, 
                hardware_group_id = hw_group_id
            )

            for take_off_sheet_section_area_item_id in take_off_sheet_section_area_item_ids:
                # Update area item statistics related to the hardware group
                take_off_sheet_section_id = await update_area_item_stats(
                    db,
                    project_take_off_sheet_section_area_item_id = take_off_sheet_section_area_item_id
                )
                
                # Update section statistics related to the hardware group
                await update_section_stats(
                    db,
                    project_take_off_sheet_section_id = take_off_sheet_section_id
                )

        # update stats of all affected non hw groups
        for project_material_updated_non_hw_area_item_id in project_material_updated_non_hw_area_item_ids:
            # Update area item statistics related to the hardware group
            take_off_sheet_section_id = await update_area_item_stats(
                db,
                project_take_off_sheet_section_area_item_id = project_material_updated_non_hw_area_item_id
            )
        
            # Update section statistics related to the hardware group
            await update_section_stats(
                db,
                project_take_off_sheet_section_id = take_off_sheet_section_id
            )

        project_take_off_data = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.project_id == project_maretials_data[0].project_id
            )
            .first()
        )
        
        #update the sheet stats after deleting the section area and its associated openings
        await update_take_off_sheet_stats(db,project_take_off_sheet_id= project_take_off_data.id)

        #update the raw material stats after deleting the section area and its associated openings
        await update_raw_material_stats(db,project_id= project_take_off_data.project_id)

        return True
    except Exception as e:
        print("update_project_stats:: error - ",e)
        raise e

