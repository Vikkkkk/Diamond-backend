"""
This module containes all routes those are related to takeoff-sheet add/update/read/delete.
"""
from typing import List
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import take_off_sheet_controller, take_off_sheet_item_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.take_off_sheet_schemas import TakeOffSheets, TakeOffSheetRequest, TakeOffSheetSectionAreaRequest
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required
from fastapi import APIRouter, Depends, UploadFile, Form, File
from typing import Optional


router = APIRouter(prefix="/take_off_sheet", tags=["Take off Sheet APIs"])

@router.get("/get_take_off_sheet_sections/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_sections(
    project_id: str,
    verified_token: bool = Depends(verify_token),
    role_required_ = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Retrieve sections of a take-off sheet for a given project.

    **Args:**
    - `project_id` (str): The unique identifier of the project.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the take-off sheet sections.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_controller.get_take_off_sheet_sections(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/add_take_off_sheet_sections", status_code=status.HTTP_200_OK)
@logger.catch
async def add_take_off_sheet_sections(
    request_data: TakeOffSheetRequest,
    current_member: Members = Depends(get_current_member),
    role_required_ = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add sections to a take-off sheet for the current project.

    **Args:**
    - `request_data` (TakeOffSheetRequest): The request data containing information
      about the sections to be added to the take-off sheet.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.

    **Raises:**
    - `HTTPException`: If the current member is not authorized to perform the operation.
    - `JSONResponse`: If an internal server error occurs, returns a JSON response
      with an appropriate error message.
    """
    try:
        return await take_off_sheet_controller.add_take_off_sheet_sections(db, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/{project_id}/add_take_off_sheet_section_area", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_take_off_sheet_section_area(
    request_data: TakeOffSheetSectionAreaRequest,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Add a section area to a take-off sheet section for the current project.

    **Args:**
    - `request_data` (TakeOffSheetSectionAreaRequest): The request data containing
      information about the section area to be added to the take-off sheet section.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.

    **Raises:**
    - `HTTPException`: If the current member is not authorized to perform the operation.
    - `JSONResponse`: If an internal server error occurs, returns a JSON response
      with an appropriate error message.
    """

    try:
        return await take_off_sheet_controller.add_take_off_sheet_section_area(db, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/{project_id}/update_take_off_sheet_section_area/{section_area_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def update_take_off_sheet_section_area(
    section_area_id: str,
    request_data: TakeOffSheetSectionAreaRequest,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Update details of a section area in a take-off sheet section for the current project.

    **Args:**
    - `section_area_id` (str): The unique identifier of the section area to be updated.
    - `request_data` (TakeOffSheetSectionAreaRequest): The request data containing
      information about the updated section area.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.

    **Raises:**
    - `HTTPException`: If the current member is not authorized to perform the operation
      or if the specified section area is not found.
    - `JSONResponse`: If an internal server error occurs, returns a JSON response
      with an appropriate error message.
    """
    try:
        return await take_off_sheet_controller.update_take_off_sheet_section_area(db, section_area_id, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.delete("/{project_id}/delete_take_off_sheet_section_area/{section_area_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_take_off_sheet_section_area(
    section_area_id: str,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Delete a section area from a take-off sheet section for the current project.

    **Args:**
    - `section_area_id` (str): The unique identifier of the section area to be deleted.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.

    **Raises:**
    - `HTTPException`: If the current member is not authorized to perform the operation
      or if the specified section area is not found.
    - `JSONResponse`: If an internal server error occurs, returns a JSON response
      with an appropriate error message.
    """
    try:
        return await take_off_sheet_controller.delete_take_off_sheet_section_area(db, section_area_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_take_off_sheet_section_area/{take_off_sheet_section_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_section_area(
    take_off_sheet_section_id: str,
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Retrieve sections of a take-off sheet for a given section id.

    **Args:**
    - `section_id` (str): The unique identifier of the section.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the take-off sheet section area.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_controller.get_take_off_sheet_section_area(db, take_off_sheet_section_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
  



@router.get("/project/{project_id}/take_off_sheet/exist", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_exists(
    project_id: str, 
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Check if a take-off sheet exists for a given project ID.

    **Args:**
    - `project_id` (str): The unique identifier of the project.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating whether the take-off sheet exists.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_controller.take_off_sheet_exists(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/{project_id}/upload_door_frame_documents", status_code=status.HTTP_201_CREATED)
@logger.catch
async def upload_door_frame_documents(
    project_id = str,
    project_material_id: str = Form(...),
    file: UploadFile = File(None),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for uploading documents for a project.

    **Args:**
    - `db` (Session): db session referance
    - `takeoff_sheet_section_area_item_id` (str): takeoff_sheet_section_area_item_id, which will add along with the file data into the database
    - `file` (file): File, selected and uploaded in to the system for a specific project
    - `current_member` (Members): This will contain member details of current loggedin member.
    """
    try:
        return await take_off_sheet_item_controller.upload_door_frame_documents(db, file, project_id, project_material_id, current_member)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)