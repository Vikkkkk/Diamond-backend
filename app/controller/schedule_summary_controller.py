"""
This module containes all logical operation and db operations those are related to schedule add/update/read/delete.
"""
import traceback
from typing import List
from schemas.take_off_sheet_estimation_schemas import EstimationDiscount
from models.members import Members
from repositories.update_stats_repositories import get_installation_adon_charges
from models.project_take_off_sheets import ProjectTakeOffSheets
from repositories.common_repositories import get_total_adon_price
from utils.common import get_utc_time, generate_uuid, get_random_hex_code
from loguru import logger
from models.schedules import Schedules
from utils.request_handler import call_get_api, call_post_api
from sqlalchemy import or_
from models import get_db
from models.raw_materials import RawMaterials
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.adon_opening_fields import AdonOpeningFields
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.schedule_data import ScheduleData, COMPONENT_TYPE
from models.brands import Brands
from models.manufacturers import Manufacturers
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from sqlalchemy.orm import Session
from controller.material_controller import get_adonprice
from controller.transfer_opening_controller import compare_take_off_data
from schemas.schedule_schemas import ScheduleRequest, ScheduleResponse
from schemas.schedule_data_schema import ScheduleDataRequest, ScheduleDataBulkRequest, ScheduleDataBulkSaveSchema, ScheduleDataResponse, ScheduleData as ScheduleDataRes
from schemas.adon_opening_fields_schema import AdonOpeningFieldSchema, AdonOpeningFieldOptionSchema, AdonOpeningFieldResponseSchema
from utils.common import get_user_time, upload_to_s3, get_aws_full_path, delete_from_s3, find_best_match_dict
from fastapi import HTTPException
from repositories.material_repositories import get_material_catalog, get_material_series
from repositories.schedule_repositories import get_schedule_summary, set_hardware_prep_data, set_location_data,comparison_opening_data, set_opening_breakups_to_schedule_data, update_schedule_stats
from repositories.schedule_summary_repositories import add_schedule_discount_project_quote, get_project_schedule_component_summary, get_project_schedule_summary, get_schedule_discount_data, get_schedule_component_summary, delete_schedule_discount_project_quote, get_project_comparison_data, get_schedule_comparison_data
from fastapi.responses import JSONResponse, FileResponse
import json
from sqlalchemy.exc import SQLAlchemyError



async def get_schedule_overall_summary(db: Session, project_id: str):
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
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            [project_take_off_sheet_id] = (
                db.query(ProjectTakeOffSheets.id)
                .filter(
                    ProjectTakeOffSheets.project_id == project_id, 
                    ProjectTakeOffSheets.is_deleted == False,
                    ProjectTakeOffSheets.is_active == True
                ).first()
            )
            if not project_take_off_sheet_id:
                return JSONResponse(content={"message": f"Takeoff sheet not exist."}, status_code=406)
            summary_data = await get_project_schedule_summary(db, project_id)
            # print("-----------------------------")
            # print("summary_data:: ", summary_data)
            # print("-----------------------------")
            comparision_data = await get_project_comparison_data(db, project_id)
            resp = []
            for data in summary_data:
                final_amount_change = 0
                final_base_amount_change = 0
                final_sell_amount_change = 0
                final_extended_sell_amount_change = 0
                schedule_comparison_data = comparision_data.get(data["schedule_id"], None)
                if schedule_comparison_data is  not None:
                    for component, price_change in schedule_comparison_data.items():
                        # print("component, price_change:: ", component, price_change)
                        final_amount_change += price_change["final_amount"]
                        final_base_amount_change += price_change["final_base_amount"]
                        final_sell_amount_change += price_change["final_sell_amount"]
                        final_extended_sell_amount_change += price_change["final_extended_sell_amount"]
                data["old_final_amount"] = round(data["final_amount"] - final_amount_change, 3)
                data["old_final_base_amount"] = round(data["final_base_amount"] - final_base_amount_change, 3)
                data["old_final_sell_amount"] = round(data["final_sell_amount"] - final_sell_amount_change, 3)
                data["old_final_extended_sell_amount"] = round(data["final_extended_sell_amount"] - final_extended_sell_amount_change, 3)
                data["final_amount_diff"] = final_amount_change
                data["final_base_amount_diff"] = final_base_amount_change
                data["final_sell_amount_diff"] = final_sell_amount_change
                data["final_extended_sell_amount_diff"] = final_extended_sell_amount_change
                resp.append(data)
            miscellaneous_price = await get_total_adon_price(db, project_take_off_sheet_id)
            installation_charge = None
            adon_data = await get_installation_adon_charges(db, project_id)
            if adon_data is not None:
                installation_charge = adon_data["final_extended_sell_amount"]
            return {"data": resp, "miscellaneous_price": miscellaneous_price, "installation_charge": installation_charge, "status": "success"}

    except Exception as e:
        print(traceback.format_exc())
        print('Error:: ',e)
        raise e



async def get_schedule_component_breakup_summary(db: Session, schedule_id: str):
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
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            summary_data = await get_schedule_component_summary(db, schedule_id)
            comparision_data = await get_schedule_comparison_data(db, schedule_id)
            resp = []
            for data in summary_data:
                old_final_amount = 0
                old_final_base_amount = 0 
                old_final_sell_amount = 0 
                old_final_extended_sell_amount = 0 
                comp_part_key =  f"{data['component']}-{data['part_number']}" if data['component'] == "DOOR" else data['component']
                data["comp_part_key"] = comp_part_key
                component_comparison_data = comparision_data.get(comp_part_key, None)
                if component_comparison_data is not None:
                    old_final_amount += (data["final_amount"] - component_comparison_data["final_amount"])
                    old_final_base_amount += (data["final_base_amount"] - component_comparison_data["final_base_amount"])
                    old_final_sell_amount += (data["final_sell_amount"] - component_comparison_data["final_sell_amount"])
                    old_final_extended_sell_amount += (data["final_extended_sell_amount"] - component_comparison_data["final_extended_sell_amount"])
                else:
                    old_final_amount = data["final_amount"] 
                    old_final_base_amount = data["final_base_amount"] 
                    old_final_sell_amount = data["final_sell_amount"] 
                    old_final_extended_sell_amount = data["final_extended_sell_amount"] 
                data["old_final_amount"] = old_final_amount
                data["old_final_base_amount"] = old_final_base_amount
                data["old_final_sell_amount"] = old_final_sell_amount
                data["old_final_extended_sell_amount"] = old_final_extended_sell_amount
                data["final_amount_diff"] = round(data["final_amount"] - old_final_amount, 3)
                data["final_base_amount_diff"] = round(data["final_base_amount"] - old_final_base_amount, 3)
                data["final_sell_amount_diff"] = round(data["final_sell_amount"] - old_final_sell_amount, 3)
                data["final_extended_sell_amount_diff"] = round(data["final_extended_sell_amount"] - old_final_extended_sell_amount, 3)
                resp.append(data)
            return {"data": resp, "status": "success"}
    except Exception as e:
        print(traceback.format_exc())
        print('Error:: ',e)
        raise e




async def get_schedule_discount(db: Session, project_id: str):
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
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            result, raw_data = await get_schedule_discount_data(db, project_id)
            data = {}
            for elm in result:
                elm["catalog"] = elm["brand_name"] if elm["brand_id"] else elm["manufacturer_name"]
                if elm["raw_material_code"] not in data:
                    data[elm["raw_material_code"]] = [elm]
                else:
                    data[elm["raw_material_code"]].append(elm)
            return {"data": data, "status": "success"}
    except Exception as e:
        print(traceback.format_exc())
        print('Error:: ',e)
        raise e



async def add_schedule_discount_quote(
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
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            data = await add_schedule_discount_project_quote(
                db, 
                discount_project_quote, 
                files, 
                project_id,  
                current_member
            )
            return {"id": data, "message": "Data inserted successfully.", "status": "success"}
    except Exception as e:
        print(traceback.format_exc())
        print('Error:: ',e)
        raise e



async def delete_discount_schedule_quote(
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
            request_data = request_data.model_dump(exclude_unset=True)
            await delete_schedule_discount_project_quote(
                db, 
                request_data,
                current_member
            )
            return {"message": "Data delted successfully.", "status": "success"}
    except Exception as e:
        print(traceback.format_exc())
        print('Error:: ',e)
        raise e