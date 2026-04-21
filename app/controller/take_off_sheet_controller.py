from typing import List
from utils.common import get_utc_time, generate_uuid, get_random_hex_code, generate_uuid
from loguru import logger
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_sections import ProjectTakeOffSheetSections
from models.project_take_off_sheet_section_areas import ProjectTakeOffSheetSectionAreas
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.sections import Sections
from repositories.common_repositories import get_take_off_sheet_section_price
from repositories.take_off_sheet_repositories import delete_opening
from repositories.update_stats_repositories import update_take_off_sheet_stats, update_raw_material_stats, update_section_stats
from models.projects import Projects
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from fastapi.responses import JSONResponse
import math
from datetime import datetime
from utils.common import get_user_time
from sqlalchemy.orm import Session
from schemas.take_off_sheet_schemas import TakeOffSheets, TakeOffSheetRequest, TakeOffSheetSectionAreaRequest
from models.members import Members


async def add_take_off_sheet_sections(
    db: Session, 
    request_data: TakeOffSheetRequest, 
    current_member: Members
):
    """**Summary:**
    Add or update take-off sheet sections for a project.

    **Args:**
    - `db` (Session): The database session.
    - `request_data` (dict): A dictionary containing the request data with the following keys:
        - `project_id` (str): The unique identifier of the project.
        - `section_ids` (List[str]): A list of unique identifiers for the sections to be added or updated.
    - `current_member` (Any): The current authenticated member making the request.

    **Returns:**
    - dict: A dictionary containing information about the operation:
        - `id` (dict): A dictionary containing the ID of the updated take-off sheet:
            - `sheet_id` (str): The unique identifier of the take-off sheet.
        - `message` (str): A message indicating the result of the operation.
        - `status` (str): The status of the operation, either "success" or "failure".

    Raises:
    - IntegrityError: If an integrity error occurs during the database operation.
    - Exception: If an unexpected error occurs during the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            request_data = request_data.dict()
            project_data = db.query(Projects).filter(Projects.id==request_data["project_id"], Projects.is_deleted==False).first()
            if project_data.is_estimation == False or project_data.current_project_status == "Failed":
                return JSONResponse(content={"message": f"Take off sheet cann't be created as the project is completed."}, status_code=400)
            
            sheet_exists = (
                db.query(ProjectTakeOffSheets)
                .filter(ProjectTakeOffSheets.project_id == request_data["project_id"], \
                        ProjectTakeOffSheets.is_deleted == False).first()
            )
            if sheet_exists:
                project_take_off_sheet_id = sheet_exists.id
                db.query(ProjectTakeOffSheetSections)\
                    .filter(ProjectTakeOffSheetSections.project_take_off_sheet_id == project_take_off_sheet_id).update({'is_deleted': True})
                for section_id in request_data['section_ids']:
                    section_exists = (
                        db.query(ProjectTakeOffSheetSections)
                        .filter(ProjectTakeOffSheetSections.project_take_off_sheet_id == project_take_off_sheet_id, \
                                ProjectTakeOffSheetSections.section_id == section_id).first()
                        )
                    if section_exists:
                        section_exists.is_deleted = False
                    else:
                        sheet = ProjectTakeOffSheetSections(id = generate_uuid(), desc = 'Take Off Sheet Section', section_id = section_id, project_take_off_sheet_id = project_take_off_sheet_id, created_by = current_member.id)
                        db.add(sheet)
                        db.flush()
            else:
                project_take_off_sheet_id = generate_uuid()
                name = "Take Off Sheet"
                desc = "Take Off Sheet"
                sheet = ProjectTakeOffSheets(id = project_take_off_sheet_id, name = name, desc = desc, project_id = request_data["project_id"], created_by = current_member.id)
                db.add(sheet)
                db.flush()
                for section_id in request_data['section_ids']:
                    section = ProjectTakeOffSheetSections(id = generate_uuid(), \
                        desc = 'Take Off Sheet Section', section_id = section_id, \
                        project_take_off_sheet_id = project_take_off_sheet_id, created_by = current_member.id)
                    db.add(section)
                    db.flush()
            return {"id": {"sheet_id": project_take_off_sheet_id}, "message": "Data Updated", "status": "success"}   
            
    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def get_take_off_sheet_sections(db: Session, project_id: str):
    """**Summary:**
    Retrieve sections associated with a project's take-off sheet.

    **Args:**
    - db (Database): The database session.
    - project_id (int): The ID of the project.

    **Returns:**
    - dict: A dictionary containing the sections' data and status.

    **Raises:**
    - HTTPException: Returns a 400 status code with an error message if the take-off sheet is not found.
    """
    try:
        response = []
        project_take_off_sheet = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.project_id == project_id,
                ProjectTakeOffSheets.is_deleted == False
            )
            .first()
        )
        if project_take_off_sheet:
            project_take_off_sheet_sections = (
                db.query(ProjectTakeOffSheetSections)
                .join(Sections)
                .filter(
                    ProjectTakeOffSheetSections.project_take_off_sheet_id == project_take_off_sheet.id,
                    ProjectTakeOffSheetSections.is_deleted == False
                )
                .order_by(Sections.sort_order.asc())
                .all()
            )
            if project_take_off_sheet_sections:
                
                for project_take_off_sheet_section in project_take_off_sheet_sections:
                    data = {}
                    if not project_take_off_sheet_section.section.is_deleted:
                        data['project_take_off_sheet_id'] = project_take_off_sheet_section.project_take_off_sheet_id
                        data['project_take_off_sheet_sections_id'] = project_take_off_sheet_section.id
                        data['section_id'] = project_take_off_sheet_section.section_id
                        data['name'] = project_take_off_sheet_section.section.name
                        data['code'] = project_take_off_sheet_section.section.code
                        data['default_section'] = project_take_off_sheet_section.section.default_section
                        data['is_door_frame'] = project_take_off_sheet_section.section.is_door_frame
                        data['is_hwd'] = project_take_off_sheet_section.section.is_hwd
                        data['is_installation'] = project_take_off_sheet_section.section.is_installation
                        data['has_pricebook'] = project_take_off_sheet_section.section.has_pricebook
                        response.append(data)

        response = {"data": response, "status": "success"}
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def add_take_off_sheet_section_area(db: Session, request_data: TakeOffSheetSectionAreaRequest, current_member: Members):
    """**Summary:**
    Add a new section area to a project's take-off sheet section.

    **Args:**
    - db (Database): The database session.
    - request_data (RequestData): The data containing information about the new section area.
    - current_member (CurrentMember): The current member adding the section area.

    **Returns:**
    - dict: A dictionary containing a success message and status upon successful addition.

    **Raises:**
    - Exception: Raises any unexpected error that occurs during the operation. The error is logged for debugging.
    """
    try:
        data = {}
        project_take_off_sheet_section_area_id = generate_uuid()
        data['id'] = project_take_off_sheet_section_area_id
        data['name'] = request_data.name
        data['project_take_off_sheet_section_id'] = request_data.project_take_off_sheet_section_id
        data['desc'] = "Take Off Sheet Section Area"
        data['created_by'] = current_member.id
        section_area = ProjectTakeOffSheetSectionAreas(**data)
        db.add(section_area)
        db.commit()
        return {"id": {"take_off_sheet_section_area_id": project_take_off_sheet_section_area_id}, "message": "Area Added.", "status": "success"}
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
    

async def update_take_off_sheet_section_area(db: Session, id: str, request_data: TakeOffSheetSectionAreaRequest, current_member: Members):
    """**Summary:**
    Update a section area within a project's take-off sheet section.

    **Args:**
    - db (Database): The database session.
    - id (int): The ID of the section area to be updated.
    - request_data (RequestData): The data containing information for the update.
    - current_member (CurrentMember): The current member performing the update.

    **Returns:**
    - dict: A dictionary containing a success message and status upon successful update.

    **Raises:**
    - HTTPException: Returns a 400 status code with an error message if the area is not found.
    - Exception: Raises any unexpected error that occurs during the operation. The error is logged for debugging.
    """
    try:
        existing_area = db.query(ProjectTakeOffSheetSectionAreas).filter(ProjectTakeOffSheetSectionAreas.id == id, ProjectTakeOffSheetSectionAreas.is_deleted == False).first()
        if existing_area:
            
            request_data = request_data.model_dump(exclude_unset=True)
            request_data['updated_by'] = current_member.id
            for key, value in request_data.items():
                if value is not None:
                    setattr(existing_area, key, value)
            db.commit()
            return {"message": "Area Updated.", "status": "success"}
        else:
            return JSONResponse(content={"message": "Area not found."}, status_code=400)
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
    

async def delete_take_off_sheet_section_area(db: Session, id: str, current_member: Members):
    """**Summary:**
    Delete a section area within a project's take-off sheet section.

    **Args:**
    - db (Database): The database session.
    - id (int): The ID of the section area to be deleted.
    - current_member (CurrentMember): The current member performing the deletion.

    **Returns:**
    - dict: A dictionary containing a success message and status upon successful deletion.

    **Raises:**
    - HTTPException: Returns a 400 status code with an error message if the area is not found.
    - Exception: Raises any unexpected error that occurs during the operation. The error is logged for debugging.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Fetch the project take-off sheet section area based on provided ID
            section_area = (
                db.query(ProjectTakeOffSheetSectionAreas)
                .filter(
                    ProjectTakeOffSheetSectionAreas.id == id,
                    ProjectTakeOffSheetSectionAreas.is_deleted == False
                )
                .first()
            )
            
            # Check if the section area exists
            if section_area:
                # list all opening related to the given section area ID
                section_area_items = (
                    db.query(ProjectTakeOffSheetSectionAreaItems)
                    .filter(
                        ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_area_id == id,
                        ProjectTakeOffSheetSectionAreaItems.is_deleted == False
                    )
                    .all()
                )
                
                # delete all opening related to the given section area ID
                for area_item in section_area_items:
                    await delete_opening(
                        id=area_item.id,
                        current_member=current_member,
                        db=db
                    )
                db.flush()
                # Soft delete the section area
                section_area.deleted_by = current_member.id
                section_area.deleted_at = datetime.now()
                section_area.is_deleted = True
                db.flush()

                # print("section_area.project_take_off_sheet_section_id:: ",section_area.project_take_off_sheet_section_id)
                #update the section stats after deleting the section area and its associated openings
                project_take_off_sheet_id = await update_section_stats(db,project_take_off_sheet_section_id = section_area.project_take_off_sheet_section_id)
                
                # print("project_take_off_sheet_id:: ",project_take_off_sheet_id)
                #update the sheet stats after deleting the section area and its associated openings
                project_id = await update_take_off_sheet_stats(db,project_take_off_sheet_id= project_take_off_sheet_id)

                #update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(db,project_id= project_id)

                return {"message": "Area Deleted.", "status": "success"}
            else:
                # Return an error response if the section area is not found
                return JSONResponse(content={"message": "Area not found"}, status_code=400)
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    

async def get_take_off_sheet_section_area(db: Session, take_off_sheet_section_id: str):
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
        section_area = db.query(ProjectTakeOffSheetSectionAreas).filter(ProjectTakeOffSheetSectionAreas.project_take_off_sheet_section_id == take_off_sheet_section_id, ProjectTakeOffSheetSectionAreas.is_deleted == False).all()
        if section_area:
            for area in section_area:
                data.append(area.to_dict)
        return {"data": data, "status": "success"}
    
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def take_off_sheet_exists(db: Session, project_id: str):
    try:
        sheet_exists = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.project_id == project_id,
                ProjectTakeOffSheets.is_deleted == False,
                or_(
                    ProjectTakeOffSheets.total_extended_sell_amount != 0,
                    ProjectTakeOffSheets.total_extended_sell_amount.isnot(None)
                )
            )
            .first()
        )
        
        if sheet_exists:
            content = {"exist": True, "message": "Takeoff sheet already exist."}
            return JSONResponse(content=content, status_code=200)
        else:
            content = {"exist": False, "message": "The takeoff sheet does not exist. Please create it before proceeding."}
            return JSONResponse(content=content, status_code=406)

    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


