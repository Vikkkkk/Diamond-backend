"""
This file contains all operations related to take-off sheet estimation.
"""
import json
import traceback
from typing import List
from loguru import logger
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_sections import ProjectTakeOffSheetSections
from models.project_take_off_sheet_section_areas import ProjectTakeOffSheetSectionAreas
from models.project_take_off_sheet_charges import ProjectTakeOffSheetCharges
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.project_raw_material_manufacturer_quotes import ProjectRawMaterialManufacturerQuotes
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.manufacturers import Manufacturers
from models.opening_schedules import OpeningSchedules
from models.raw_materials import RawMaterials
from models.hardware_group_materials import HardwareGroupMaterials
from models.project_materials import ProjectMaterials, MATERIAL_TYPE
from models.sections import Sections
from models.projects import Projects
from models.project_raw_materials import ProjectRawMaterials
from models.project_take_of_sheet_notes import ProjectTakeOffSheetNotes
from models.brands import Brands
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, and_, update, case, func
from repositories.update_stats_repositories import get_installation_adon_charges, calulate_adons, convert_margin_to_markup, convert_markup_to_margin, get_project_summary, update_project_stats, update_area_item_stats, update_take_off_sheet_stats, update_raw_material_stats
from repositories.take_off_sheet_repositories import get_installed_raw_materials
from repositories.common_repositories import get_total_adon_price
from repositories.charge_repositories import get_installtion_stats
from utils.common import generate_uuid, delete_file, save_uploaded_file, format_project_code
from fastapi.responses import JSONResponse, FileResponse
import math
from datetime import date, datetime, timedelta
from utils.common import get_user_time
import sys
from fastapi import HTTPException
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session
from schemas.take_off_sheet_estimation_schemas import EstimationBreakdown
from schemas.take_off_sheet_estimation_schemas import EstimationSurcharge 
from schemas.take_off_sheet_estimation_schemas import EstimationDiscount
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from models.members import Members
from utils.common import upload_to_s3, delete_from_s3
import os


async def get_all_sections(db: Session, project_id: str):
    """**Summary:**
    Retrieve information about all sections in a project's take-off sheet.

    **Args:**
    - db (Database Session): The SQLAlchemy database session.
    - project_id (int): The ID of the project.

    **Returns:**
        dict: A dictionary containing the retrieved data and status.
            - 'data' (list): List of dictionaries with section information.
                Each dictionary contains:
                - 'project_take_off_sheet_section_id' (int): ID of the section.
                - 'section' (str): Name of the section.
                - 'item_count' (int): Number of items in the section.
                - 'final_amount' (float): Final amount, if applicable.
            - 'status' (str): Status of the operation ('success' or other).
    """
    take_off_sheet_data = (
        db.query(ProjectTakeOffSheets)
        .filter(
            ProjectTakeOffSheets.is_deleted == False,
            ProjectTakeOffSheets.project_id == project_id,
        )
        .first()
    )
    project_take_off_sheet_sections = (
        db.query(ProjectTakeOffSheetSections)
        .join(Sections)
        .filter(
            ProjectTakeOffSheetSections.is_deleted == False,
            ProjectTakeOffSheetSections.project_take_off_sheet_id == take_off_sheet_data.id,
            Sections.is_deleted == False
        )
        .order_by(ProjectTakeOffSheetSections.created_at.asc())
        .all()
    )    
    data = []
    for sheet_section in project_take_off_sheet_sections:
        res = {"section": "", "item_count": 0, "final_amount": 0.0}
        res['project_take_off_sheet_section_id'] = sheet_section.id
        res['section'] = sheet_section.section.name
        res['section_code'] = sheet_section.section.code
        res['section_number'] = sheet_section.section.item_number
        # calculationg the section item count
        item_data = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_id == sheet_section.id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .order_by(ProjectTakeOffSheetSectionAreaItems.created_at.asc())
            .all()
        )
        if item_data:
            res['item_count'] = len(item_data)
            final_amount = 0
            for item in item_data:
                total_extended_sell_amount = item.total_extended_sell_amount if item.total_extended_sell_amount is not None else 0
                final_amount = final_amount + total_extended_sell_amount

            res['final_amount'] = round(final_amount, 2)
            data.append(res)
    return {"data": data, "status": "success"} 


async def get_opening_items_summary(
    db: Session, 
    project_id: str, 
    project_take_off_sheet_section_area_item_id: str
):
    """
    Retrieves the summary of opening items for a specific project's opening(TakeOffSheetAreaItem).
    It also calculates discountAmount based on the discount type

    Args:
        db (Session): The database session object.
        project_id (int): The ID of the project.
        project_take_off_sheet_section_area_item_id (int): The ID of the project take off sheet section area item.

    Returns:
        dict: A dictionary containing the data and status of the response. The data key contains a list of dictionaries
        representing the opening project materials, each with the discount amount. The status key indicates the success or
        failure of the operation.

    Raises:
        Exception: If an error occurs during the retrieval process.
    """
    try:
        
        non_hwd_query_text = f"""
        SELECT 
            pm.material_type,
            AVG(pm.markup) AS avg_markup,
            SUM(
                CASE 
                    WHEN pm.discount_type = 'PERCENTAGE' THEN ROUND(IFNULL(pm.total_amount * pm.discount, 0), 2)
                    WHEN pm.discount_type = 'MULTIPLIER' THEN ROUND(IFNULL(pm.total_amount * (1 - pm.discount), 0), 2)
                    ELSE 0
                END
            ) AS discount_amount,
            SUM(os.final_sell_amount - os.final_base_amount) AS markup_amount,
            SUM(os.final_extended_sell_amount - os.final_sell_amount) AS surcharge_amount,
            AVG(os.quantity) AS quantity,
            SUM(os.final_amount) AS final_amount,
            SUM(os.final_base_amount) AS final_base_amount,
            SUM(os.final_sell_amount) AS final_sell_amount,
            SUM(os.final_extended_sell_amount) AS final_extended_sell_amount,
            MAX(pm.created_at) AS most_recent_creation
        FROM 
            project_take_off_sheet_section_area_items pts
        LEFT JOIN opening_schedules os ON os.project_take_off_sheet_section_area_item_id = pts.id
        JOIN project_materials pm ON os.project_material_id = pm.id
        WHERE 
            pts.id = '{project_take_off_sheet_section_area_item_id}'
        GROUP BY
            pm.material_type, os.id
        ORDER BY 
            pm.material_type DESC, most_recent_creation DESC;

        """
        results = db.execute(text(non_hwd_query_text)).fetchall()
        # Process results to mimic the desired output structure
        resp = []
        doors_found = 0
        for result in results:
            material_type, avg_markup, discount_amount, markup_amount, surcharge_amount, quantity, final_amount, final_base_amount, final_sell_amount, final_extended_sell_amount, most_recent_creation = result
            row_data = {'material_type': material_type, "markup": avg_markup, "markup_amount": markup_amount}
            if material_type == "DOOR":
                doors_found += 1
                row_data["material_name"] = f"{material_type} {doors_found}"
            else:
                row_data["material_name"] = f"{material_type}"
            row_data['discount_amount'] = discount_amount
            row_data['surcharge_amount'] = surcharge_amount
            row_data['quantity'] = quantity
            row_data['final_amount'] = final_amount
            row_data['final_base_amount'] = final_base_amount
            row_data['final_sell_amount'] = final_sell_amount
            row_data['final_extended_sell_amount'] = final_extended_sell_amount
            resp.append(row_data)


        hw_query_text = f"""
        SELECT
            ROUND(MAX(og.total_amount), 2) AS final_amount,
            ROUND(MAX(og.total_base_amount), 2) AS final_base_amount,
            ROUND(MAX(og.total_sell_amount), 2) AS final_sell_amount,
            ROUND(AVG(pm.markup), 2) AS markup,
            ROUND(MAX(og.total_amount) - MAX(og.total_base_amount), 2) AS discount_amount,
            ROUND(MAX(os.final_sell_amount) - MAX(os.final_base_amount), 2) AS markup_amount,
            ROUND(MAX(os.final_extended_sell_amount) - MAX(os.final_sell_amount), 2) AS surcharge_amount,
            ROUND(MAX(og.total_extended_sell_amount), 2) AS final_extended_sell_amount,
            ROUND(MAX(og.quantity), 2) AS quantity
        FROM
            opening_schedules AS os
        JOIN
            hardware_groups AS og ON og.id = os.hardware_group_id
        JOIN
            hardware_group_materials AS hgm ON hgm.hardware_group_id = og.id
        JOIN
            project_materials AS pm ON pm.id = hgm.project_material_id
        WHERE
            os.project_take_off_sheet_section_area_item_id = '{project_take_off_sheet_section_area_item_id}'
            AND os.component = 'HARDWARE';
        """

        result = db.execute(text(hw_query_text)).fetchone()

        if result:
            resp.append({
                "material_type": "HARDWARE",
                "material_name": "HARDWARE",
                "surcharge_amount": result.surcharge_amount,
                "final_amount": result.final_amount,
                "final_base_amount": result.final_base_amount,
                "final_sell_amount": result.final_sell_amount,
                "markup": result.markup,
                "markup_amount": result.markup_amount,
                "discount_amount": result.discount_amount,
                "final_extended_sell_amount": result.final_extended_sell_amount,
                "quantity": result.quantity
            })

        return {"data": resp, "status": "success"}
    except Exception as e:
        print(e)
        raise e


async def get_openings_summary(db: Session, project_id: str):
    """
    Retrieves the summary of each opening for a given project(which may be empty).
    It also calculates discountAmount based on the discount type & fetches markup from the db.

    Parameters:
        db (Database): The database object used for querying.
        project_id (int): The ID of the project.

    Returns:
        dict: A dictionary containing the openings summary data.

    Raises:
        Exception: If an error occurs during the retrieval process.
    """
    try:
        project_take_off_sheet_id = (
            db.query(ProjectTakeOffSheets.id)
            .filter(
                ProjectTakeOffSheets.project_id == project_id, 
                ProjectTakeOffSheets.is_deleted == False,
                ProjectTakeOffSheets.is_active == True
            ).first()
        )
        if not project_take_off_sheet_id:
            return JSONResponse(content={"message": f"Takeoff sheet not exist."}, status_code=406)
        
        project_take_off_sheet_id = project_take_off_sheet_id[0]

        query_text = """
            SELECT
                ptsai.*,
                (ptsai.final_amount - ptsai.final_base_amount) AS discount_amount,
                (ptsai.final_extended_sell_amount - ptsai.final_sell_amount) AS surcharge_amount,
                AVG(COALESCE(pm.markup, hgm.avg_markup)) AS markup,
                AVG(COALESCE(pm.margin, hgm.avg_margin)) AS margin
            FROM
                project_take_off_sheet_section_area_items ptsai
            LEFT JOIN opening_schedules os ON
                os.project_take_off_sheet_section_area_item_id = ptsai.id
                AND os.is_active = TRUE
                AND os.project_id = :project_id
            LEFT JOIN (
                SELECT
                    hgm.hardware_group_id,
                    AVG(pm.markup) AS avg_markup,
                    AVG(pm.margin) AS avg_margin
                FROM
                    hardware_group_materials hgm
                JOIN project_materials pm ON
                    hgm.project_material_id = pm.id
                    AND pm.is_active = TRUE
                    AND pm.is_deleted = FALSE
                    AND pm.project_id = :project_id
                WHERE
                    hgm.is_active = TRUE
                GROUP BY
                    hgm.hardware_group_id
            ) hgm ON
                os.hardware_group_id = hgm.hardware_group_id
            LEFT JOIN project_materials pm ON
                os.project_material_id = pm.id
                AND pm.is_active = TRUE
                AND pm.is_deleted = FALSE
                AND pm.project_id = :project_id
            WHERE
                ptsai.is_active = TRUE
                AND ptsai.is_deleted = FALSE
                AND ptsai.project_take_off_sheet_id = :project_take_off_sheet_id
            GROUP BY
                ptsai.id;
        """


        result = db.execute(
            text(query_text),
            {"project_id": project_id, "project_take_off_sheet_id": project_take_off_sheet_id}
        ).fetchall()


        resp = []
        for row in result:
            row_data = row._asdict()
            row_data["adon_fields"] = json.loads(row_data["adon_fields"])
            resp.append(row_data)

        miscellaneous_price = await get_total_adon_price(db, project_take_off_sheet_id)
        installation_adon_charge = None
        installation_charge = await get_installation_adon_charges(db, project_id)
        # print("installation_charge:: ",installation_charge)
        if installation_charge is not None:
            installation_adon_charge = {
                "final_amount": installation_charge["final_amount"],
                "final_base_amount": installation_charge["final_base_amount"],
                "final_sell_amount": installation_charge["final_sell_amount"],
                "final_extended_sell_amount": installation_charge["final_extended_sell_amount"]
            }
        return {"data": resp, "miscellaneous_price": miscellaneous_price, "installation_adon_charge": installation_adon_charge, "status": "success"}

    except Exception as e:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        raise e


async def set_estimation_breakdown(db: Session, project_id: str, request_data: EstimationBreakdown):
    """
    Set the estimation breakdown for a given project.

    Parameters:
        - db: The database connection object.
        - project_id: The ID of the project.
        - request_data: The data for the estimation breakdown.

    Returns:
        None
    """
    affected_raw_materials_ids = []
    request_data = request_data.model_dump(exclude_unset=True)
    # will be either 'margin' or 'markup'
    update_column = request_data['tab_type'].name.lower()
    if update_column == 'margin':
        # We compute the corresponding markup from the given margin
        update_column1 = 'markup'
        update_column1_data = {raw_material_code: convert_margin_to_markup(margin)   for raw_material_code, margin in request_data['data'].items()}
    elif update_column == 'markup':
        # We compute the corresponding margin from the given markup
        update_column1 = 'margin'
        update_column1_data = {raw_material_code: convert_markup_to_margin(markup)   for raw_material_code, markup in request_data['data'].items()}
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            all_raw_materials = (
                db.query(RawMaterials.id, RawMaterials.code, RawMaterials.name).all()
            )
            warning_fields = {}
            for (raw_material_id, raw_material_code, raw_material_name) in all_raw_materials:
                # print("processing:: ",raw_material_id, raw_material_code, raw_material_name)
                if raw_material_code not in request_data['data']: continue
                try:
                    percentage = request_data['data'][raw_material_code]
                    if raw_material_code == "INST":
                        stat_data = await get_installation_adon_charges(db, project_id)
                        if stat_data is not None:
                            final_sell_amount = (
                                stat_data["final_base_amount"] + 
                                await calulate_adons(
                                    stat_data["final_base_amount"],
                                    update_column1_data[raw_material_code] if update_column == 'margin' else percentage,
                                    "PERCENTAGE"
                                )
                            )
                            final_extended_sell_amount = final_sell_amount
                            data = {
                                update_column: percentage,
                                update_column1: update_column1_data[raw_material_code],
                                "final_amount":stat_data["final_amount"],
                                "final_base_amount":stat_data["final_base_amount"],
                                "final_sell_amount": final_sell_amount,
                                "final_extended_sell_amount": final_extended_sell_amount,
                                "quantity": stat_data["quantity"]
                            }
                            old_data = (
                                db.query(ProjectRawMaterials)
                                .filter(
                                    ProjectRawMaterials.raw_material_id == raw_material_id,
                                    ProjectRawMaterials.project_id == project_id,
                                )
                                .first()
                            )
                            if old_data:
                                for key, value in data.items():
                                    setattr(old_data, key, value)
                                db.flush()
                            else:
                                warning_fields[raw_material_name] = "No affected rows!"
                    else:
                        data = {
                            update_column: percentage,
                            update_column1: update_column1_data[raw_material_code]
                        }
                        # print("data:: ",data)
                        res = (
                            db.query(ProjectMaterials)
                            .filter(
                                ProjectMaterials.raw_material_id == raw_material_id,
                                ProjectMaterials.project_id == project_id,
                            )
                            .update(data)
                        )
                        db.flush()
                        if res:
                            affected_raw_materials_ids.append(raw_material_id)
                        else:
                            warning_fields[raw_material_name] = "No affected rows!"
                except Exception as e1:
                    logger.exception("set_estimation_breakdown -> for_loop: " + str(e1))

            # update the project for the breakup changes
            affected_raw_materials_ids = list(set(affected_raw_materials_ids))
            # print("affected_raw_materials_ids:: ",affected_raw_materials_ids)
            for raw_material_id in affected_raw_materials_ids:
                rows = (
                    db.query(ProjectMaterials)
                    .filter(
                        ProjectMaterials.is_deleted == False,
                        ProjectMaterials.project_id == project_id,
                        ProjectMaterials.raw_material_id == raw_material_id
                    )
                    .all()
                )
                # print("data:: ", [(elm.id, elm.markup, elm.margin) for elm in rows])
                # Update the stats in all table using update stats
                await update_project_stats(db, rows)

            if len(warning_fields) == 0:
                return {"status": "success"}
            else:
                return {"status": "success", "warning_fields": warning_fields}
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error



async def set_estimation_surcharge(db: Session, project_id: str, request_data: EstimationSurcharge):
    """
    Set estimation surcharge in the database for a specific project.

    Args:
        db: The database session.
        project_id: The ID of the project.
        request_data: The data containing surcharge information for raw materials.

    Returns:
        A dictionary with the status of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            affected_raw_materials_ids = []
            request_data = request_data.model_dump(exclude_unset=True)
            all_raw_materials = (
                db.query(RawMaterials.id, RawMaterials.code, RawMaterials.name).all()
            )
            
            warning_fields = {}
            for (raw_material_id, raw_material_code, raw_material_name) in all_raw_materials:
                if raw_material_code not in request_data['data']: continue
                try:
                    surcharge_data = request_data['data'][raw_material_code]
                    surcharge_type, surcharge = surcharge_data['surcharge_type'], surcharge_data['surcharge']
                    surcharge_type = surcharge_type if isinstance(surcharge_type, str) else surcharge_type.value
                    if raw_material_code == "INST":
                        stat_data = await get_installation_adon_charges(db, project_id)
                        if stat_data is not None:
                            final_extended_sell_amount = (
                                stat_data["final_sell_amount"] + 
                                await calulate_adons(
                                    stat_data["final_sell_amount"],
                                    surcharge,
                                    surcharge_type
                                )
                            )
                            data = {
                                "surcharge": surcharge,
                                "surcharge_type": surcharge_type,
                                "final_amount":stat_data["final_amount"],
                                "final_base_amount":stat_data["final_base_amount"],
                                "final_sell_amount": stat_data["final_sell_amount"],
                                "final_extended_sell_amount": final_extended_sell_amount,
                                "quantity": stat_data["quantity"]
                            }
                            old_data = (
                                db.query(ProjectRawMaterials)
                                .filter(
                                    ProjectRawMaterials.raw_material_id == raw_material_id,
                                    ProjectRawMaterials.project_id == project_id,
                                )
                                .first()
                            )
                            if old_data:
                                for key, value in data.items():
                                    setattr(old_data, key, value)
                                db.flush()
                            else:
                                warning_fields[raw_material_name] = "No affected rows!"
                    else:
                        data = {
                            "surcharge": surcharge,
                            "surcharge_type": surcharge_type,
                        }
                        result = (
                            db.query(ProjectMaterials)
                            .filter(
                                ProjectMaterials.raw_material_id == raw_material_id,
                                ProjectMaterials.project_id == project_id,
                            )
                            .update(data)
                        )
                        db.flush()
                        if result:
                            affected_raw_materials_ids.append(raw_material_id)
                        else:
                            warning_fields[raw_material_name] = "No affected rows!"
                except Exception as e1:
                    logger.exception("set_estimation_surcharge -> for_loop: " + str(e1))
            
            # update the project for the breakup changes
            affected_raw_materials_ids = list(set(affected_raw_materials_ids))
            for raw_material_id in affected_raw_materials_ids:
                rows = (
                    db.query(ProjectMaterials)
                    .filter(
                        ProjectMaterials.is_deleted == False,
                        ProjectMaterials.project_id == project_id,
                        ProjectMaterials.raw_material_id == raw_material_id
                    )
                    .all()
                )
                # print("data:: ", [(elm.id, elm.markup, elm.margin) for elm in rows])
                # Update the stats in all table using update stats
                await update_project_stats(db, rows)
            if len(warning_fields) == 0:
                return {"status": "success"}
            else:
                return {"status": "success", "warning_fields": warning_fields}
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def get_estimation_breakdown(db: Session, project_id: str, tab_type: str):
    """
    Asynchronously gets the estimation breakdown for a project.

    Args:
        db: The database session.
        project_id: The id of the project.
        tab_type: The type of the tab.

    Returns:
        A dictionary containing the estimation breakdown data and a status message.
    """
    if tab_type not in ["MARGIN","MARKUP","SURCHARGE","SELL_PRICE"]:
        return JSONResponse(content={"message": "Invalid tab type"}, status_code=500)
    try:
        data = await get_project_summary(db, project_id)
        resp = {}
        for elm in data:
            if tab_type == "MARGIN":
                resp[elm["code"]] = elm["margin"]
            if tab_type == "MARKUP":
                resp[elm["code"]] = elm["markup"]
            if tab_type == "SURCHARGE":
                resp[elm["code"]] = elm["surcharge"]
            if tab_type == "SELL_PRICE":
                resp[elm["code"]] = elm["final_extended_sell_amount"]
        return {"data": resp, "status": "success"}
    except Exception as e:
        print(traceback.format_exc())
        print("here: ", e)
        raise e


async def get_estimation_surcharge(db: Session, project_id: str):
    """
    Asynchronously retrieves the estimation surcharge for a given project from the database.

    Parameters:
    - db: The database session to use for the query (type: Session)
    - project_id: The ID of the project for which to retrieve the estimation surcharge (type: int)

    Returns:
    - A dictionary containing the estimation surcharge data and the status of the operation (type: dict)
    """
    try:
        data = (
            db.query(RawMaterials, func.avg(ProjectMaterials.surcharge), func.min(ProjectMaterials.surcharge_type))
            .join(ProjectMaterials, isouter=True)
            .filter(
                or_(
                    ProjectMaterials.id == None,  # if ProjectMaterials.id is NULL (i.e., no corresponding ProjectMaterial found)
                    and_(
                        ProjectMaterials.is_deleted == False,  # then filter by project_id and is_active
                        ProjectMaterials.project_id == project_id,
                        ProjectMaterials.is_active == True
                    )
                )
            )
            .group_by(RawMaterials.id)
            .all()
        )
        resp = {}
        for raw_material_data, surcharge, surcharge_type in data:
            if raw_material_data.code != "INST":
                project_raw_material_data = (
                    db.query(ProjectRawMaterials)
                    .filter(
                        ProjectRawMaterials.raw_material_id == raw_material_data.id,
                        ProjectRawMaterials.project_id == project_id,
                    )
                    .first()
                )
                if project_raw_material_data:
                    resp[raw_material_data.code] = {
                        "surcharge_type": surcharge_type,
                        "surcharge": surcharge
                    }
            else:
                stat_data = await get_installation_adon_charges(db, project_id)
                if stat_data is not None:
                    resp[raw_material_data.code] = {
                        "surcharge_type": stat_data["surcharge_type"],
                        "surcharge": stat_data["surcharge"]
                    }

            
        return {"data": resp, "status": "success"}
    except Exception as e:
        print(e)
        raise e



async def discount_project_quote(
    db: Session, 
    discount_project_quote: dict, 
    files: List[UploadFile], 
    project_id: str,  
    current_member: Members
):
    """
    Adds a discount to a project quote.
 
    Args:
        db: Database session object.
        discount_project_quote (dict): Discount project quote data.
        files: List of uploaded files.
        project_id (str): Identifier of the project.
        current_member: Current member performing the operation.
    """
    try:
        manufacturer_id = str(discount_project_quote["manufacturer_id"]) if discount_project_quote["manufacturer_id"] is not None else None
        brand_id = str(discount_project_quote["brand_id"]) if discount_project_quote["brand_id"] is not None else None
        raw_material_id = str(discount_project_quote["raw_material_id"]) if discount_project_quote["raw_material_id"] is not None else None
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            catalog_mapping = (
                db.query(RawMaterialCatalogMapping)
                .filter(
                    RawMaterialCatalogMapping.manufacturer_id==manufacturer_id,
                    RawMaterialCatalogMapping.brand_id==brand_id,
                    RawMaterialCatalogMapping.raw_material_id==raw_material_id
                )
                .first()
            )
            if not catalog_mapping:
                return JSONResponse(content={"message": "wrong catalog selection"}, status_code=400)

            catalog_discount_quote = (
                db.query(ProjectRawMaterialManufacturerQuotes)
                .filter(
                    ProjectRawMaterialManufacturerQuotes.project_id==project_id,
                    ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id==catalog_mapping.id,
                    ProjectRawMaterialManufacturerQuotes.expiry_date <= date.today() - timedelta(days=7)
                ).first()
            )
            if catalog_discount_quote:
                return JSONResponse(content={"message": "Valid Discount already exists"}, status_code=400)
            
            insert_arr = {}
            is_file = False
            if 'discount_quote_number' in discount_project_quote:
                discount_quote_number = discount_project_quote['discount_quote_number']
                insert_arr['quote_text'] = discount_quote_number
            else:
                is_file = True
            if "expiry_date" in discount_project_quote:
                insert_arr['expiry_date'] = discount_project_quote["expiry_date"]

            discount = discount_project_quote['discount']
            discount_type = discount_project_quote['discount_type']
    
            insert_arr['project_id'] = project_id
            insert_arr['discount'] = discount
            insert_arr['raw_materials_catalog_mapping_id'] = catalog_mapping.id
            insert_arr['discount_type'] = discount_type
            insert_arr['created_by'] = current_member.id
    
            discount_manufacturer_quote = ProjectRawMaterialManufacturerQuotes(**insert_arr)
            db.add(discount_manufacturer_quote)
            db.flush()
            
            if is_file and files is not None:
                # Claaing function "upload_to_s3" to upload the attachment to S3
                for file in files:
                    upload_path = f"discount_project_quote_documents/{discount_manufacturer_quote.id}"
                    file_path = await upload_to_s3(file, upload_path)
                    discount_manufacturer_quote.file_path = file_path
    
            update_arr = {
                "discount_type": discount_type,
                "discount_is_basic": False,
                "updated_by": current_member.id,
                "updated_at": datetime.now(),
                "discount": discount
            }
            # chnage the discount type and discount amount in project maetrial so that we can recalculate the discounted price.
            (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.is_deleted == False,
                    ProjectMaterials.project_id == project_id,
                    ProjectMaterials.manufacturer_id == manufacturer_id,
                    ProjectMaterials.brand_id == brand_id,
                    ProjectMaterials.raw_material_id == raw_material_id
                )
                .update(update_arr)
            )
            db.flush()
            # Update the stats in all table using update stats
            rows = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.is_deleted == False,
                    ProjectMaterials.project_id == project_id,
                    ProjectMaterials.manufacturer_id == manufacturer_id,
                    ProjectMaterials.brand_id == brand_id,
                    ProjectMaterials.raw_material_id == raw_material_id
                )
                .all()
            )
            await update_project_stats(db, rows)
    
            return {"id": discount_manufacturer_quote.id, "message": "Data inserted successfully.", "status": "success"}
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error




async def delete_discount_project_quote(
        db: Session,
        request_data: EstimationDiscount, 
        current_member: Members
    ):
    """
    Adds a discount to a project quote.
 
    Args:
        db: Database session object.
        reqest_data (dict): Discount project quote data removar info.
        current_member: Current member performing the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # request_data = request_data.model_dump(exclude_unset=True)
            request_data = request_data.model_dump()
            raw_material_id = str(request_data["raw_material_id"]) if request_data["raw_material_id"] is not None else None
            manufacturer_id = str(request_data["manufacturer_id"]) if request_data["manufacturer_id"] is not None else None
            brand_id = str(request_data["brand_id"]) if request_data["brand_id"] is not None else None
            project_id = str(request_data["project_id"])
            catalog_mapping = (
                db.query(RawMaterialCatalogMapping)
                .filter(
                    RawMaterialCatalogMapping.manufacturer_id==manufacturer_id,
                    RawMaterialCatalogMapping.brand_id==brand_id,
                    RawMaterialCatalogMapping.raw_material_id==raw_material_id
                )
                .first()
            )
            if not catalog_mapping:
                return JSONResponse(content={"message": "wrong catalog selection"}, status_code=400)

            update_arr = {
                "discount_type": "PERCENTAGE",
                "discount_is_basic": True,
                "updated_by": current_member.id,
                "updated_at": datetime.now(),
                "discount": catalog_mapping.discount_percentage if catalog_mapping.discount_percentage is not None else 0
            }


            # remove the previous percentage and put default from manufaturer
            (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.is_deleted == False,
                    ProjectMaterials.project_id == project_id,
                    ProjectMaterials.manufacturer_id == manufacturer_id,
                    ProjectMaterials.brand_id == brand_id,
                    ProjectMaterials.raw_material_id == raw_material_id
                )
                .update(update_arr)
            )
            # delete the quote info
            project_raw_material_quote_data = (
                db.query(ProjectRawMaterialManufacturerQuotes)
                .filter(
                    ProjectRawMaterialManufacturerQuotes.project_id==project_id,
                    ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id==catalog_mapping.id,
                )
            )

            project_raw_material_quote_data_first = project_raw_material_quote_data.first()

            if project_raw_material_quote_data_first.file_path is not None:
                # delete file
                await delete_from_s3(project_raw_material_quote_data_first.file_path)

            project_raw_material_quote_data.delete()

            # Update the stats in all table using update stats
            rows = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.is_deleted == False,
                    ProjectMaterials.project_id == project_id,
                    ProjectMaterials.manufacturer_id == manufacturer_id,
                    ProjectMaterials.brand_id == brand_id,
                    ProjectMaterials.raw_material_id == raw_material_id
                )
                .all()
            )
            await update_project_stats(db, rows)

            return {"message": "Data removed successfully.", "status": "success"}
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def get_project_discount(db: Session, raw_material_id: str, project_id: str):
    """
    get discount infos
    """
    try:
        query = db.query(
            ProjectMaterials.manufacturer_id,
            ProjectMaterials.brand_id,
            func.avg(ProjectMaterials.discount).label('discount'),
            func.min(ProjectMaterials.discount_type).label('discount_type'),
            func.min(ProjectMaterials.discount_is_basic).label('discount_is_basic')
        ).filter(
            ProjectMaterials.raw_material_id == raw_material_id,
            ProjectMaterials.project_id == project_id,
            ProjectMaterials.is_deleted == False
        ).group_by(
            ProjectMaterials.manufacturer_id,
            ProjectMaterials.brand_id

        )

        results = query.all()
        reponse_data = []
        for manufact_data in results:
            data = {
                "manufacturer_id": manufact_data.manufacturer_id,
                "brand_id": manufact_data.brand_id,
                "discount": manufact_data.discount,
                "discount_type": manufact_data.discount_type,
                "discount_is_basic": manufact_data.discount_is_basic,
            }
            current_manufacturer_id = manufact_data.manufacturer_id
            current_brand_id = manufact_data.brand_id
            manu_data = db.query(Manufacturers).filter(Manufacturers.id == current_manufacturer_id).first()
            brand_data = db.query(Brands).filter(Brands.id == current_brand_id).first()
            quote_data = None
            if not manufact_data.discount_is_basic:
                catalog_mapping = (
                    db.query(RawMaterialCatalogMapping)
                    .filter(
                        RawMaterialCatalogMapping.manufacturer_id==current_manufacturer_id,
                        RawMaterialCatalogMapping.brand_id==current_brand_id,
                        RawMaterialCatalogMapping.raw_material_id==raw_material_id
                    )
                    .first()
                )
                quote_data = (
                    db.query(ProjectRawMaterialManufacturerQuotes)
                    .filter(
                        ProjectRawMaterialManufacturerQuotes.raw_materials_catalog_mapping_id == catalog_mapping.id,
                        ProjectRawMaterialManufacturerQuotes.project_id == project_id,
                    )
                    .first()
                )
            data["manufacturer"] = manu_data
            data["brand"] = brand_data
            data["quote_data"] = quote_data
            reponse_data.append(data)
        return {"data": reponse_data, "message": "Data fetched successfully."}
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise e
    


# async def download_descount_quote(db: Session, discount_quote_id: str):
#     """
#     Download the discount quote file from the database and serve it as a FileResponse.

#     Args:
#         db (Session): The SQLAlchemy database session.
#         discount_quote_id (str): The ID of the discount quote to download.
#     """
#     try:
#         discount_quote = db.query(ProjectRawMaterialManufacturerQuotes).filter(ProjectRawMaterialManufacturerQuotes.id == discount_quote_id).first()
#         if discount_quote:
#             # BUCKET_NAME = os.environ.get("BUCKET_NAME")
#             file_path = discount_quote.file_path
#             # s3_file_path = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_path}"
#             # print(s3_file_path)
#             # headers = {"Content-Disposition": "inline"}
#             # return FileResponse(s3_file_path, headers=headers)
        
#             file_content, content_type, filename = download_from_s3(file_path)
    
#             # Return the file as a streaming response
#             return StreamingResponse(
#                 file_content,
#                 media_type=content_type,
#                 headers={
#                     "Content-Disposition": f"attachment; filename={filename}"
#                 }
#             )

#         else:
#             raise HTTPException(status_code=404, detail="Discount quote not found")
    
#     except IntegrityError as e:
#         logger.exception(f"IntegrityError: {e}")
#         raise e
 
#     except Exception as e:
#         logger.exception(f"An unexpected error occurred: {e}")
#         raise e



# TODO
def format_float(value):
    # print(value)
    value = float(format(Decimal(value), '.2f')) if value is not None else 0
    # value = float(format(Decimal(value), '.2f'))
    return value

async def material_type_wise_estimated_price(db: Session, project_id: str):
    """
    Retrieves the material type wise estimated price for a given project.
    Args:
        db (Session): The database session.
        project_id (int): The ID of the project.
    """
    try:
        # Check if project_id exists
        project_exists = db.query(Projects.id).filter(Projects.id == project_id, Projects.is_deleted == False).first()

        if not project_exists:
            return {"data": None, "message": f"Project with ID {project_id} does not exist."}
        # Finding out all ids of door related raw materials that are used in 
        # any area item where there is no installation charge added to it
        installing_opening_raw_material_ids = await get_installed_raw_materials(db, project_id)
        # print("installing_opening_raw_material_ids:: ",installing_opening_raw_material_ids)
        # Main Summarization query
        query = (
            db.query(
                ProjectRawMaterials.id.label('project_raw_material_id'),
                ProjectRawMaterials.section_id.label('section_id'),
                RawMaterials.id.label("raw_material_id"),
                ProjectRawMaterials.name,
                RawMaterials.code,
                RawMaterials.item_number,
                ProjectRawMaterials.final_amount.label('final_amount'),
                ProjectRawMaterials.final_base_amount.label('final_base_amount'),
                ProjectRawMaterials.final_sell_amount.label('final_sell_amount'),
                ProjectRawMaterials.final_extended_sell_amount.label('final_extended_sell_amount'),
                ProjectRawMaterials.quantity.label('quantity'),
                # ProjectRawMaterials.has_installation,
                ProjectTakeOffSheetNotes.id.label('note_id'),
                ProjectTakeOffSheetNotes.name.label('note_name'),
                ProjectTakeOffSheetNotes.desc.label('note_desc')
            )
            .join(RawMaterials, ProjectRawMaterials.raw_material_id == RawMaterials.id)
            .outerjoin(ProjectTakeOffSheetNotes, ProjectTakeOffSheetNotes.project_raw_material_id == ProjectRawMaterials.id)
            .filter(ProjectRawMaterials.project_id == project_id)
            .order_by(RawMaterials.sort_order.asc(), ProjectTakeOffSheetNotes.created_at.asc())
        )

        
        # Execute the query and fetch results
        results = query.all()
        response_data = []
        for res in results:
            has_installation = res.raw_material_id in installing_opening_raw_material_ids
            raw_material_data = {
                'project_raw_material_id': res.project_raw_material_id,
                'raw_material_id': res.raw_material_id,
                'name': res.name,
                'raw_material_code': res.code,
                'item_number': res.item_number,
                'final_amount': format_float(res.final_amount),
                'final_base_amount': format_float(res.final_base_amount),
                'final_sell_amount': format_float(res.final_sell_amount),
                'final_extended_sell_amount': format_float(res.final_extended_sell_amount),
                'quantity': res.quantity,
                'has_installation': has_installation,
                'notes': []
            }
            # Find the index of the dictionary where 'x' equals 1
            index_of_dict = next((i for i, d in enumerate(response_data) if d.get("project_raw_material_id") == res.project_raw_material_id), None)
            if index_of_dict is not None:
                if res.note_id:
                    # Append the note to the existing dictionary
                    response_data[index_of_dict]['notes'].append({
                        'id': res.note_id,
                        'name': res.note_name,
                        'desc': res.note_desc
                    })
            else:
                if res.note_id:
                    raw_material_data['notes'].append({
                        'id': res.note_id,
                        'name': res.note_name,
                        'desc': res.note_desc
                    })
                # Append the raw material data to the response list
                response_data.append(raw_material_data)
        project_take_off_sheet = db.query(ProjectTakeOffSheets.id).filter(ProjectTakeOffSheets.project_id == project_id).first()
        miscellaneous_price = await get_total_adon_price(db, project_take_off_sheet.id)
        # miscellaneous_price = 0

        return {"data": response_data, "miscellaneous_price": round(miscellaneous_price, 2), "message": "Data fetched successfully."}

    except IntegrityError as e:
        # Log and handle specific integrity errors
        logger.error(f"Integrity error occurred: {str(e)}")
        return {"data": None, "message": f"Integrity error occurred: {str(e)}"}

    except SQLAlchemyError as e:
        # Log and handle more general SQLAlchemy errors
        logger.error(f"Database error occurred: {str(e)}")
        return {"data": None, "message": f"Database error occurred: {str(e)}"}

    except Exception as e:
        # Log and handle any other exceptions
        logger.error(f"An unexpected error occurred: {str(e)}")
        print(traceback.format_exc())
        return {"data": None, "message": f"An unexpected error occurred: {str(e)}"}
    

async def get_take_off_sheet_section_area_info(db: Session, take_off_sheet_section_area_item_id: str):
    """**Summary:**
   get the details of a section area within a project's take-off sheet section.

    **Args:**
    - db (Database): The database session.
    - take_off_sheet_section_id (int): The ID of the section area to be fetched.

    **Returns:**
    - dict: A dictionary containing the details of the section area.
    """
    try:
        data = []

        section_area_item, section_area_name, section_name = (
            db.query(ProjectTakeOffSheetSectionAreaItems, ProjectTakeOffSheetSectionAreas.name, Sections.name)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.id == take_off_sheet_section_area_item_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .first()
        )
        # if section_area_item:
        #     section_area_item_data = (
        #         db.query(ProjectTakeOffSheetSectionAreaItems)
        #         .filter(
        #             ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_area_id == section_area_item.project_take_off_sheet_section_area_id,
        #             ProjectTakeOffSheetSectionAreaItems.is_deleted == False
        #         )
        #         .all()
        #     )
        #     for area in section_area_item_data:
        #         data.append(area.to_dict)
        return {
            "data": section_area_item,
            "section_area_name": section_area_name,
            "section_name": section_name,
            "status": "success"
        }
    
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
