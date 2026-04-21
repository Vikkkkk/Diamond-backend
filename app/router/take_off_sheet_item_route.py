"""
This module containes all routes those are related to takeoff-sheet add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import take_off_sheet_item_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.take_off_sheet_schemas import TakeOffSheets, TakeOffSheetRequest, TakeOffSheetSectionAreaRequest
from schemas.auth_schemas import invalid_credential_resp
from schemas.take_off_sheet_item_schema import TakeOffSheetItem, TakeOffSheetCloneRequest
from middleware.permission_middleware import role_required, project_access_required
from typing import Optional


router = APIRouter(prefix="/take_off_sheet_item", tags=["Take Off Sheet Items APIs"])

@router.get("/{project_id}/get_adon_opening_fileds", status_code=status.HTTP_200_OK)
@logger.catch
async def get_adon_opening_fileds(
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for fetching all adon fileds for openings.

    **Args:**
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_item_controller.get_adon_opening_fileds(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/{project_id}/get_take_off_sheet_item_details/{id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_item_details(
    id: str,
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add item to a take-off sheet for an section's area.

    **Args:**
    - `id` (str): Take off sheet area item id.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_item_controller.get_take_off_sheet_item_details(id, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/take_off_sheet_area/{id}/items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_area_items(
    id: str,
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add item to a take-off sheet for an section's area.

    **Args:**
    - `id` (str): Take off sheet area id.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_item_controller.get_take_off_sheet_area_items(id, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_project_openings/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_project_openings(
    project_id: str,
    opening_number: str = Query(None),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add all openings for an project.

    **Args:**
    - project_id (str): project id for which we need to have the list of openings.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_item_controller.get_project_openings(project_id, opening_number, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/{project_id}/add_take_off_sheet_item", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_take_off_sheet_item(
    request_data: TakeOffSheetItem,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add item to a take-off sheet for an section's area.

    **Args:**
    - `request_data` (TakeOffSheetItem): The request data containing information
      about the item to be added to the take-off sheet for an section's area.
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
        return await take_off_sheet_item_controller.add_take_off_sheet_item(request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/{project_id}/delete_take_off_sheet_item/{id}", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_take_off_sheet_item(
    id: str,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Add item to a take-off sheet for an section's area.

    **Args:**
    - `id` (str): take off sheet item id to be deleted.
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
        return await take_off_sheet_item_controller.delete_take_off_sheet_item(id, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/{project_id}/update_take_off_sheet_item/{take_off_sheet_area_item_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def update_take_off_sheet_item(
    take_off_sheet_area_item_id: str,
    request_data: TakeOffSheetItem,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    Update an existing item in the take-off sheet section area.

    **Args:**
    - `take_off_sheet_area_item_id` (str): The ID of the take-off sheet item to be updated.
    - `request_data` (TakeOffSheetItem): Data for updating the take-off sheet item.
    - `current_member` (Members): Member details of the currently logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the result of the update operation.
            - 'message' (str): A message indicating the result of the operation.
            - 'status' (str): The status of the update operation ('success' or 'failure').

    **Raises:**
    - `HTTPException`: If an unexpected error occurs during the update process.
    """
    try:
        return await take_off_sheet_item_controller.update_take_off_sheet_item(take_off_sheet_area_item_id, request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/{project_id}/get_associate_item/{take_off_sheet_area_item_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_associate_item(
    take_off_sheet_area_item_id: str,
    material_type: str = Query(alias="material_type"),
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Fetches associated items based on the given project take-off sheet area item ID and material type.

    Parameters:
        - take_off_sheet_area_item_id (str): ID of the project take-off sheet area item.
        - material_type (str, optional): Type of material, e.g., 'DOOR', 'FRAME', 'HARDWARE' or 'other'.
        - verified_token (bool): Token verification flag obtained from the dependency.
        - db (Session): SQLAlchemy database session.

    Returns:
        dict: A dictionary containing the fetched data.
              - If material_type is 'HARDWARE', the dictionary includes details about hardware items.
              - If material_type is not 'HARDWARE', the dictionary includes details about opening schedules.
    """
    try:
        # Verify the token before proceeding
        if not verified_token:
            return invalid_credential_resp
        
        # Call the controller function to fetch associated items
        return await take_off_sheet_item_controller.get_associate_item(db, take_off_sheet_area_item_id, material_type)
    except Exception as error:
        # Log and handle unexpected errors
        return JSONResponse(content={"message": str(error)}, status_code=500)
    



@router.post("/{project_id}/clone_opening/{take_off_sheet_area_item_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def clone_opening(
    take_off_sheet_area_item_id: str,
    request_data: TakeOffSheetCloneRequest,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Clone an existing item in the ProjectTakeOffSheetSectionAreaItems table along with its related OpeningSchedules.

    Parameters:
        take_off_sheet_area_item_id (str): The ID of the item to be cloned.
        request_data (TakeOffSheetCloneRequest): Request data containing the new item information.
        current_member (Members): The current member performing the action.
        db (Session): SQLAlchemy database session.

    Returns:
        JSONResponse: A JSON response indicating the success or failure of the operation.
    """
    try:
        # Call the controller function to fetch associated items
        return await take_off_sheet_item_controller.clone_opening(db, take_off_sheet_area_item_id, current_member, request_data)
    except Exception as error:
        # Log and handle unexpected errors
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/items", status_code=status.HTTP_200_OK)
@logger.catch
async def get_take_off_sheet_items(
    project_id: str,
    opening_number: str = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Retrieves items for a specific project within a take-off sheet.

    **Parameters:**
    - `project_id` (str): The unique identifier for the project.
    - `opening_number` (str): The opening number for the specified area within the take-off sheet.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `role_required` (Depends, optional): Dependency to check if the user has the required role.
    - `project_access` (Depends, optional): Dependency to verify project access permissions.
    - `db` (Session, optional): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the items for the specified project of the take-off sheet.
      Status code 200 if successful, or 500 if an exception occurs.

    **Raises:**
    - `HTTPException`: If the token verification or role check fails, or if any other error occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await take_off_sheet_item_controller.get_take_off_sheet_items(project_id, opening_number, db, page, page_size)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)