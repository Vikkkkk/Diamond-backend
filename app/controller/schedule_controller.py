"""
This module containes all logical operation and db operations those are related to schedule add/update/read/delete.
"""
import traceback
from typing import List
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
from models.opening_door_frame_materials import OpeningDoorFrameMaterials
from models.schedule_opening_door_frame_material import ScheduleOpeningDoorFrameMaterials
from models.co_schedules import CoSchedules
from models.change_order import ChangeOrder, ChangeOrderStatusEnum
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from sqlalchemy.orm import Session
from controller.material_controller import get_adonprice
from controller.transfer_opening_controller import compare_take_off_data
from schemas.schedule_schemas import ScheduleRequest, ScheduleResponse, ScheduleStatus
from schemas.schedule_data_schema import ScheduleDataRequest, ScheduleDataBulkRequest, ScheduleDataBulkSaveSchema, ScheduleDataResponse, ScheduleData as ScheduleDataRes
from schemas.adon_opening_fields_schema import AdonOpeningFieldSchema, AdonOpeningFieldOptionSchema, AdonOpeningFieldResponseSchema
from utils.common import get_user_time, upload_to_s3, get_aws_full_path, delete_from_s3, find_best_match_dict
from fastapi import HTTPException
from repositories.material_repositories import get_material_catalog, get_material_series
from repositories.schedule_repositories import get_hing_locations, set_hardware_prep_data, set_location_data,comparison_opening_data, set_opening_breakups_to_schedule_data, update_schedule_stats
from fastapi.responses import JSONResponse, FileResponse
from repositories import schedule_repositories
from sqlalchemy import exists, and_
from schemas.schedule_schemas import AdonOpeningFieldCreateSchema
import json
from sqlalchemy.exc import SQLAlchemyError


async def get_schedules(db: Session, project_id: str):
    """
    Fetch schedules for a specific project.

    Args:
        db (Session): SQLAlchemy database session used to query the database.
        project_id (str): The unique identifier of the project whose schedules are to be fetched.

    Returns:
        ScheduleResponse: A response containing a list of schedules and a success status.

    Raises:
        HTTPException: 
            - 200: If no schedules are found for the given project_id.
            - 500: If an unexpected error occurs while fetching the schedules.
    """
    try:
        logger.info(f"Fetching schedules for project_id={project_id}")
        result = db.query(Schedules).filter(Schedules.project_id == project_id).order_by(Schedules.created_at.desc()).all()

        if not result:
            logger.warning(f"No schedules found for project_id={project_id}")
            raise HTTPException(
                status_code=200, detail=f"No schedules found for project_id: {project_id}"
            )
        response = []
        for res in result:
            data = {}
            data['id'] = res.id
            data['opening_number'] = res.opening_number
            data['area'] = res.area
            data['location_1'] = res.location_1
            data['location_2'] = res.location_2
            data['from_to'] = res.from_to
            data['door_qty'] = res.door_qty
            data['frame_qty'] = res.frame_qty
            data['project_id'] = res.project_id
            data['frame_section_file_path'] = get_aws_full_path(res.frame_section_file_path) if res.frame_section_file_path is not None else None
            data['frame_section_file_type'] = res.frame_section_file_type
            data['frame_material_code'] = res.frame_material_code
            data['door_material_code'] = res.door_material_code
            data['door_type'] = res.door_type
            data['swing'] = res.swing
            data['is_freezed'] = res.is_freezed
            data['is_in_change_order'] = res.is_in_change_order
            has_requested = (
                res.has_door_requested == True
                and res.has_frame_requested == True
                and res.has_hw_requested == True
            )
            has_ordered = (
                res.has_door_ordered == True
                and res.has_frame_ordered == True
                and res.has_hw_ordered == True
            )
            has_shipped = (
                res.has_door_shipped == True
                and res.has_frame_shipped == True
                and res.has_hw_shipped == True
            )

            data['has_requested'] = has_requested
            data['has_ordered'] = has_ordered
            data['has_shipped'] = has_shipped

            # Derive an overall status from the aggregate stage flags.
            if has_shipped:
                data['status'] = ScheduleStatus.SHIPPED
            elif has_ordered:
                data['status'] = ScheduleStatus.ORDERED
            elif has_requested:
                data['status'] = ScheduleStatus.REQUESTED
            else:
                data['status'] = ScheduleStatus.NOT_REQUESTED

            response.append(data)
        

        return ScheduleResponse(data=response, status="success")

    except HTTPException as http_exc:
        logger.info(f"Raising HTTPException with status: {http_exc.status_code}")
        return JSONResponse(status_code=http_exc.status_code, content={"message": http_exc.detail})

    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

async def save_initial_schedule_data(db: Session, component: str, schedule_id: str, field_name: str, filed_value: str, field_id: str):
    try:
        existing_data = db.query(ScheduleData).filter(ScheduleData.schedule_id == schedule_id, ScheduleData.name == field_name, ScheduleData.component == component).first()
        field_option_data = db.query(AdonOpeningFieldOptions).filter(AdonOpeningFieldOptions.adon_opening_field_id == field_id, AdonOpeningFieldOptions.name == filed_value).first()
        adon_field_option_id = None
        if field_option_data:
            adon_field_option_id = field_option_data.id
        if existing_data:
            existing_data.value = filed_value
            existing_data.adon_field_option_id = adon_field_option_id
            db.flush()
        else:
            data = {
                "name": field_name,
                "component": component,
                "schedule_id": schedule_id,
                "value": filed_value,
                "desc": field_name,
                "adon_field_option_id": adon_field_option_id,
                "adon_field_id": field_id,
            }
            new_data = ScheduleData(**data)
            db.add(new_data)
            db.flush()
    except Exception as error:
        logger.exception(f"save_initial_schedule_data:: An unexpected error occurred: {error}")
        raise error

async def save_initial_adon_fileds(db: Session, schedule_id: str, schedule_data):
    try:
        if "door_type" in schedule_data:
            door_type = schedule_data["door_type"]
            door_type_details = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == "door_type").first()
            if door_type_details:
                field_id = door_type_details.id
                if door_type_details.is_door_data:
                    await save_initial_schedule_data(db, "DOOR", schedule_id, "door_type", door_type, field_id)
                if door_type_details.is_frame_data:
                    await save_initial_schedule_data(db, "FRAME", schedule_id, "door_type", door_type, field_id)
        if "swing" in schedule_data:
            swing = schedule_data["swing"]
            swing_details = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == "swing").first()
            if swing_details:
                field_id = swing_details.id
                if swing_details.is_door_data:
                    await save_initial_schedule_data(db, "DOOR", schedule_id, "swing", swing, field_id)
                if swing_details.is_frame_data:
                    await save_initial_schedule_data(db, "FRAME", schedule_id, "swing", swing, field_id)
        db.flush()
    except Exception as error:
        logger.exception(f"save_initial_adon_fileds:: An unexpected error occurred: {error}")
        raise error

async def save_schedule(db: Session, project_id: str, schedule: ScheduleRequest, current_member: str):
    """
    Create a new schedule entry in the database.

    Args:
        db (Session): SQLAlchemy session object.
        schedule (ScheduleRequest): Schedule data from the request body.
        current_member (str): ID of the current user creating the schedule.

    Returns:
        Schedules: The newly created schedule object.
    """
    try:
        schedule_data = schedule.model_dump(exclude_unset=True)
        logger.info(f"Creating schedule with data: {schedule_data} by member: {current_member}")

        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Get takeoff sheet data
            take_off_area_item_id = None
            section_id = None
            door_material_id = None
            frame_material_id = None
            takeoff_sheet_data = db.query(ProjectTakeOffSheetSectionAreaItems).filter(ProjectTakeOffSheetSectionAreaItems.opening_number == schedule_data['opening_number']).first()
            if takeoff_sheet_data:
                take_off_area_item_id = takeoff_sheet_data.id
                section_id = takeoff_sheet_data.project_take_off_sheet_section_id
            if "door_material_code" in schedule_data:
                door_mat_data = db.query(RawMaterials).filter(RawMaterials.code == schedule_data["door_material_code"]).first()
                door_material_id = door_mat_data.id
                schedule_data["door_material_id"] = door_material_id
            if "frame_material_code" in schedule_data:
                frame_mat_data = db.query(RawMaterials).filter(RawMaterials.code == schedule_data["frame_material_code"]).first()
                frame_material_id = frame_mat_data.id
                schedule_data["frame_material_id"] = frame_material_id
            # Check if the manufacturer already exists
            if "id" in schedule_data:
                schedule_info = db.query(Schedules).get(schedule_data['id'])
                if not schedule_info:
                    # raise Exception("Invalid Schedule ID")
                    return JSONResponse(status_code=400, content={"message": "Invalid Schedule ID"})
                else:
                    # Update existing manufacturer
                    for key, value in schedule_data.items():
                        setattr(schedule_info, key, value)
                    db.flush()
                    # db.refresh(schedule_info)
                    # await save_initial_adon_fileds(db, schedule_info.id, schedule_data)
                    resp_data = {
                        "id": schedule_info.id,
                        "opening_number": schedule_info.opening_number,
                        "location_1": schedule_info.location_1,
                        "location_2": schedule_info.location_2,
                        "from_to": schedule_info.from_to,
                        "door_qty": schedule_info.door_qty,
                        "frame_qty": schedule_info.frame_qty,
                        "door_material_id": schedule_info.door_material_id,
                        "door_material_code": schedule_info.door_material_code,
                        "frame_material_id": schedule_info.frame_material_id,
                        "frame_material_code": schedule_info.frame_material_code,
                        "door_type": schedule_info.door_type,
                        "swing": schedule_info.swing,
                    }
                    # Log success
                    logger.info(f"Schedule updated successfully with ID: {schedule_info.id}")
                    # Return response with status code and message
                    return {
                        "status": 200,
                        "message": "Schedule updated successfully.",
                        "data": resp_data
                    }
            else:
                # Prepare the schedule data
                new_schedule = Schedules(
                        type = "OPENING",
                        project_id = project_id,
                        opening_number = schedule_data['opening_number'],
                        area = schedule_data['area'],
                        location_1 = schedule_data['location_1'],
                        location_2 = schedule_data['location_2'],
                        from_to = schedule_data['from_to'],
                        door_qty = schedule_data['door_qty'],
                        frame_qty = schedule_data['frame_qty'],
                        door_material_id = schedule_data['door_material_id'],
                        door_material_code = schedule_data['door_material_code'],
                        frame_material_id = schedule_data['frame_material_id'],
                        frame_material_code = schedule_data['frame_material_code'],
                        door_type = schedule_data['door_type'],
                        swing = schedule_data['swing'],
                        created_by = current_member.id,
                        take_off_area_item_id = take_off_area_item_id,
                        section_id = section_id
                    )

                # Add to the session
                db.add(new_schedule)
                db.flush()
                # db.refresh(new_schedule)
                # await save_initial_adon_fileds(db, new_schedule.id, schedule_data)
                resp_data = {
                    "id": new_schedule.id,
                    "opening_number": new_schedule.opening_number,
                    "location_1": new_schedule.location_1,
                    "location_2": new_schedule.location_2,
                    "from_to": new_schedule.from_to,
                    "door_qty": new_schedule.door_qty,
                    "frame_qty": new_schedule.frame_qty,
                    "door_material_id": new_schedule.door_material_id,
                    "door_material_code": new_schedule.door_material_code,
                    "frame_material_id": new_schedule.frame_material_id,
                    "frame_material_code": new_schedule.frame_material_code,
                    "door_type": new_schedule.door_type,
                    "swing": new_schedule.swing,
                }
                # Log success
                logger.info(f"Schedule created successfully with ID: {new_schedule.id}")

                # Return response with status code and message
                return {
                    "status": 201,
                    "message": "Schedule created successfully.",
                    "data": resp_data
                }
    except HTTPException as http_exc:
        logger.info(f"Raising HTTPException with status: {http_exc.status_code}")
        return JSONResponse(status_code=http_exc.status_code, content={"message": http_exc.detail})
    
    except Exception as e:
        print(traceback.format_exc())
        logger.error(f"Error fetching schedules: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

async def get_opening_fields(db: Session, opening_type: str):
    """
    Retrieve opening fields based on the specified opening type.

    Args:
        db (Session): SQLAlchemy database session used to query the database.
        opening_type (str): The type of opening data to filter by. Possible values are:
                            - "DOOR": Filters for door-related fields.
                            - "FRAME": Filters for frame-related fields.
                            - "HARDWARE": Filters for hardware-related fields.

    Returns:
        AdonOpeningFieldResponseSchema: A structured response containing the list of opening fields 
                                         and their associated options, along with a success status.

    Raises:
        HTTPException: If an error occurs during the database query or data mapping.
    """
    try:
        query = db.query(AdonOpeningFields).filter(
        AdonOpeningFields.field_category.like("%OPENING_SCHEDULE%"),
        or_(
            AdonOpeningFields.is_adon_field == True,
            AdonOpeningFields.name.like("%_catalog%"),
            AdonOpeningFields.name.like("%_series%")
        ))

        if opening_type == "DOOR":
            query = query.filter(AdonOpeningFields.is_door_data == True)
        elif opening_type == "FRAME":
            query = query.filter(AdonOpeningFields.is_frame_data == True)
        elif opening_type == "HARDWARE":
            query = query.filter(AdonOpeningFields.is_hw_data == True)
        elif opening_type == "OPENING":
            query = query.filter(AdonOpeningFields.is_opening_data == True)


        fields = query.order_by(AdonOpeningFields.sort_order.asc()).all()

        response = []
        for field in fields:
            # Map each AdonOpeningFieldSchema
            field_data = AdonOpeningFieldSchema(
                id=field.id,
                name=field.name,
                desc=field.desc,
                has_price_dependancy=field.has_price_dependancy,
                field_type=str(field.field_type.value),
                field_category=field.field_category,
                rule=field.rule,
                is_adon_field=field.is_adon_field,
                field_options=[
                    AdonOpeningFieldOptionSchema(
                        id=option.id,
                        name=option.name,
                        desc=option.desc,
                        rule=option.rule,
                        adon_opening_field_id=option.adon_opening_field_id,
                    )
                    for option in field.adon_field_options
                ] if field.adon_field_options and not field.has_price_dependancy else None
            )
            response.append(field_data)

        return {
                "status": "success",
                "component": opening_type,
                "data": response
            } 
    except Exception as error:
        logger.exception(f"get_opening_fields:: An unexpected error occurred: {error}")
        raise error




async def get_feature_options(db: Session, manufacturer_code: str, brand_code: str, field_name: str, series_code: str):
    """**Summary:**
    fetch all feature options matching with keywords and series code(if there in the filter).

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - field_name (str): The field name.
    - series_code (str): The series code.

    **Returns:**
    - dict: A dictionary containing information about all available feature options of a manufacturer and brand depending on the filters.
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        field_data = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == field_name).first()
        if field_name in ["door_catalog", "frame_catalog"]:
            data = db.query(RawMaterials).filter(RawMaterials.name.ilike(f'%{field_name.split("_")[0]}%')).all()
            code_list = []
            for item in data:
                code_list.append(item.code)
            return {"data": await get_material_catalog(db, code_list), "message": "Data fetch successfull"}
        elif field_name in ["door_series", "frame_series"]:
            if manufacturer_code is None:
                return JSONResponse(content={"message": "Manufacture not provided"}, status_code=400)
            else:
                return {"data": await get_material_series(manufacturer_code, brand_code, field_name.split("_")[0]), "message": "Data fetch successfull"}
        else:
            if brand_code is not None:
                param_data = {
                    "manufacturerCode": manufacturer_code,
                    "brandCode": brand_code,
                    "seriesCode": series_code,
                    "keywords": field_data.search_keywords.lower(),
                }
            else:
                param_data = {
                    "manufacturerCode": manufacturer_code,
                    "seriesCode": series_code,
                    "keywords": field_data.search_keywords.lower(),
                }
                
            if field_data.adon_field_options and len(field_data.adon_field_options) > 0:
                param_data["keywords"] = param_data["keywords"] + "," + ",".join(elm.search_keywords for elm in field_data.adon_field_options)
            if field_data.is_adon_field:
                response = await call_get_api("diamond/adonFeatures/get_adon_feature_options", param_data)
            else:
                response = await call_get_api("diamond/features/get_feature_options", param_data)
            if int(response["status_code"]) == 200:
                resp_data = response["response"]["data"]
                for indx, elm in enumerate(resp_data):
                    if "_id" in elm:
                        resp_data[indx]["id"] = elm["_id"]
                        del resp_data[indx]["_id"]
                return {"data": response["response"]["data"], "message": "Data fetch successfull"}
            else:
                return JSONResponse(content={"message": "Unable to fetch pricebook data"}, status_code=int(response["status_code"]))
    except Exception as error:
        logger.exception(f"get_feature_options:: An unexpected error occurred: {error}")
        raise error


async def filter_by_series_code(data, input_series_codes):
    # Filter the dictionaries where any seriesCode in availabilityCriteria matches the input series codes
    # print("input_series_codes:: ",input_series_codes)
    # print("data:: ",len(data))
    result = [
        d for d in data
        if "availabilityCriteria" in d and any(
            criteria.get("seriesCode") in input_series_codes
            for criteria in d["availabilityCriteria"]
        )
    ]
    # print("result:: ",len(result))
    # print("result:: ",result)
    return result


async def get_static_option(
        db,
        manufacturer_code,
        brand_code,
        series_code,
        field_name,
        adon_field_id,
        adon_field_option_id
    ):
    try:
        field_options_info = await get_feature_options(
            db=db,
            manufacturer_code=manufacturer_code,
            brand_code=brand_code,
            series_code=series_code,
            field_name=field_name
        )
        if "data" in field_options_info:
            field_options_info = field_options_info["data"]
            field_options_info = await filter_by_series_code(field_options_info, [series_code])
            if len(field_options_info) > 0:
                adon_field_option_info = db.query(AdonOpeningFieldOptions).get(adon_field_option_id)
                search_keywords = adon_field_option_info.search_keywords.split(",")
                # print("search_keywords:: ",search_keywords)
                best_match = await find_best_match_dict(
                    search_keywords,
                    field_options_info,
                    "optionCode"
                )
                return best_match
            else:
                None
        else:
            return None
    except Exception as error:
        logger.exception(f"get_static_option:: An unexpected error occurred: {error}")
        return None
    
async def get_static_option_price(
        db,
        manufacturer_code,
        brand_code,
        series_code,
        field_name,
        adon_field_id,
        adon_field_option_id
    ):
    try:
        field_options_info = await get_feature_options(
            db=db,
            manufacturer_code=manufacturer_code,
            brand_code=brand_code,
            series_code=series_code,
            field_name=field_name
        )
        if "data" in field_options_info:
            field_options_info = field_options_info["data"]
            field_options_info = await filter_by_series_code(field_options_info, [series_code])
            if len(field_options_info) > 0:
                adon_field_option_info = db.query(AdonOpeningFieldOptions).get(adon_field_option_id)
                search_keywords = adon_field_option_info.search_keywords.split(",")
                # print("search_keywords:: ",search_keywords)
                best_match = await find_best_match_dict(
                    search_keywords,
                    field_options_info,
                    "optionCode"
                )
                # print("field_options_info:: ",field_options_info)
                # print("best_match:: ",best_match)
                adon_price_obj = None
                if best_match is not None:
                    adon_price_obj = await get_adonprice(
                        {best_match["adonFeatureCode"]: best_match["optionCode"]},
                        manufacturer_code,
                        brand_code,
                        series_code
                    )
                    # print("adon_price_obj:: ",adon_price_obj)
                return adon_price_obj, best_match
            else:
                return None, None
        else:
            return None, None
    except Exception as error:
        logger.exception(f"get_static_option_price:: An unexpected error occurred: {error}")
        return None, None
    

async def prepare_price_fetch_data(db, fields, component, schedule_id, part_number):
    try:
        catalog_field_name = f"{component.lower()}_catalog"
        series_field_name = f"{component.lower()}_series"
        if component in ["DOOR","FRAME"] and catalog_field_name not in list(fields.keys()):
            raise ValueError(f"Catalog field '{catalog_field_name}' not found in fields.")
        if component in ["DOOR","FRAME"] and series_field_name not in list(fields.keys()):
            raise ValueError(f"Series field '{series_field_name}' not found in fields.")
        base_price_request_data = {}
        original_request_data = {}
        adon_price_request_data = []

        for field_name, field_value in fields.items():
            adon_field_id = None
            # print("field_name:: ",field_name)
            # print("has_price_dependancy:: ",field_value["has_price_dependancy"])
            # print("is_adon_field:: ",field_value["is_adon_field"])
            if "adon_field_id" in field_value and field_value["adon_field_id"] != "":
                adon_field_id = field_value["adon_field_id"]
            adon_field_option_id = None
            if "adon_field_option_id" in field_value and field_value["adon_field_option_id"] != "":
                adon_field_option_id = field_value["adon_field_option_id"]
            if component in ["DOOR","FRAME"]:
                if (field_name not in [catalog_field_name, series_field_name]) and field_value["has_price_dependancy"]:

                    if not field_value["is_adon_field"]:
                        print("field_value", field_value)
                        if "manufacturerCode" not in base_price_request_data:
                            base_price_request_data["manufacturerCode"] = field_value["manufacturerCode"] if "manufacturerCode" in field_value else None
                        if "brandCode" not in base_price_request_data:
                            base_price_request_data["brandCode"] = field_value["brandCode"] if "brandCode" in field_value else None
                        if "seriesCode" not in base_price_request_data:
                            base_price_request_data["seriesCode"] = field_value["seriesCode"] if "seriesCode" in field_value else None
                        if ("category" not in base_price_request_data) and ("category" in  field_value):
                            base_price_request_data["category"] = field_value["category"]
                        if "featureCode" in field_value and field_value["featureCode"] not in base_price_request_data:
                            base_price_request_data[field_value["featureCode"]] = field_value["optionCode"]
                        else:
                            # print(field_value)
                            if adon_field_option_id is not None:
                                base_feature = await get_static_option(
                                    db,
                                    field_value["manufacturerCode"] if "manufacturerCode" in field_value else None,
                                    field_value["brandCode"] if "brandCode" in field_value else None,
                                    field_value["seriesCode"] if "seriesCode" in field_value else None,
                                    field_name,
                                    adon_field_id,
                                    adon_field_option_id
                                )
                                # print("base_feature:: ",base_feature)
                                if base_feature is not None:
                                    base_price_request_data[base_feature["featureCode"]] = base_feature["optionCode"]
                                    field_value["featureCode"] = base_feature["featureCode"]
                                    field_value["optionCode"] = base_feature["optionCode"]
                        obj = {
                            "component": component,
                            "name": field_value["name"],
                            "value": field_value["value"],
                            "desc": field_value["desc"],
                            "part_number": part_number,
                            "adon_field_id": adon_field_id,
                            "adon_field_option_id": adon_field_option_id,
                            "is_manual": field_value["is_manual"],
                            "is_adon_field": field_value["is_adon_field"],
                            "has_price_dependancy": field_value["has_price_dependancy"],
                            "feature_code": field_value["featureCode"] if "featureCode" in field_value else None,
                            "option_code": field_value["optionCode"] if "optionCode" in field_value else None,
                            "schedule_id": schedule_id
                        }
                        original_request_data[field_name] = obj
                    elif field_value["is_adon_field"]:
                        adon_price_obj = {}
                        if "seriesCode" in field_value:
                            adon_price_obj["seriesCode"] = field_value["seriesCode"]
                        if "adonFeatureCode" in field_value and "optionCode" in field_value:
                            adon_price_obj[field_value["adonFeatureCode"]] = field_value["optionCode"]
                        adon_price_request_data.append(adon_price_obj)
                        obj = {
                            "component": component,
                            "name": field_value["name"],
                            "value": field_value["value"],
                            "desc": field_value["desc"],
                            "part_number": part_number,
                            "adon_field_id": adon_field_id,
                            "adon_field_option_id": adon_field_option_id,
                            "is_manual": field_value["is_manual"],
                            "is_adon_field": field_value["is_adon_field"],
                            "has_price_dependancy": field_value["has_price_dependancy"],
                            "feature_code": field_value["adonFeatureCode"] if "adonFeatureCode" in field_value else None,
                            "option_code": field_value["optionCode"] if "optionCode" in field_value else None,
                            "schedule_id": schedule_id

                        }
                        original_request_data[field_name] = obj
                else:
                    # in case of catalog field and sereis filed
                    obj = {
                        "component": component,
                        "name": field_value["name"],
                        "value": field_value["value"],
                        "desc": field_value["desc"],
                        "part_number": part_number,
                        "adon_field_id": adon_field_id,
                        "adon_field_option_id": adon_field_option_id,
                        "is_manual": field_value["is_manual"],
                        "is_adon_field": field_value["is_adon_field"],
                        "has_price_dependancy": field_value["has_price_dependancy"],
                        "schedule_id": schedule_id
                    }
                    original_request_data[field_name] = obj
            else:
                # in case of catalog field and sereis filed
                obj = {
                    "component": component,
                    "name": field_value["name"],
                    "value": field_value["value"],
                    "desc": field_value["desc"],
                    "part_number": part_number,
                    "adon_field_id": adon_field_id,
                    "adon_field_option_id": adon_field_option_id,
                    "is_manual": field_value["is_manual"],
                    "is_adon_field": field_value["is_adon_field"],
                    "has_price_dependancy": field_value["has_price_dependancy"],
                    "schedule_id": schedule_id
                }
                original_request_data[field_name] = obj
        return {"base_price": base_price_request_data, "adon_price": adon_price_request_data, "original_request_data": original_request_data}
    except Exception as e:
        logger.error(f"prepare_price_fetch_data:: General Exception: {str(e)}")
        raise e

async def post_process_price_data(
        db,
        manufacturer_code,
        brand_code,
        original_request_data,
        base_price,
        adon_prices,
        component
    ):
    try:
        request_data = []
        catalog_field_name = f"{component.lower()}_catalog"
        series_field_name = f"{component.lower()}_series"
        for field_name, field_data in original_request_data.items():
            if (field_name not in [catalog_field_name, series_field_name]) and field_data["has_price_dependancy"]:
                    if not field_data["is_adon_field"]:
                        quantity = 1
                        total_amount = base_price["pricePerQuantity"][0]["price"]
                        final_amount = total_amount * quantity
                        field_data["feature_data"] = base_price
                        field_data["price_data"] = base_price["pricePerQuantity"]
                        field_data["total_amount"] = total_amount
                        field_data["total_sell_amount"] = total_amount
                        field_data["total_base_amount"] = total_amount
                        field_data["total_extended_sell_amount"] = total_amount
                        field_data["final_amount"] = final_amount
                        field_data["final_sell_amount"] = final_amount
                        field_data["final_base_amount"] = final_amount
                        field_data["final_extended_sell_amount"] = final_amount
                        # request_data.append(field_data)
                    else:
                        if field_data["feature_code"] in adon_prices:
                            adon_price = adon_prices[field_data["feature_code"]]
                            quantity = 1
                            total_amount = adon_price["pricePerQuantity"][0]["price"]
                            final_amount = total_amount * quantity
                            field_data["feature_data"] = adon_price
                            field_data["price_data"] = adon_price["pricePerQuantity"]
                            field_data["total_amount"] = total_amount
                            field_data["total_sell_amount"] = total_amount
                            field_data["total_base_amount"] = total_amount
                            field_data["total_extended_sell_amount"] = total_amount
                            field_data["final_amount"] = final_amount
                            field_data["final_sell_amount"] = final_amount
                            field_data["final_base_amount"] = final_amount
                            field_data["final_extended_sell_amount"] = final_amount
                            # request_data.append(field_data)
                        else:
                            adon_field_option_data = (
                                db.query(AdonOpeningFieldOptions)
                                .get(field_data["adon_field_option_id"])
                            )
                            if not adon_field_option_data.is_default:
                                adon_price, adon_feature = await get_static_option_price(
                                    db,
                                    manufacturer_code,
                                    brand_code,
                                    base_price["seriesCode"],
                                    field_name,
                                    field_data["adon_field_id"],
                                    field_data["adon_field_option_id"],
                                )
                                if adon_price is not None and len(adon_price["data"]) > 0:
                                    adon_price = adon_price["data"][0]
                                    quantity = 1
                                    total_amount = adon_price["pricePerQuantity"][0]["price"]
                                    final_amount = total_amount * quantity
                                    field_data["feature_code"] = adon_feature["adonFeatureCode"]
                                    field_data["option_code"] = adon_feature["optionCode"]
                                    field_data["feature_data"] = adon_price
                                    field_data["price_data"] = adon_price["pricePerQuantity"]
                                    field_data["total_amount"] = total_amount
                                    field_data["total_sell_amount"] = total_amount
                                    field_data["total_base_amount"] = total_amount
                                    field_data["total_extended_sell_amount"] = total_amount
                                    field_data["final_amount"] = final_amount
                                    field_data["final_sell_amount"] = final_amount
                                    field_data["final_base_amount"] = final_amount
                                    field_data["final_extended_sell_amount"] = final_amount
                                    # request_data.append(field_data)
                            else:
                                quantity = 1
                                total_amount = 0
                                final_amount = total_amount * quantity
                                field_data["total_amount"] = total_amount
                                field_data["total_sell_amount"] = total_amount
                                field_data["total_base_amount"] = total_amount
                                field_data["total_extended_sell_amount"] = total_amount
                                field_data["final_amount"] = final_amount
                                field_data["final_sell_amount"] = final_amount
                                field_data["final_base_amount"] = final_amount
                                field_data["final_extended_sell_amount"] = final_amount
                                # request_data.append(field_data)
            request_data.append(field_data)
        return request_data
    except Exception as error:
        logger.error(f"post_process_price_data:: General Exception: {str(error)}")
        raise error

async def get_left_over_feature_data(db: Session, featureCode: str, schedule_id: str, component: str):
    try:
        left_over_filed_data = (
            db.query(ScheduleData)
            .filter(
                ScheduleData.name == featureCode,
                ScheduleData.component == component,
                ScheduleData.schedule_id == schedule_id
            )
            .first()
        )
        if left_over_filed_data:
            return left_over_filed_data.to_dict
        else:
            return None
    except Exception as error:
        logger.error(f"get_left_over_feature_data:: General Exception: {str(error)}")
        raise error


async def add_opening_data(db: Session, schedule_data: ScheduleDataBulkSaveSchema, current_member):
    """
    Add or update schedule data in the database.

    This function either adds a new schedule data entry or updates an existing one based 
    on the presence of the `id` field in the provided `schedule_data`.

    Args:
        db (Session): SQLAlchemy database session used to interact with the database.
        schedule_data (ScheduleDataRequest): The schedule data payload from the request body.

    Raises:
        ValueError: If the `id` field is provided but no matching record is found in the database.

    Returns:
        None: The function performs database operations and commits changes, but does not return any value.
    """
    try:
        schedule_data_dict = schedule_data.model_dump(exclude_unset=True)
        fields = schedule_data_dict.get('fields', {})
        component = schedule_data_dict.get('component')
        schedule_id = schedule_data_dict.get("schedule_id")
        part_number = schedule_data_dict.get("part_number", None)
        print("component:: ",component)
        request_data= await prepare_price_fetch_data(db, fields, component, schedule_id, part_number)
        original_request_data = request_data["original_request_data"]
        base_price_request_data = request_data["base_price"]
        adon_price_request_data = request_data["adon_price"]
        del request_data["original_request_data"]
        if (len(base_price_request_data.keys()) > 0) or (len(adon_price_request_data)):
            # In case we are performing operation for Frame or door as it will have something related to base price and adon price
            # print("request_data", request_data)
            response = await call_post_api("diamond/bulkprice/get_bulkprice", json.dumps(request_data))
            if int(response["status_code"]) == 200:
                resp_data = response["response"]["data"]
                left_over_feature_data = resp_data["left_over_feature_data"]
                base_price = resp_data["base_price"]
                adon_prices = resp_data["adon_prices"]
                if left_over_feature_data is not None:
                    # In case we need to have further selection to make in order to get the base price
                    selected_data = {}
                    for indx, elm in enumerate(left_over_feature_data):
                        if "_id" in elm:
                            left_over_feature_data[indx]["id"] = elm["_id"]
                            del left_over_feature_data[indx]["_id"]
                        left_over_selected_data = await get_left_over_feature_data(
                            db,
                            elm["featureCode"],
                            schedule_id,
                            component
                        )
                        if left_over_selected_data is not None:
                            selected_data[elm["featureCode"]] = left_over_selected_data
                    return JSONResponse(content={"message": "Need to select further information in order to get the base price", "data": left_over_feature_data, "selected_data": selected_data}, status_code=202)
                else:
                    # In case we dont have any pending field to be selected
                    if base_price is None:
                        return JSONResponse(content={"message": "Invalid Option selection"}, status_code=400)
                    else:
                        response_data = await post_process_price_data(
                            db,
                            base_price_request_data["manufacturerCode"],
                            base_price_request_data["brandCode"],
                            original_request_data,
                            base_price,
                            adon_prices,
                            component
                        )
                        final_resp = {}
                        if db.in_transaction():
                            # if there is an any active transaction then commit it
                            db.commit()
                        # Begin a transaction
                        with db.begin():
                            # delete all adon fields for the currect component of current schedule
                            old_data = (
                                db.query(ScheduleData)
                                .filter(
                                    ScheduleData.has_price_dependancy == True,
                                    ScheduleData.schedule_id == schedule_id,
                                    ScheduleData.component == component,
                                    ScheduleData.part_number == part_number
                                )
                                .first()
                            )
                            markup = old_data.markup if old_data else 0
                            margin = old_data.margin if old_data else 0
                            discount = old_data.discount if old_data else 0
                            surcharge = old_data.surcharge if old_data else 0
                            discount_type = old_data.discount_type if old_data else "PERCENTAGE"
                            surcharge_type = old_data.surcharge_type if old_data else "PERCENTAGE"
                            # print("markup, margin, discount, surcharge, discount_type, surcharge_type:: ",markup, margin, discount, surcharge, discount_type, surcharge_type)
                            (
                                db.query(ScheduleData)
                                .filter(
                                    ScheduleData.is_adon_field == True,
                                    ScheduleData.schedule_id == schedule_id,
                                    ScheduleData.component == component,
                                    ScheduleData.part_number == part_number
                                )
                                .delete()
                            )
                            for indx, elm in enumerate(response_data):
                                elm["markup"] = markup
                                elm["margin"] = margin
                                elm["discount"] = discount
                                elm["surcharge"] = surcharge
                                elm["discount_type"] = discount_type
                                elm["surcharge_type"] = surcharge_type
                                final_resp[elm["name"]] = elm
                                # print(indx, elm['name'])
                                # print("---------------------")
                                # print("elm:: ",elm)
                                existing_data = (
                                    db.query(ScheduleData)
                                    .filter(
                                        ScheduleData.schedule_id == schedule_id, 
                                        ScheduleData.name == elm["name"], 
                                        ScheduleData.component == elm["component"],
                                        ScheduleData.part_number == part_number
                                    )
                                    .first()
                                )
                                if existing_data:
                                    final_resp[elm["name"]]["id"] = existing_data.id
                                    for key, value in elm.items():
                                        setattr(existing_data, key, value)
                                    db.flush()
                                else:
                                    new_data = ScheduleData(**elm)
                                    db.add(new_data)
                                    db.flush()
                                    final_resp[elm["name"]]["id"] = new_data.id
                            if component == "FRAME":
                                await set_hardware_prep_data(db, schedule_id, component)
                            db.flush()
                            # set the price breakups depending on the discount , surcharge, markup, margin
                            await set_opening_breakups_to_schedule_data(db, schedule_id, component)
                            db.flush()
                            # Update the schedule stats
                            await update_schedule_stats(db, schedule_id)
                            db.flush()
                            db.commit()
                        return {"data": final_resp, "message": "Data Upserted successfull"}
            else:
                return JSONResponse(content={"message": "Unable to fetch pricebook data"}, status_code=int(response["status_code"]))
        else:
            final_resp = {}
            if db.in_transaction():
                # if there is an any active transaction then commit it
                db.commit()
            # Begin a transaction
            with db.begin():
                print("original_request_data:: ",original_request_data)
                for field_name, field_value in original_request_data.items():
                    old_prep_data = (
                        db.query(ScheduleData)
                        .filter(
                            ScheduleData.schedule_id == schedule_id, 
                            ScheduleData.component == component,
                            ScheduleData.part_number == part_number,
                            ScheduleData.name == field_name,
                            ScheduleData.latest_data == True
                        )
                        .first()
                    )
                    prep_id = None
                    if old_prep_data:
                        old_prep_data.value = field_value["value"]
                        prep_id = old_prep_data.id
                    else:
                        new_data = ScheduleData(**field_value)
                        db.add(new_data)
                        prep_id = new_data.id
                    db.flush()
                    final_resp[field_value["name"]] = field_value
                    final_resp[field_value["name"]]["id"] = prep_id
                if component == "FRAME":
                    await set_hardware_prep_data(db, schedule_id, component)
                    db.flush()
                    # set the price breakups depending on the discount , surcharge, markup, margin
                    await set_opening_breakups_to_schedule_data(db, schedule_id, component)
                    db.flush()
                # Update the schedule stats
                await update_schedule_stats(db, schedule_id)
                db.flush()
                db.commit()

            return {"data": final_resp, "message": "Data Upserted successfull"}
    except Exception as e:
        db.rollback()
        print(traceback.format_exc())
        logger.error(f"add_opening_data:: General Exception: {str(e)}")
        return JSONResponse(content={"message": str(e)}, status_code=500)
    finally:
        print("component:: ",component)
        # print((db, current_member, schedule_id, component, part_number))
        # Prepare compare between take-off-data and opening-data and insert into "opening_change_stats" table
        await compare_take_off_data(db, current_member, schedule_id, component, part_number)
    

async def upload_opening_file(db: Session, schedule_id: str, file: UploadFile):
    """
    Upload a file to S3 and update the corresponding schedule record in the database.

    This function uploads the provided file to an S3 bucket, updates the `frame_section_file_path` 
    and `frame_section_file_type` fields in the database for the specified opening ID, 
    and commits the changes.

    Args:
        db (Session): SQLAlchemy database session used to query and update the database.
        schedule_id (str): The ID of the schedule to which the file is associated.
        file (UploadFile): The file object to be uploaded.

    Returns:
        dict: A dictionary containing a success message and the file path if the operation is successful.
              If an error occurs, the dictionary contains an error message.

    Raises:
        ValueError: If no schedule record is found for the provided opening ID.
        Exception: For any general exceptions that occur during the process.
    """
    try:
        # Query the schedule info from the database
        schedule_info = db.query(Schedules).filter(Schedules.id == schedule_id).first()
        if not schedule_info:
            raise ValueError(f"No record found with ID: {schedule_id}")
        
        # Prepare the upload path
        upload_path = f"opening_document/{schedule_info.project_id}/{schedule_info.id}"
        
        # Call the upload_to_s3 function to upload the file
        file_path = await upload_to_s3(file, upload_path)

        # Delete the existing file from S3, if any
        if schedule_info.frame_section_file_path:
            await delete_from_s3(schedule_info.frame_section_file_path)
            
        # Update the frame_section_file_path in the database
        schedule_info.frame_section_file_path = file_path
        schedule_info.frame_section_file_type = file.content_type
        
        db.commit()  # Commit the changes to persist in the database
        
        logger.info(f"File uploaded successfully to S3: {get_aws_full_path(file_path)}")
        return {"message": "File uploaded successfully", "file_path": get_aws_full_path(file_path)}
    
    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        return {"error": str(e)}
    
    except Exception as e:
        logger.error(f"General Exception: {str(e)}")
        return {"error": str(e)}
    


async def delete_schedule(db: Session, schedule_id: str):
    """
    Deletes a schedule and its related records from the database by its schedule_id.

    Args:
        db (Session): Database session.
        schedule_id (str): The unique ID of the schedule to delete.

    Returns:
        dict: Success message or error message.
    """
    try:
        # Start a database transaction
        with db.begin():
            logger.info(f"Attempting to delete schedule with ID: {schedule_id}")

            # Fetch the schedule by its ID
            schedule = db.query(Schedules).filter(Schedules.id == schedule_id).first()

            if not schedule:
                logger.warning(f"Schedule with ID {schedule_id} not found.")
                return JSONResponse(content={"message": "Schedule not found"}, status_code=404)
            
            if schedule.frame_section_file_path:
                logger.info(f"Deleting file from S3: {schedule.frame_section_file_path}")
                await delete_from_s3(schedule.frame_section_file_path)

            # Delete related records from ScheduleData
            db.query(ScheduleData).filter(ScheduleData.schedule_id == schedule_id).delete()
            logger.info(f"Deleted related ScheduleData for schedule ID: {schedule_id}")

            # Delete related records from ScheduleOpeningHardwareMaterials
            db.query(ScheduleOpeningHardwareMaterials).filter(
                ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
            ).delete()
            logger.info(f"Deleted related ScheduleOpeningHardwareMaterials for schedule ID: {schedule_id}")

            # Delete the schedule itself
            db.delete(schedule)

            logger.info(f"Successfully deleted schedule with ID: {schedule_id}")

            return {"message": "Schedule and related records deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting schedule with ID {schedule_id}: {str(e)}")
        raise e


async def get_schedule_data(
    db: Session,
    schedule_id: str,
    opening_type: str,
    part_number: str
):
    """
    Fetch schedule data based on `schedule_id` and optional `component` & part_number.
    """
    try:
        query = db.query(ScheduleData).filter(ScheduleData.schedule_id == schedule_id, ScheduleData.latest_data == True)
        
        if opening_type:
            query = query.filter(ScheduleData.component == opening_type)
        
        if part_number:
            query = query.filter(ScheduleData.part_number == part_number)

        schedule_data = query.all()

        response = [
            ScheduleDataRes(
                id=item.id,
                name=item.name,
                desc=item.desc,
                value=item.value,
                component=item.component.value if hasattr(item.component, "value") else item.component,
                part_number=item.part_number if item.part_number is not None else None,
                feature_code=item.feature_code,
                option_code=item.option_code,
                feature_data=item.feature_data,
                price_data=item.price_data,
                additional_data=item.additional_data,
                total_amount=item.total_amount,
                total_sell_amount=item.total_sell_amount,
                total_base_amount=item.total_base_amount,
                total_extended_sell_amount=item.total_extended_sell_amount,
                quantity=item.quantity,
                final_amount=item.final_amount,
                final_sell_amount=item.final_sell_amount,
                final_base_amount=item.final_base_amount,
                final_extended_sell_amount=item.final_extended_sell_amount,
                markup=item.markup or 0,
                margin=item.margin or 0,                          
                is_basic_discount=item.is_basic_discount,        
                discount=item.discount,
                discount_type=item.discount_type.value if hasattr(item.discount_type, "value") else item.discount_type,
                surcharge=item.surcharge,
                surcharge_type=item.surcharge_type.value if hasattr(item.surcharge_type, "value") else item.surcharge_type,
                adon_field_id=item.adon_field_id,
                adon_field_option_id=item.adon_field_option_id,
                schedule_id=item.schedule_id,
                is_manual=item.is_manual,
                is_table_data=item.is_table_data,
                is_adon_field=item.is_adon_field,
                has_price_dependancy=item.has_price_dependancy,
                # Optional system fields
                # is_active=item.is_active,
                # created_at=item.created_at.strftime("%d/%m/%Y %H:%M:%S") if item.created_at else None,
                # updated_at=item.updated_at.strftime("%d/%m/%Y %H:%M:%S") if item.updated_at else None,
            ).model_dump()
            for item in schedule_data
        ]

        return {
            "data": response,
            "component": opening_type,
            "part_number": part_number,
            "message": "Data fetch successful",
        }

    except Exception as e:
        print(traceback.format_exc())
        logger.error(f"get_schedule_data:: Error fetching schedule with ID {schedule_id}: {str(e)}")
        raise e



async def get_comparison_opening_stats(
    db: Session,
    schedule_id: str
):
    """
    Retrieve comparison statistics for opening changes based on the provided schedule ID.

    This function fetches data from the `opening_change_stats` table using the given 
    `schedule_id`, and returns detailed change information for each opening entry.

    Args:
        db (Session): The database session/connection.
        schedule_id (str): The unique identifier of the schedule for which 
                           opening change stats are to be fetched.

    Returns:
        dict: A dictionary containing the fetched data and a success message.

    Raises:
        Exception: If any error occurs during the data fetch process.
    """
    try:
        response, message = await comparison_opening_data(db,schedule_id)

        return {"data": response, "message": message}

    except Exception as e:
        print(traceback.format_exc())
        logger.error(f"get_comparison_opening_stats:: Error get_comparison_opening_stats schedule with ID {schedule_id}: {str(e)}")
        raise e



async def get_opening_feature_fields(
    db: Session, 
    opening_type: str, 
    manufacturer_code: str, 
    brand_code: str,
    series_code: str,
):
    try:
        # Base query
        query = (
            db.query(AdonOpeningFields)
            .filter(
                AdonOpeningFields.is_adon_field == False,
                AdonOpeningFields.has_price_dependancy == True,
                AdonOpeningFields.field_category.like("%OPENING_SCHEDULE%")
            )
        )

        # Add filters based on opening type
        if opening_type == "DOOR":
            query = query.filter(AdonOpeningFields.is_door_data == True)
        elif opening_type == "FRAME":
            query = query.filter(AdonOpeningFields.is_frame_data == True)
        elif opening_type == "HARDWARE":
            query = query.filter(AdonOpeningFields.is_hw_data == True)
        elif opening_type == "OPENING":
            query = query.filter(AdonOpeningFields.is_opening_data == True)

        # Execute query and fetch results
        result = query.all()

        # Prepare data
        requestFieldKeywords = {}
        catalog_field = f"{opening_type}_catalog"
        series_field = f"{opening_type}_series"

        for item in result:
            # Add the field to the dictionary if it doesn't contain "catalog" or "series"
            if item.name not in [series_field, catalog_field]:
                keywords = item.search_keywords  # Start with the main field's keywords
                if item.adon_field_options and len(item.adon_field_options) > 0:
                    # Append the keywords from the related `adon_field_options`
                    option_keywords = ",".join(res.search_keywords for res in item.adon_field_options if res.search_keywords)
                    keywords = f"{keywords},{option_keywords}" if keywords else option_keywords
                requestFieldKeywords[item.name] = keywords
        filed_data = []
        if len(requestFieldKeywords.keys()) > 0:
            request_data = {
                "manufacturerCode": manufacturer_code,
                "brandCode": brand_code,
                "seriesCode": series_code,
                "requestFieldKeywords": requestFieldKeywords
            }
            # print("Request data:::::::::", request_data)
            response = await call_post_api("diamond/bulkprice/get_all_base_field_options", json.dumps(request_data))
            # print("Response::::::::::::::", json.dumps(response))
            if int(response["status_code"]) == 200:
                resp_data = response["response"]["data"]
                for field, filed_options in resp_data.items():
                    print("filed_options", filed_options[0]['featureCode'])
                    isFieldExists = (
                        db.query(AdonOpeningFields)
                        .filter(
                            AdonOpeningFields.name == field
                        )
                        .first()
                    )
                    obj = {
                        "id": None,
                        "featureCode": field,
                        "name": filed_options[0]['featureCode'],
                        "desc": field,
                        # "featureCode": filed_options['featureCode'],
                        "has_price_dependancy": True,
                        "field_type": "DROPDOWN",
                        "field_category": "OPENING_SCHEDULE",
                        "rule": [],
                        "is_adon_field": False,
                        "field_options": None,
                        "pricebook_options": filed_options,
                    }
                    if isFieldExists:
                        obj["id"] = isFieldExists.id
                        obj["desc"] = isFieldExists.desc
                        obj["field_type"] = str(isFieldExists.field_type.value)
                        obj["field_category"] = isFieldExists.field_category
                        obj["rule"] = isFieldExists.rule
                        obj["is_adon_field"] = isFieldExists.is_adon_field
                    filed_data.append(obj)

        # Perform sorting based on availability criteria.
        filed_data = sort_by_availability_criteria(filed_data)

        # Return successful JSON response
        return JSONResponse(
            status_code=200,
            content={"status": "success", "data": filed_data}
        )
    except SQLAlchemyError as e:
        # Handle database-related errors
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "A database error occurred.",
                "details": str(e),
            }
        )
    
    except Exception as e:
        # Handle other exceptions
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An unexpected error occurred.",
                "details": str(e),
            }
        )
    

# def check_dependency(feature, all_features):
#     feature_name = feature['name']
#     for option in feature['pricebook_options']:
#         for criteria in option.get('availabilityCriteria', []):
#             for key in criteria.keys():
#                 if key in [f['name'] for f in all_features]:
#                     return True  # Dependency found
#     return False  # No dependency


# def sort_by_availability_criteria(data):

#     # Sort features based on dependency (dependent features come after their dependencies)
#     sorted_data = sorted(data, key=lambda feature: check_dependency(feature, data))
#     # print(json.dumps(sorted_data))
#     return sorted_data

# Function to count total availability criteria objects for a feature
def count_availability_criteria(feature):
    pricebook_options = feature.get('pricebook_options', [])

    if not pricebook_options:  # Check if pricebook_options is empty
        return 0
    
    option = pricebook_options[0]
    availability_criteria = option.get('availabilityCriteria', [])
    count = sum(len(criteria) for criteria in availability_criteria)
    return count

def sort_by_availability_criteria(data):
    # Sort features by number of availabilityCriteria (ascending order)
    sorted_data = sorted(data, key=count_availability_criteria)
    return sorted_data


async def create_adon_opening_field(
    db: Session,
    payload: AdonOpeningFieldCreateSchema
):
    """
    Controller: Create a new AdonOpeningField.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            response = await schedule_repositories.create_adon_opening_field(db, payload)
            return JSONResponse(
                status_code=201,
                content={
                    "data": response,
                    "message": "Adon Opening Field created successfully"
                }
            )
    except Exception as e:
        print(traceback.format_exc())
        logger.error(f"create_adon_opening_field:: Error while creating field {payload.name}: {str(e)}")
        raise e