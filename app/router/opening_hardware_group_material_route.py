"""
This module containes all routes those are related to Opening Hardware Group material add/update/read/delete.
"""
from typing import List, Union
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
from schemas.hardware_group_material_schema import ScheduleHardwarMaterialRequest, ScheduleHardwareMaterialReponse
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/opening/assign_hardware_to_opening", tags=["Opening Hardware Group Materials APIs"])

@router.post("/{project_id}/assign/{schedule_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def assign_hardware_to_opening(
    project_id: str,
    schedule_id: str,
    request_data: ScheduleHardwarMaterialRequest,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """
    **Assign Hardware Materials to a Schedule for a Project**

    This endpoint assigns hardware materials to a specific schedule within a project.

    **Path Parameters:**
    - `project_id` (str): Unique project identifier.
    - `schedule_id` (str): Unique schedule identifier.

    **Request Body (ScheduleHardwarMaterialRequest):**
    ```json
    {
        "hardware_materials": {
            "3b495456-672d-4296-b7fb-e4374bffc1b6": 3,
            "65bef17a-ced8-4d84-a9f6-cd8fc1c910ed": 1
        }
    }
    ```

    **Response Example:**
    ```json
    {
        "status": "success",
        "results": {
            "added": [
                {"id": "65bef17a-ced8-4d84-a9f6-cd8fc1c910ed", "quantity": 1}
            ],
            "removed": [
                {"id": "3b495456-672d-4296-b7fb-e4374bffc1b6"}
            ]
        }
    }
    ```
    """
    try:
        return await opening_hardware_group_controller.assign_hardware_to_opening(
            db=db,
            request_data=request_data,
            schedule_id=schedule_id,
            current_member=current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_assigned_hardwares/{schedule_id}", response_model=ScheduleHardwareMaterialReponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_assigned_hardwares(
    project_id: str,
    schedule_id: str,
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Project Manager", "Chief Project Manager"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """
    **Assign Hardware Materials to a Schedule for a Project**
    """
    try:
        return await opening_hardware_group_controller.get_assigned_hardwares(db, schedule_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)