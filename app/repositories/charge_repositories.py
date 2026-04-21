"""
This file contains all charge releated used repositories.
"""
from loguru import logger
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.project_take_off_sheets import ProjectTakeOffSheets
from repositories.update_stats_repositories import calulate_adons, update_area_item_stats, update_section_stats, update_take_off_sheet_stats, update_raw_material_stats
from models.opening_schedules import OpeningSchedules
from models.project_materials import ProjectMaterials
from models.sections import Sections
from models.project_raw_materials import ProjectRawMaterials
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.project_materials import ProjectMaterials
from models.raw_materials import RawMaterials
from sqlalchemy import or_, and_, update, func, text, case




    
    
async def update_installtion_stats(db, take_off_sheet_id, project_id):
    try:

        inst_raw_mat_data = db.query(RawMaterials).filter(RawMaterials.code == "INST").first()
        area_items = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_sheet_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False,
                ProjectTakeOffSheetSectionAreaItems.installation_charge != None
            )
            .all()
        )
        if len(area_items) > 0:
            processed_area_item_ids = []
            insert_data = []
            update_data = []
            # prepare the installation adon charges
            install_summary_data = (
                db.query(ProjectRawMaterials)
                .filter(
                    ProjectRawMaterials.raw_material_id == inst_raw_mat_data.id,
                    ProjectRawMaterials.project_id == project_id
                )
                .first()
            )
            surcharge = None
            surcharge_type = None
            markup = None
            if install_summary_data:
                markup = install_summary_data.markup
                surcharge = install_summary_data.surcharge
                surcharge_type = install_summary_data.surcharge_type
            for area_item in area_items:
                # print("processing:: ",area_item.installation_charge)
                if area_item.installation_charge is not None:
                    total_amount = area_item.installation_charge
                    quantity = 1
                    total_base_amount = total_amount
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
                    old_opening_data = (
                        db.query(OpeningSchedules)
                        .filter(
                            OpeningSchedules.is_active == True,
                            OpeningSchedules.project_take_off_sheet_section_area_item_id == area_item.id,
                            OpeningSchedules.raw_material_id == inst_raw_mat_data.id,
                            OpeningSchedules.component == "OTHER"
                        )
                        .first()
                    )
                    processed_area_item_ids.append(area_item.id)
                    if old_opening_data:
                        update_data.append({
                            "id": old_opening_data.id,
                            "component": 'OTHER',
                            "total_amount": total_amount,
                            "total_base_amount": total_base_amount,
                            "total_sell_amount": total_sell_amount,
                            "total_extended_sell_amount": total_extended_sell_amount,
                            "quantity": quantity,
                            "final_amount": total_amount,
                            "final_base_amount": total_base_amount,
                            "final_sell_amount": total_sell_amount,
                            "final_extended_sell_amount": total_extended_sell_amount,
                            "raw_material_id": inst_raw_mat_data.id,
                            "project_take_off_sheet_section_area_item_id": area_item.id,
                            "project_id": project_id,
                        })
                    else:
                        curr_data = {
                            "component": 'OTHER',
                            "total_amount": total_amount,
                            "total_base_amount": total_base_amount,
                            "total_sell_amount": total_sell_amount,
                            "total_extended_sell_amount": total_extended_sell_amount,
                            "quantity": quantity,
                            "final_amount": total_amount,
                            "final_base_amount": total_base_amount,
                            "final_sell_amount": total_sell_amount,
                            "final_extended_sell_amount": total_extended_sell_amount,
                            "raw_material_id": inst_raw_mat_data.id,
                            "project_take_off_sheet_section_area_item_id": area_item.id,
                            "project_id": project_id,
                        }
                        insert_data.append(OpeningSchedules(**curr_data))
            if len(update_data) > 0:
                # Bulk update
                db.bulk_update_mappings(OpeningSchedules, update_data)
                db.flush()

            if len(insert_data) > 0:
                # Bulk Insert
                db.bulk_save_objects(insert_data)
                db.flush()
            
            db.flush()
            for take_off_sheet_section_area_item_id in processed_area_item_ids:
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

                #update the sheet stats after deleting the section area and its associated openings
                await update_take_off_sheet_stats(db,project_take_off_sheet_id= take_off_sheet_id)

                #update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(db,project_id= project_id)
        else:
            # If there is last record for a project then the record will be deleted
            (
                db.query(ProjectRawMaterials)
                .filter(
                    ProjectRawMaterials.project_id == project_id,
                    ProjectRawMaterials.raw_material_id == inst_raw_mat_data.id,
                )
                .delete()
            ) 
        db.flush()

    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")




async def get_installtion_stats(db, take_off_sheet_id):
    try:
        stat = {}
        found = None
        inst_raw_mat_data = db.query(RawMaterials).filter(RawMaterials.code == "INST").first()
        area_item_inst_charge_data = (
            db.query(ProjectTakeOffSheetSectionAreaItems.id)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_sheet_id,
                ProjectTakeOffSheetSectionAreaItems.installation_charge != None,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False,
            )
            .all()
        )
        area_item_inst_charge_ids = [row[0] for row in area_item_inst_charge_data]
        if len(area_item_inst_charge_ids) > 0:
            opening_data = (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.project_take_off_sheet_section_area_item_id.in_(area_item_inst_charge_ids)
                )
            )
            install_data = (
                db.query(
                    func.sum(OpeningSchedules.total_amount).label("total_amount"),
                    func.sum(OpeningSchedules.total_base_amount).label("total_base_amount"),
                    func.sum(OpeningSchedules.total_sell_amount).label("total_sell_amount"),
                    func.sum(OpeningSchedules.total_extended_sell_amount).label("total_extended_sell_amount"),
                    func.sum(OpeningSchedules.quantity).label("quantity"),
                    func.sum(OpeningSchedules.final_amount).label("final_amount"),
                    func.sum(OpeningSchedules.final_base_amount).label("final_base_amount"),
                    func.sum(OpeningSchedules.final_sell_amount).label("final_sell_amount"),
                    func.sum(OpeningSchedules.final_extended_sell_amount).label("final_extended_sell_amount"),
                ).filter(
                    OpeningSchedules.is_active == True,
                    OpeningSchedules.project_take_off_sheet_section_area_item_id.in_(area_item_inst_charge_ids),
                    OpeningSchedules.raw_material_id == inst_raw_mat_data.id,
                    OpeningSchedules.component == "OTHER"
                ).first()
            )
            stat = {
                "total_amount": install_data[0],
                "total_base_amount": install_data[1],
                "total_sell_amount": install_data[2],
                "total_extended_sell_amount": install_data[3],
                "quantity": install_data[4],
                "final_amount": install_data[5],
                "final_base_amount": install_data[6],
                "final_sell_amount": install_data[7],
                "final_extended_sell_amount": install_data[8]
            }
        # stat_data = {
        #     "final_amount": install_data[1] if install_data[1] is not None else 0,
        #     "final_base_amount": install_data[1] if install_data[1] is not None else 0,
        #     "final_sell_amount": install_data[1] if install_data[1] is not None else 0,
        #     "final_extended_sell_amount": install_data[1] if install_data[1] is not None else 0,
        #     "quantity": install_data[0],
        #     "markup": 0.0,
        #     "margin": 0.0,
        #     "discount": 0.0,
        #     "surcharge": 0.0,
        #     "category": 'OTHER',
        #     "discount_type": 'FLAT',
        #     "surcharge_type": 'FLAT'
        # }
        # print("stat_data", stat_data)
        return stat
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")