"""
This file contains all the controller operations related to take-off sheet items.
"""
from loguru import logger
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.project_take_off_sheet_sections import ProjectTakeOffSheetSections
from models.project_take_off_sheet_section_areas import ProjectTakeOffSheetSectionAreas
from models.opening_schedules import OpeningSchedules
from models.project_materials import ProjectMaterials
from models.hardware_group_materials import HardwareGroupMaterials
from models.hardware_groups import HardwareGroups
from models.sections import Sections
from models.schedules import Schedules
from models.schedule_data import ScheduleData
from models.opening_hardware_materials import OpeningHardwareMaterials
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from repositories.take_off_sheet_repositories import get_door_count_mapping
from repositories.update_stats_repositories import update_opening_schedule_stats, update_area_item_stats, update_section_stats, update_take_off_sheet_stats, update_raw_material_stats
from repositories.take_off_sheet_repositories import delete_opening, clone_sheet_area_item, is_opening_number_exists
from models.adon_opening_fields import AdonOpeningFields
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.hardware_product_category import HardwareProductCategory
from fastapi.responses import JSONResponse
import functools
from sqlalchemy.orm import Session
from schemas.take_off_sheet_item_schema import TakeOffSheetItem, TakeOffSheetCloneRequest
from models.members import Members
from typing import Optional
import math
from starlette import status
from utils.common import upload_to_s3, delete_from_s3, download_from_s3, get_aws_full_path
from fastapi import HTTPException
import os
import traceback

async def get_adon_opening_fileds(db: Session):
    """**summary**
    This method is responsible for fetching all adon fileds for openings.

    **Args:**
    - `db` (Session): The database session.

    **Returns:**
    - item_data: it will return the item details of a area item.
    """
    try:
        item_data = (
            db.query(AdonOpeningFields)
            .join(AdonOpeningFieldOptions)
            .filter(
                AdonOpeningFields.is_active == True,
                AdonOpeningFields.field_category.ilike("%TAKE_OFF_SHEET%")
            )
            .all()
        )
        resp = []
        for item in item_data:
            item_info = item.to_dict
            item_info["adon_field_options"] = item.adon_field_options
            resp.append(item_info)

        return {"data": item_data, "message": "Data Fetch Successfully.", "status": "success"}
    except Exception as error:
        logger.exception(f"get_adon_opening_fileds:: An unexpected error occurred: {error}")
        raise error


async def get_take_off_sheet_item_details(item_id: str, db: Session):
    """**summary**
    This method is responsible for fetching item details of an item.

    **Args:**
    - item_id (str): item id for which we want to get all details.
    - `db` (Session): The database session.

    **Returns:**
    - item_data: it will return the item details of a area item.
    """
    try:
        item_data = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.id == item_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .one()
        )
        return {"data": item_data, "message": "Data Fetch Successfully.", "status": "success"}
    except Exception as error:
        logger.exception(f"get_take_off_sheet_item_details:: An unexpected error occurred: {error}")
        raise error


async def get_take_off_sheet_area_items(take_off_sheet_area_id: str, db: Session):
    """**Summary:**
    This module is responsible for getting all of the items for an take off sheet area.

    **Args:**
    - take_off_sheet_area_id (str): take off sheet area id.
    - `db` (Session): The database session.

    **Return:**
    - `data` (dict): A dictionary containing all sheet area items data.
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        item_data = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_area_id == take_off_sheet_area_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .order_by(ProjectTakeOffSheetSectionAreaItems.created_at.asc())
            .all()
        )
        response = []
        for data in item_data:
            data_dict = data.to_dict
            response.append(data_dict)

        return {"data": response, "message": "Data Fetch Successfully.", "status": "success"}
    except Exception as error:
        logger.exception(f"get_take_off_sheet_area_items:: An unexpected error occurred: {error}")
        raise error



async def get_project_openings(project_id: str, keyword: str, db: Session):
    """**Summary:**
    This module is responsible for getting all of the openings for a project.

    **Args:**
    - project_id (str): project id for which we need to have the list of openings.
    - `db` (Session): The database session.

    **Return:**
    - `data` (dict): A dictionary containing all sheet area items data.
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        openings = []
        take_off_sheet_data = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.project_id == project_id,
                ProjectTakeOffSheets.is_deleted == False
            )
            .all()
        )
        if len(take_off_sheet_data) > 0:
            schedule_openings = (
                db.query(Schedules.take_off_area_item_id)
                .filter(
                    Schedules.project_id == project_id,
                    Schedules.is_active == True,
                    Schedules.take_off_area_item_id != None
                )
                .all()
            )
            schedule_opening_ids = [elm[0] for elm in schedule_openings]
            openings = (
                db.query(ProjectTakeOffSheetSectionAreaItems)
                .filter(
                    ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_sheet_data[0].id,
                    ProjectTakeOffSheetSectionAreaItems.is_deleted == False
                )
                .order_by(ProjectTakeOffSheetSectionAreaItems.created_at.asc())
            )
            if keyword:
                openings = openings.filter(ProjectTakeOffSheetSectionAreaItems.opening_number.ilike(f'%{keyword}%'))
            
            openings = openings.all()
        response = []
        for data in openings:
            if data.id not in schedule_opening_ids:
                data_dict = data.to_dict
                data_dict['area_info'] = data.take_off_sheet_section_area
                response.append(data_dict)

        return {"data": response, "message": "Data Fetch Successfully.", "status": "success"}
    except Exception as error:
        logger.exception(f"get_take_off_sheet_area_items:: An unexpected error occurred: {error}")
        raise error


async def add_take_off_sheet_item(
    take_off_sheet_item_req_data: TakeOffSheetItem, 
    current_member: Members, 
    db: Session
    ):
    """**Summary:**
    This module is responsible for creating an area item in take off sheet.

    **Args:**
    - take_off_sheet_item_req_data (dict): take off sheet item create data.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `take_off_sheet_item_id` (str): created take off sheet item id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            take_off_sheet_item_req_data = take_off_sheet_item_req_data.model_dump(exclude_unset=True)
            take_off_sheet_item_req_data['created_by'] = current_member.id
            project_take_off_sheet_id = take_off_sheet_item_req_data["project_take_off_sheet_id"]
            opening_number = take_off_sheet_item_req_data["opening_number"]
            project_takeoffsheet_section_area_opening_exist = await is_opening_number_exists(project_take_off_sheet_id, opening_number, db)
            
            door_type_id = take_off_sheet_item_req_data['adon_fields']['door_type']
            id_to_count_mappings, _ = await get_door_count_mapping(db)
            if door_type_id not in id_to_count_mappings:
                raise Exception("Invalid door_type")
            door_count = id_to_count_mappings[door_type_id]
            take_off_sheet_item_req_data['door_width'], take_off_sheet_item_req_data['door_height'] = [ ",".join(["_"] * door_count) ] * 2

            if not project_takeoffsheet_section_area_opening_exist:
                item_data = ProjectTakeOffSheetSectionAreaItems(**take_off_sheet_item_req_data)
                db.add(item_data)
                db.flush()
                project_take_off_sheet_section_area_item_id = item_data.id
                return {"id": project_take_off_sheet_section_area_item_id, "message": "Area item Added.", "status": "success"}
            else:
                return JSONResponse(content={"message": "Opening Number already exists in the current Section"}, status_code=400)
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def delete_take_off_sheet_item(id: str, current_member: Members, db: Session):
    """**Summary:**
    This module is responsible for deleting an item for a take off sheet.

    **Args:**
    - id (str): take off sheet item id to be deleted.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

        - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
        
            project_takeoffsheet_item_exist = db.query(ProjectTakeOffSheetSectionAreaItems).filter(ProjectTakeOffSheetSectionAreaItems.id == id, ProjectTakeOffSheetSectionAreaItems.is_deleted == False).first()
            if project_takeoffsheet_item_exist:
                project_take_off_sheet_section_id = project_takeoffsheet_item_exist.project_take_off_sheet_section_id
                await delete_opening(id, current_member, db)

                #update the section stats after deleting the section area and its associated openings
                await update_section_stats(db, project_take_off_sheet_section_id = project_take_off_sheet_section_id)

                #update the sheet stats after deleting the section area and its associated openings
                await update_take_off_sheet_stats(db,project_take_off_sheet_id= project_takeoffsheet_item_exist.project_take_off_sheet_id)

                project_take_off_data = (
                    db.query(ProjectTakeOffSheets)
                    .filter(
                        ProjectTakeOffSheets.id == project_takeoffsheet_item_exist.project_take_off_sheet_id
                    )
                    .first()
                )
                
                #update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(db,project_id= project_take_off_data.project_id)

                return {"message": "Data deleted successfully.", "status": "success"}
            else:
                return JSONResponse(content={"message": "Item not found"}, status_code=400)
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    


async def update_take_off_sheet_item(
    take_off_sheet_item_id: str, 
    take_off_sheet_item_req_data: TakeOffSheetItem, 
    current_member: Members, 
    db: Session
):
    """**Summary:**
    Update an existing item in the take-off sheet section area.

    **Args:**
    - take_off_sheet_item_id (str): The ID of the take-off sheet item to be updated.
    - take_off_sheet_item_req_data (dict): take off sheet item update data.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    -  dict: A dictionary containing the message and status of the update operation.
    - 'message' (str): A message indicating the result of the operation.
    - 'status' (str): The status of the update operation ('success' or 'failure').
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            valid_opening_number = True
            item = db.query(ProjectTakeOffSheetSectionAreaItems).filter(ProjectTakeOffSheetSectionAreaItems.id==take_off_sheet_item_id, ProjectTakeOffSheetSectionAreaItems.is_deleted == False).first()
            if item:
                take_off_sheet_item_req_data = take_off_sheet_item_req_data.model_dump(exclude_unset=True)
                if "opening_number" in take_off_sheet_item_req_data and str(take_off_sheet_item_req_data["opening_number"]) != str(item.opening_number):
                    #In case user is trying to update the opening number of the current item
                    opening_number = take_off_sheet_item_req_data["opening_number"]
                    project_takeoffsheet_section_area_opening_exist = await is_opening_number_exists(item.project_take_off_sheet_id, opening_number, db)
                    if project_takeoffsheet_section_area_opening_exist: 
                        # In case the user input of opening number is already exists in the current section area,
                        # then make the opennig number invalid
                        valid_opening_number = False 
                if valid_opening_number:               
                    # Handle Door Width & Height Update                                 
                    id_to_count_mapping, _ = await get_door_count_mapping(db)
                    old_door_type, new_door_type = item.adon_fields['door_type'], take_off_sheet_item_req_data['adon_fields']['door_type']
                    old_door_count, new_door_count = id_to_count_mapping[old_door_type], id_to_count_mapping[new_door_type]
                    if new_door_count > old_door_count:
                        # Step Up Count, we can simple append underscores as required
                        diff = new_door_count - old_door_count
                        postfix = "," + ",".join(["_"] * diff)
                        take_off_sheet_item_req_data['door_width'], take_off_sheet_item_req_data['door_height'] = item.door_width + postfix, item.door_height + postfix
                    elif new_door_count < old_door_count:
                        # Step Down Count, Only possible if we have enough empty slots
                        diff = old_door_count - new_door_count
                        empty_slots = item.door_width.count("_")
                        if empty_slots >= diff:
                            can_remain_empty_count = empty_slots - diff
                            take_off_sheet_item_req_data['door_width'] = ",".join(functools.reduce(lambda acc, cur: acc + [cur] if cur != "_" or acc.count("_") < can_remain_empty_count else acc, item.door_width.split(","), []))
                            take_off_sheet_item_req_data['door_height'] = ",".join(functools.reduce(lambda acc, cur: acc + [cur] if cur != "_" or acc.count("_") < can_remain_empty_count else acc, item.door_width.split(","), []))
                        else:
                            raise Exception("Unable to reduce door type!, remove " + str(diff) + " " + ("door" if diff == 1 else "doors") + " from the opening first!")

                    # Update existing client data
                    take_off_sheet_item_req_data['updated_by'] = current_member.id
                    # Update the attributes of the existing client with the values from the client_data dictionary.
                    for key, value in take_off_sheet_item_req_data.items():
                        setattr(item, key, value)
                    if "quantity" in take_off_sheet_item_req_data:

                        # update the area item stats
                        take_off_sheet_section_id = await update_area_item_stats(db, project_take_off_sheet_section_area_item_id=take_off_sheet_item_id)

                        project_take_off_sheet_area_item_data = (
                            db.query(ProjectTakeOffSheetSectionAreaItems)
                            .filter(
                                ProjectTakeOffSheetSectionAreaItems.id == take_off_sheet_item_id
                            )
                            .first()
                        )
                        # Update section statistics related to the hardware group
                        await update_section_stats(
                            db,
                            project_take_off_sheet_section_id = take_off_sheet_section_id
                        )
                        #update the sheet stats after deleting the section area and its associated openings
                        await update_take_off_sheet_stats(db,project_take_off_sheet_id= project_take_off_sheet_area_item_data.project_take_off_sheet_id)

                        project_take_off_sheet_data = (
                            db.query(ProjectTakeOffSheets)
                            .filter(
                                ProjectTakeOffSheets.id == project_take_off_sheet_area_item_data.project_take_off_sheet_id
                            )
                            .first()
                        )

                        #update the raw material stats after deleting the section area and its associated openings
                        await update_raw_material_stats(db,project_id= project_take_off_sheet_data.project_id)

                    return {"message": "Area item Updated.", "status": "success"}
                else:
                    return JSONResponse(content={"message": "Opening Number already exists in the current area"}, status_code=400)
            else:
                return JSONResponse(content={"message": "Item not found"}, status_code=400)
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    


async def get_associate_item(db: Session, take_off_sheet_area_item_id: str, material_type: str):
    """**Summary:**
    Fetches associated items based on the given project take-off sheet area item ID and material type.

    Parameters:
        - db (Session): SQLAlchemy database session.
        - take_off_sheet_area_item_id (str): ID of the project take-off sheet area item.
        - material_type (str): Type of material, e.g., 'HARDWARE' or other.

    Returns:
        dict: A dictionary containing the fetched data.
              - If material_type is 'HARDWARE', the dictionary includes details about hardware items.
              - If material_type is not 'HARDWARE', the dictionary includes details about opening schedules.
    """
    try:
        # Fetch opening schedule data based on the provided parameters
        opening_schedule_data = (
            db.query(OpeningSchedules)
            .filter(
                OpeningSchedules.project_take_off_sheet_section_area_item_id == take_off_sheet_area_item_id,
                OpeningSchedules.component == material_type
            )
            .all()
        )

        # if not opening_schedule_data:
        #     return JSONResponse(content={"message": "No Hardware Material Associated with this Opening"})
        
        response = []
        # Handle logic for 'HARDWARE' material type
        if material_type == "HARDWARE":
            for opening_schedule_info in opening_schedule_data:
                # Fetch additional data related to hardware items
                item_data = (
                    db.query(ProjectMaterials)
                    .join(HardwareGroupMaterials)
                    .filter(
                        HardwareGroupMaterials.hardware_group_id == opening_schedule_info.hardware_group_id,
                        ProjectMaterials.is_deleted == False
                    )
                    .order_by(HardwareGroupMaterials.created_at.desc())
                    .all()
                )
                hw_group_data = db.query(HardwareGroups).get(opening_schedule_info.hardware_group_id)
                
                group_material_info = {"group_info": hw_group_data.to_dict}
                # Process each hardware item and add details to the response
                material_info = []
                for data in item_data:
                    data_dict = data.to_dict

                    # Find matching entries in material groups
                    matching_entries = []
                    for item in data.material_groups:
                        if item.hardware_group_id == opening_schedule_info.hardware_group_id:
                            matching_entries.append(item)
                            break
                    
                    # Add additional details to the data_dict
                    data_dict['hardware_group_id'] = opening_schedule_info.hardware_group_id
                    data_dict['quantity'] = matching_entries[0].quantity
                    data_dict['final_amount'] = matching_entries[0].final_amount
                    data_dict['final_base_amount'] = matching_entries[0].final_base_amount
                    data_dict['final_sell_amount'] = matching_entries[0].final_sell_amount
                    data_dict['final_extended_sell_amount'] = matching_entries[0].final_extended_sell_amount
                    data_dict['manufacturer_code'] = data.material_manufacturer.code
                    data_dict['brand_code'] = data.material_brand.code if data.material_brand else None
                    material_info.append(data_dict)

                group_material_info['material_info'] = material_info
                response.append(group_material_info)
        else:
            # Handle logic for material types other than 'HARDWARE'
            for data in opening_schedule_data:
                data_dict = data.to_dict
                data_dict['file'] = {
                    'file_name': data.opening_material.content_file_name, 
                    'file_path': get_aws_full_path(data.opening_material.content_file_path),
                    'file_type': data.opening_material.content_file_type
                } if data.opening_material.content_file_path is not None else None
                data_dict['description'] = data.opening_material.desc
                data_dict['series'] = data.opening_material.series
                data_dict['manufacturer_code'] = data.opening_material.material_manufacturer.code if data.opening_material.has_pricebook else None
                data_dict['brand_code'] = data.opening_material.material_brand.code if data.opening_material.material_brand else None
                
                # Edit Purpose Requirement
                data_dict['manufacturer_id'] = data.opening_material.manufacturer_id
                data_dict['brand_id'] = data.opening_material.brand_id
                data_dict['base_price'] = data.opening_material.base_price
                data_dict['adon_price'] = data.opening_material.adon_price
                data_dict['base_feature'] = data.opening_material.base_feature
                data_dict['adon_feature'] = data.opening_material.adon_feature
                data_dict['material_type'] = data.opening_material.material_type
                data_dict['selected_unit'] = data.opening_material.selected_unit
                data_dict['short_code'] = data.opening_material.short_code if data.opening_material.short_code else None
                response.append(data_dict)
        
        # Return the final response dictionary
        return {"data": response, "message": "Data Fetch Successfully.", "status": "success"}
    
    except Exception as error:
        # Log and raise an exception in case of an unexpected error
        logger.exception(f"get_associate_item:: An unexpected error occurred: {error}")
        raise error


async def clone_opening(
    db: Session, 
    take_off_sheet_area_item_id: str, 
    current_member: Members, 
    request_data: TakeOffSheetCloneRequest
):
    """**Summary:**
    Clones an existing item in the ProjectTakeOffSheetSectionAreaItems table along with its related OpeningSchedules.

    Parameters:
        db: SQLAlchemy database session.
        take_off_sheet_area_item_id (int): The ID of the item to be cloned.
        current_member: The current member performing the action.
        request_data: Request data containing the new item information.

    Returns:
        JSONResponse: A JSON response indicating the success or failure of the operation.
    """
    try:
        # Exclude unset fields from the request data
        request_data = request_data.model_dump(exclude_unset=True)
        take_off_sheet_section_area_id = None
        take_off_sheet_section_id = None
        # Fetch the item data based on the provided ID
        item_data = (
                db.query(ProjectTakeOffSheetSectionAreaItems)
                .filter(
                    ProjectTakeOffSheetSectionAreaItems.id == take_off_sheet_area_item_id,
                    ProjectTakeOffSheetSectionAreaItems.is_deleted == False
                )
                .first()
            )
        if not item_data:
            return JSONResponse(content={"message": "Invalid request."}, status_code=400)
        
        # Convert item data to dictionary
        item_data = item_data.to_dict

        # Check if 'opening_number' is provided in the request data
        if not 'opening_number' in request_data:
            return JSONResponse(content={"message": "Something went wrong."}, status_code=400)

        # Check if the provided opening number already exists
        is_opening_exists = await is_opening_number_exists(item_data['project_take_off_sheet_id'], request_data['opening_number'], db)
        if is_opening_exists:
            return JSONResponse(content={"message": "Opening Number already exists."}, status_code=400)
        # check if there is take_off_sheet_section_id passed in the request or not if yes then take that otherwise consider the area item will be clonned into same section.
        if "project_take_off_sheet_section_id" in request_data and request_data["project_take_off_sheet_section_id"] is not None:
            take_off_sheet_section_id = request_data["project_take_off_sheet_section_id"]
        else:
            take_off_sheet_section_id = item_data["project_take_off_sheet_section_id"]
        
        # check if there is take_off_sheet_section_area_id passed in the request or not if yes then take that otherwise consider the area item will be clonned into same section area.
        if "project_take_off_sheet_section_area_id" in request_data and request_data["project_take_off_sheet_section_area_id"] is not None:
            take_off_sheet_section_area_id = request_data["project_take_off_sheet_section_area_id"]
        else:
            take_off_sheet_section_area_id = item_data["project_take_off_sheet_section_area_id"]

        # Do the clonning process
        await clone_sheet_area_item(
            db=db,
            old_opening_data=item_data,
            take_off_sheet_section_area_id=take_off_sheet_section_area_id,
            take_off_sheet_section_id=take_off_sheet_section_id,
            opening_number=request_data['opening_number'],
            current_member=current_member
        )
        
        # Return the response data along with the operation status
        return {"message": "Data Clonned Successfully", "status": "success"}
    except Exception as error:
        # Log and raise an exception in case of an unexpected error
        logger.exception(f"clone_opening:: An unexpected error occurred: {error}")
        raise error



async def get_take_off_sheet_items(
    project_id: str,
    opening_number: str,
    db: Session,
    page: Optional[int] = None,
    page_size: Optional[int] = None
):
    """
    Retrieves specific fields for items within a take-off sheet area with optional pagination.

    **Args:**
    - project_id (str): The unique identifier for the project.
    - opening_number (str): The opening number for the specified area within the take-off sheet.
    - db (Session): The database session.
    - page (int, optional): The page number for pagination. Defaults to None (no pagination).
    - page_size (int, optional): The number of items per page. Defaults to None (no pagination).

    **Returns:**
    - dict: A dictionary containing the selected fields of sheet area items, page count, item count, and a success message.
    """
    try:
        # Check if the project_take_off_sheet exists for the given project_id
        project_take_off_sheet = db.query(ProjectTakeOffSheets).filter(
            ProjectTakeOffSheets.project_id == project_id
        ).first()

        if not project_take_off_sheet:
            return JSONResponse(
                content={"message": "No take-off sheet found for the provided project ID."},
                status_code=status.HTTP_404_NOT_FOUND
            )

        item_data_query = (
            db.query(
                ProjectTakeOffSheetSectionAreaItems.id,
                ProjectTakeOffSheetSectionAreaItems.opening_number,
                ProjectTakeOffSheetSectionAreaItems.desc,
                ProjectTakeOffSheetSectionAreaItems.door_height,
                ProjectTakeOffSheetSectionAreaItems.door_width,
                ProjectTakeOffSheetSectionAreaItems.door_raw_material_type,
                ProjectTakeOffSheetSectionAreaItems.frame_raw_material_type,
                ProjectTakeOffSheetSectionAreaItems.installation_charge,
                ProjectTakeOffSheetSectionAreaItems.adon_fields,
                ProjectTakeOffSheetSectionAreas.name.label("section_area_name"),
                Sections.name.label("section_name")
                )
            .join(
                ProjectTakeOffSheetSections, 
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_id == ProjectTakeOffSheetSections.id
            )
            .join(
                Sections,
                ProjectTakeOffSheetSections.section_id == Sections.id
            )
            .join(
                ProjectTakeOffSheetSectionAreas, 
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_area_id == ProjectTakeOffSheetSectionAreas.id
            )
            .join(OpeningSchedules, 
                  OpeningSchedules.project_take_off_sheet_section_area_item_id == ProjectTakeOffSheetSectionAreaItems.id
            )
            .filter(
                OpeningSchedules.component == "DOOR",
                ProjectTakeOffSheetSectionAreaItems.total_amount != None,
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == project_take_off_sheet.id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .group_by(ProjectTakeOffSheetSectionAreaItems.id)
            .order_by(ProjectTakeOffSheetSectionAreaItems.created_at.asc())
        )

        if opening_number:
            item_data_query = item_data_query.filter(
                ProjectTakeOffSheetSectionAreaItems.opening_number == opening_number
            )

        total_items = item_data_query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            item_data_query = item_data_query.offset(offset).limit(page_size)
        else:
            page = 1
            page_size = total_items if total_items > 0 else 1

        item_data = item_data_query.all()

        response = [
            {
                "id": item.id,
                "opening_number": item.opening_number,
                "desc": item.desc,
                "door_height": item.door_height,
                "door_width": item.door_width,
                "door_raw_material_type": item.door_raw_material_type,
                "frame_raw_material_type": item.frame_raw_material_type,
                "adon_fields": item.adon_fields,
                "installation_charge": item.installation_charge,
                "section_area_name": item.section_area_name,
                "section_name": item.section_name
            }
            for item in item_data
        ]

        # Calculate total page count
        page_count = math.ceil(total_items / page_size)

        return {
            "data": response,
            "page_count": page_count,
            "item_count": total_items,
            "status": "success",
        }
    except Exception as error:
        logger.exception(f"get_take_off_sheet_area_items:: An unexpected error occurred: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def upload_door_frame_documents(db: Session, file, project_id: str, project_material_id: str, current_member: Members):
    """**Summary:**
    Uploads tender documents for a specific project and saves the file in the database.

    **Parameters:**
    - db: The database session to perform the operation.
    - project_id: The identifier of the project to store the uploaded file with.
    - project_material_id: The identifier of the project to associate the uploaded file with.
    - files: The file to be uploaded and associated with the project.
    - current_member (Members): This will contain member details of current loggedin member.

    Returns:
    A dictionary with a success message upon successful file upload.

    Raises:
    - HTTPException: If an unexpected error occurs during the file upload process.
    """
    try:
        project_material = (
            db.query(ProjectMaterials).filter(ProjectMaterials.project_id == project_id, 
                                              ProjectMaterials.id == project_material_id).first())
        if not project_material:
            return JSONResponse(
                content={"message": "Invalid Request."},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if file:
            file_name = file.filename
            file_type = file.content_type
            # Calling function "upload_to_s3" to upload the attachment to S3
            upload_path = f"door_frame_documents/{project_id}/{project_material.id}"
            file_path = await upload_to_s3(file, upload_path)
            project_material.content_file_name = file_name
            project_material.content_file_path = file_path
            project_material.content_file_type = file_type
            db.commit()

            return {"message": "File uploaded successfully"}
        else:
            await delete_from_s3(project_material.content_file_path)
            project_material.content_file_name = None
            project_material.content_file_path = None
            project_material.content_file_type = None
            db.commit()

            return {"message": "File deleted successfully"}
        
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise