"""
This module containes all routes those are related to takeoff-sheet note add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import notes_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.notes_schemas import NoteTemplates, ProjectTakeOffSheetNotes, ProjectTakeOffSheetNotesDeleteRequest, ProjectTakeOffSheetNotesResponse
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/notes", tags=["Notes APIs"])

@router.get("/{project_id}/get_note_templates", status_code=status.HTTP_200_OK)
@logger.catch
async def get_note_templates(
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)

):
    """**Summary:**
    
    fetch all note templates.

    **Args:**
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the note templates.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await notes_controller.get_note_templates(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    
    

@router.get("/{project_id}/take_off_sheet", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_notes(
    project_id: str,
    project_raw_material_id: str = Query(None),
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    
    fetch all notes (Useful for fetching the added notes to a project).

    **Args:**
    - `project_id` (str): The project_id of the take_off_sheet for which we want notes.
    - `project_raw_material_id` (str): The project_raw_material_id for which we want notes.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing all notes of a take off sheet.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await notes_controller.get_take_off_sheet_notes(db, project_id, project_raw_material_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.post("/{project_id}/add_take_off_sheet_notes", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_take_off_sheet_notes(
    project_id: str,
    request_data: List[ProjectTakeOffSheetNotes],
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add note to a take-off sheet.

    **Args:**
    - `project_id` (str): The project_id of the take_off_sheet for which we want to add note.
    - `request_data` (List[ProjectTakeOffSheetNotes]): The request data containing information
      about the note to be added to a take-off sheet.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        return await notes_controller.add_take_off_sheet_notes(project_id, request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/{project_id}/delete_take_off_sheet_notes", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_take_off_sheet_notes(
    request_data: ProjectTakeOffSheetNotesDeleteRequest,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add item to a take-off sheet for an section's area.

    **Args:**
    - `request_data` (ProjectTakeOffSheetNotesDeleteRequest): take off sheet note ids to be deleted.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        return await notes_controller.delete_take_off_sheet_notes(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.put("/{project_id}/update_take_off_sheet_note/{id}", status_code=status.HTTP_200_OK)
@logger.catch
async def update_take_off_sheet_note(
    id: str,
    take_off_sheet_note_updated_data: ProjectTakeOffSheetNotes,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add item to a take-off sheet for an section's area.

    **Args:**
    - `id` (str): take off sheet note id to be updated.
    - `take_off_sheet_note_updated_data` (ProjectTakeOffSheetNotes): Updated take_off_sheet_note data. Refer to the ProjectTakeOffSheetNotes schema for the structure
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
        return await notes_controller.update_take_off_sheet_note(id, take_off_sheet_note_updated_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
