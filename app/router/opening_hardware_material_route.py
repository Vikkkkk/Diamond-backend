"""
This module containes all routes those are related to Opening Hardware material add/update/read/delete.
"""
from typing import List, Literal, Optional, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import opening_hardware_group_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.materials_schema import ProjectMaterial, ProjectMaterialRequest, ProjectMaterialAssignRequest
from schemas.materials_schema import OpeningHardwareMaterialCloneRequest, OpeningHardwareMaterial
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/opening/hardware_list", tags=["Opening Hardware Materials APIs"])

@router.post("/{project_id}/add_hardware", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_hardware(
    project_id: str,
    request_data: OpeningHardwareMaterial,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add opening hardware material to the hardware list.

    **Args:**
    - `request_data` (OpeningHardwareMaterial): The request data containing information
      about the opening hardware material to be added to the hardware list.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await opening_hardware_group_controller.add_hardware_material(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/{project_id}/update_hardware", status_code=status.HTTP_201_CREATED)
@logger.catch
async def update_hardware_material(
    project_id: str,
    request_data: OpeningHardwareMaterial,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    update opening hw material.

    **Args:**
    - `request_data` (OpeningHardwareMaterial): The request data containing information
      about the opeing hw material to be added to the hardware list.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await opening_hardware_group_controller.update_hardware_material(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.delete("/{project_id}/delete_hardware_material/{hardware_material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_hardware_material(
    hardware_material_id: str,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Endpoint to delete hardware material from the database.

    Args:
        hardware_material_id (str): The ID of the opening hardware material to be deleted.
        `current_member` (Members): The current authenticated member making the request.
        db (Session, optional): SQLAlchemy database session. Defaults to Depends(get_db).

    Returns:
        JSONResponse: A JSON response indicating success or failure.
    """
    try:
        return await opening_hardware_group_controller.delete_hardware_material(hardware_material_id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/{project_id}/clone_opening_hw_material/{opening_hardware_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def clone_opening_material(
    project_id: str,
    opening_hardware_id: str,
    short_code: str = Query(alias="short_code"),
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This module is responsible for clonning  a opening schedule material for a project opening.

    **Args:**
    - `project_id` (str): project id.
    - `opening_hardware_id` (str): opening_hardware_id which we want to clone.
    - `short_code` (str): short_code which we want to use to be clone.
    - `current_member` (Members): The current authenticated member making the request.
    - `db` (Session, optional): Dependency to get the database session.
    """
    try:
        return await opening_hardware_group_controller.clone_opening_hardware_material(project_id, opening_hardware_id, short_code, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_opening_hardware_materials", status_code=status.HTTP_200_OK)
@logger.catch
async def get_opening_hardware_materials(
    project_id: str,
    keyword: str = Query(None, alias="keyword"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving materials list depending on the input keyword and type

    This method fetches a subset of materials from the database based on the specified type and short code.

    **Args:**
    - `db`: The database session object.
    - `keyword` (str): this will be usefull for keyword search on short code.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await opening_hardware_group_controller.get_opening_hardware_items(db, project_id, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_hardware_product_categories", status_code=status.HTTP_200_OK)
@logger.catch
async def get_hardware_product_categories(
    keyword: str = Query(None, alias="keyword"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    Retrieve all list of hardware product categories.

    **Args:**
    - `db`: The database session object.
    - `keyword` (str): this will be usefull for keyword search on short code.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await opening_hardware_group_controller.get_hardware_product_categories(db, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_hardware_prep_fields/{schedule_opening_hardware_material_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_hardware_prep_fields(
    schedule_opening_hardware_material_id: str,
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager", "Hardware Consultant"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    Retrieve all list of hardware product categories.

    **Args:**
    - `db`: The database session object.
    - `schedule_opening_hardware_material_id` (str): schedule opening hardware material id.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await opening_hardware_group_controller.get_hardware_prep_fields(db, schedule_opening_hardware_material_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


