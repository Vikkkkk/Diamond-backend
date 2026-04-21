"""
This module contains all routes related to opening door/frame materials.
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import opening_door_frame_materials_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from schemas.materials_schema import OpeningDoorFrameMaterial, UpdateMaterialDescriptionRequest
from middleware.permission_middleware import project_access_required, role_required

router = APIRouter(prefix="/opening/door_frame_list", tags=["Opening Door/Frame Materials APIs"])


@router.post("/{project_id}/add_door_frame_material", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_door_frame_material(
    project_id: str,
    request_data: OpeningDoorFrameMaterial,
    current_member: Members = Depends(get_current_member),
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add opening door/frame material to the project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `request_data` (OpeningDoorFrameMaterial): The request data containing information
      about the opening door/frame material to be added.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    
    **Returns:**
    - `dict`: A response containing the created material ID, message, and status.
    - `JSONResponse`: A JSON response with an error message in case of an exception.
    """
    try:
        return await opening_door_frame_materials_controller.add_door_frame_material(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_opening_door_frame_materials/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_opening_door_frame_materials(
    project_id: str,
    keyword: Optional[str] = Query(title="Keyword for short_code search", default=None),
    material_type: Optional[str] = Query(title="Material Type (DOOR or FRAME)", default=None),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Retrieve opening door/frame materials for a specific project.

    This endpoint fetches door and frame materials associated with a given project ID.
    The request can optionally filter by keyword (search in short_code) and material type.

    **Args:**
    - `project_id (str)`: The ID of the project for which door/frame materials are to be fetched.
    - `keyword (Optional[str])`: Optional keyword to search in short_code field.
    - `material_type (Optional[str])`: Optional filter for material type (DOOR or FRAME).
    - `verified_token (bool)`: Indicates whether the request token is verified.
    - `db (Session)`: SQLAlchemy database session used to interact with the database.
    
    **Returns:**
    - `dict`: A response containing the list of door/frame materials with status and message.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await opening_door_frame_materials_controller.get_opening_door_frame_materials(db, project_id, keyword, material_type)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_unassigned_materials/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_unassigned_door_frame_materials(
    project_id: str,
    schedule_id: str = Query(alias="schedule_id"),
    raw_material_code: Optional[str] = Query(title="Raw Material Code", default=None),
    material_type: Optional[str] = Query(title="Material Type (DOOR or FRAME)", default=None),
    keyword: Optional[str] = Query(title="Keyword for short_code search", default=None),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Retrieve unassigned opening door/frame materials for a specific project and schedule.

    This endpoint fetches door and frame materials that are NOT assigned to the specified schedule.
    The request can optionally filter by raw_material_code, material type, and keyword.

    **Args:**
    - `project_id (str)`: The ID of the project for which materials are to be fetched.
    - `schedule_id (str)`: The ID of the schedule to check for unassigned materials.
    - `raw_material_code (Optional[str])`: Optional filter for raw material code.
    - `material_type (Optional[str])`: Optional filter for material type (DOOR or FRAME).
    - `keyword (Optional[str])`: Optional keyword to search in short_code field.
    - `verified_token (bool)`: Indicates whether the request token is verified.
    - `db (Session)`: SQLAlchemy database session used to interact with the database.
    
    **Returns:**
    - `dict`: A response containing the list of unassigned door/frame materials with status and message.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await opening_door_frame_materials_controller.get_unassigned_door_frame_materials(
            db, project_id, schedule_id, raw_material_code, material_type, keyword
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_assigned_materials/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_assigned_door_frame_materials(
    project_id: str,
    schedule_id: str = Query(alias="schedule_id"),
    raw_material_code: Optional[str] = Query(title="Raw Material Code", default=None),
    material_type: Optional[str] = Query(title="Material Type (DOOR or FRAME)", default=None),
    keyword: Optional[str] = Query(title="Keyword for short_code search", default=None),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Retrieve assigned opening door/frame materials for a specific project and schedule.

    This endpoint fetches door and frame materials that are NOT assigned to the specified schedule.
    The request can optionally filter by raw_material_code, material type, and keyword.

    **Args:**
    - `project_id (str)`: The ID of the project for which materials are to be fetched.
    - `schedule_id (str)`: The ID of the schedule to check for assigned materials.
    - `raw_material_code (Optional[str])`: Optional filter for raw material code.
    - `material_type (Optional[str])`: Optional filter for material type (DOOR or FRAME).
    - `keyword (Optional[str])`: Optional keyword to search in short_code field.
    - `verified_token (bool)`: Indicates whether the request token is verified.
    - `db (Session)`: SQLAlchemy database session used to interact with the database.
    
    **Returns:**
    - `dict`: A response containing the list of assigned door/frame materials with status and message.
    - `JSONResponse`: A JSON response with an error message in case of an exception.

    **Raises:**
    - `HTTPException`: For authentication/authorization failures or database errors.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await opening_door_frame_materials_controller.get_assigned_door_frame_materials(
            db, project_id, schedule_id, raw_material_code, material_type, keyword
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

@router.put("/{project_id}/update_door_frame_material", status_code=status.HTTP_200_OK)
@logger.catch
async def update_door_frame_material(
    project_id: str,
    request_data: OpeningDoorFrameMaterial,
    current_member: Members = Depends(get_current_member),
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Update opening door/frame material.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `request_data` (OpeningDoorFrameMaterial): The request data containing information
      about the door/frame material to be updated.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    
    **Returns:**
    - `dict`: A response containing the updated material ID, message, and status.
    - `JSONResponse`: A JSON response with an error message in case of an exception.
    """
    try:
        return await opening_door_frame_materials_controller.update_door_frame_material(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/{project_id}/delete_door_frame_material/{door_frame_material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_door_frame_material(
    project_id: str,
    door_frame_material_id: str,
    current_member: Members = Depends(get_current_member),
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Delete door/frame material from the database (soft delete).

    **Args:**
    - `project_id` (str): The ID of the project.
    - `door_frame_material_id` (str): The ID of the door/frame material to be deleted.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): SQLAlchemy database session.

    **Returns:**
    - `dict`: A response containing the message and status.
    - `JSONResponse`: A JSON response with an error message in case of an exception.
    """
    try:
        return await opening_door_frame_materials_controller.delete_door_frame_material(door_frame_material_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/clone_door_frame_material/{door_frame_material_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def clone_door_frame_material(
    project_id: str,
    door_frame_material_id: str,
    short_code: str = Query(alias="short_code"),
    current_member: Members = Depends(get_current_member),
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Clone an opening door/frame material for a project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `door_frame_material_id` (str): The ID of the door/frame material to clone.
    - `short_code` (str): The new short code for the cloned material.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    
    **Returns:**
    - `dict`: A response containing the cloned material ID, message, and status.
    - `JSONResponse`: A JSON response with an error message in case of an exception.
    """
    try:
        return await opening_door_frame_materials_controller.clone_door_frame_material(project_id, door_frame_material_id, short_code, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/assign_to_schedule", status_code=status.HTTP_200_OK)
@logger.catch
async def assign_door_frame_material_to_schedule(
    project_id: str,
    opening_door_frame_material_id: str = Query(alias="opening_door_frame_material_id"),
    schedule_id: str = Query(alias="schedule_id"),
    part_number: Optional[str] = Query(title="Part Number", default=None),
    current_member: Members = Depends(get_current_member),
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Assign a door/frame material to a schedule and populate ScheduleData from master data.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `opening_door_frame_material_id` (str): The ID of the door/frame material to assign.
    - `schedule_id` (str): The ID of the schedule to assign to.
    - `material_type` (str): The type of material (DOOR or FRAME).
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    
    **Returns:**
    - `dict`: A response containing success message and count of created schedule data records.
    - `JSONResponse`: A JSON response with an error message in case of an exception.
    """
    try:
        return await opening_door_frame_materials_controller.assign_door_frame_material_to_schedule(
            opening_door_frame_material_id, schedule_id,part_number, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/{project_id}/unassign_from_schedule", status_code=status.HTTP_200_OK)
@logger.catch
async def unassign_door_frame_material_from_schedule(
    project_id: str,
    opening_door_frame_material_id: str = Query(alias="opening_door_frame_material_id"),
    schedule_id: str = Query(alias="schedule_id"),
    current_member: Members = Depends(get_current_member),
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Unassign a door/frame material from a schedule and remove associated ScheduleData.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `opening_door_frame_material_id` (str): The ID of the door/frame material to unassign.
    - `schedule_id` (str): The ID of the schedule to unassign from.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    
    **Returns:**
    - `dict`: A response containing success message and count of deleted schedule data records.
    - `JSONResponse`: A JSON response with an error message in case of an exception.
    """
    try:
        return await opening_door_frame_materials_controller.unassign_door_frame_material_from_schedule(
            opening_door_frame_material_id, schedule_id, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/update_door_and_frame_material_description/{material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def update_door_and_frame_material_description(
    material_id: str,
    material_desc: UpdateMaterialDescriptionRequest,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Estimator",
                "Chief Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Update an existing opening door/frame material description.

    **Args:**
    - `material_id` (str): The ID of the opening door/frame material to update.
    - `description` (str): The updated material description.
    - `current_member` (Members): The current authenticated member making the request.
    - `role_required`: Dependency to check user roles.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response with success message and opening_door_frame_material_id.
      Status code 200 if successful, 404 if not found, 500 if an exception occurs.
    """
    try:
        return await opening_door_frame_materials_controller.update_door_and_frame_material_desc(
            material_id, material_desc, current_member, db
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
