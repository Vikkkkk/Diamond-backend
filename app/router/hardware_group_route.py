"""
This module containes all routes those are related to takeoff-sheet note add/update/read/delete.
"""

from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import hardware_group_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.hardware_group_schemas import HardwareGroup, AssignToOpenings
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/hardware_group", tags=["Hardware Group APIs"])


@router.get("/{project_id}/get_hardware_groups", status_code=status.HTTP_200_OK)
async def get_hardware_groups(
    project_id: str = Path(
        ..., title="Project ID", description="The ID of the project"
    ),
    keyword: str = Query(None, alias="keyword"),
    role_required=Depends(
        role_required(
            [
                "Admin",
                "Chief Estimator",
                "Estimator",
                "Project Manager",
                "Chief Project Manager",
            ]
        )
    ),  # Specify allowed roles here
    project_access=Depends(project_access_required()),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Endpoint to retrieve a list of hardware groups.

    Parameters:
    - verified_token (bool, optional): A boolean indicating whether the user's token is verified.
                                      Defaults to True when using the 'verify_token' dependency.
    - `keyword` (str): this will be usefull for keyword search on hw group name.
    - db (Session): The SQLAlchemy database session.
    - project_id: Id of the project.

    Returns:
    JSONResponse: A JSON response containing the result of the operation.
                  - If successful, status code 200 and a list of hardware groups.
                  - If the user's token is not verified, status code 401 and an invalid credential message.
                  - If unsuccessful due to an exception, status code 500 and an error message.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await hardware_group_controller.get_hardware_groups(
            db, project_id, keyword
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{project_id}/add_hardware_group", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_hardware_group(
    request_data: HardwareGroup,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Endpoint to add a new hardware group.

    Parameters:
    - request_data (HardwareGroup): The data for the new hardware group.
    - current_member (Members): The current member (user) making the request.
    - db (Session): The SQLAlchemy database session.

    Returns:
    JSONResponse: A JSON response containing the result of the operation.
                  - If successful, status code 200 and a success message with the newly inserted hardware group ID.
                  - If unsuccessful, status code 500 and an error message.
    """
    try:
        return await hardware_group_controller.add_hardware_group(
            db, request_data, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put(
    "/{project_id}/update_hardware_group/{hardware_group_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def update_hardware_group(
    hardware_group_id: str,
    request_data: HardwareGroup,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Endpoint to update an existing hardware group.

    Parameters:
    - hardware_group_id (str): The ID of the hardware group to be updated.
    - request_data (HardwareGroup): The updated data for the hardware group.
    - current_member (Members): The current member (user) making the request.
    - db (Session): The SQLAlchemy database session.

    Returns:
    JSONResponse: A JSON response containing the result of the operation.
                  - If successful, status code 200 and a success message.
                  - If the hardware group is not found, status code 400 and an error message.
                  - If unsuccessful due to an exception, status code 500 and an error message.
    """
    try:
        return await hardware_group_controller.update_hardware_group(
            db, hardware_group_id, request_data, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete(
    "/{project_id}/delete_hardware_group/{hardware_group_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def delete_hardware_group(
    hardware_group_id: str,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Endpoint to delete a hardware group.

    Parameters:
    - hardware_group_id (str): The ID of the hardware group to be deleted.
    - current_member (Members): The current member (user) making the request.
    - db (Session): The SQLAlchemy database session.

    Returns:
    JSONResponse: A JSON response containing the result of the operation.
                  - If successful, status code 200 and a success message.
                  - If the group is not found, status code 400 and an error message.
                  - If the user is not authorized, status code 401 and an invalid credential message.
                  - If unsuccessful due to an exception, status code 500 and an error message.
    """
    try:
        return await hardware_group_controller.delete_hardware_group(
            db, hardware_group_id, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/{project_id}/clone_hardware_group/{hardware_group_id}",
    status_code=status.HTTP_201_CREATED,
)
@logger.catch
async def clone_hardware_group(
    hardware_group_id: str,
    request_data: HardwareGroup,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Clone a hardware group and its associated materials.

    Args:
        hardware_group_id (str): The ID of the hardware group to clone.
        request_data (HardwareGroup): The data for the new hardware group.
        current_member (Members): The current user or member performing the operation.
        db (Session): The database session.

    Returns:
        JSONResponse: A JSON response containing the result of the operation.
            - 'id': The ID of the cloned hardware group.
            - 'message': A success message.
            - 'status': The status of the operation (e.g., 'success').
    """
    try:
        return await hardware_group_controller.clone_hardware_group(
            db, hardware_group_id, request_data, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post(
    "/{project_id}/assign_to_openings/{hardware_group_id}",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def assign_to_openings(
    hardware_group_id: str,
    request_data: AssignToOpenings,
    current_member: Members = Depends(get_current_member),
    role_required=Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """
    Assign a hardware group to specified openings and update related schedules.

    Parameters:
    - hardware_group_id (int): The identifier of the hardware group.
    - request_data (AssignToOpenings): The request data containing the opening IDs.
    - current_member (Members): The current member performing the assignment.
    - db (Session): The SQLAlchemy database session.

    Returns:
    - JSONResponse: A response containing a success message if the assignment is successful.

    Raises:
    - HTTPException: 500 Internal Server Error in case of unexpected exceptions.
    """
    try:
        return await hardware_group_controller.assign_to_openings(
            db, hardware_group_id, request_data, current_member
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/{project_id}/get_hardware_group/{hardware_group_id}/items",
    status_code=status.HTTP_200_OK,
)
@logger.catch
async def get_hardware_group_items(
    hardware_group_id: str,
    verified_token: bool = Depends(verify_token),
    role_required=Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),
    project_access=Depends(project_access_required()),
    db: Session = Depends(get_db),
):
    """**Summary:**
    Retrieve items belonging to a hardware group.

    Parameters:
    - hardware_group_id (str): The identifier of the hardware group.
    - verified_token (bool, optional): Dependency to verify the authentication token.
    - db (Session, optional): Database session dependency.

    Returns:
    - JSONResponse: A response containing the hardware group items or an error message.

    Raises:
    - HTTPException: 500 Internal Server Error in case of unexpected exceptions.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await hardware_group_controller.get_hardware_group_items(
            db, hardware_group_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
