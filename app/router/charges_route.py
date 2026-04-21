"""
This module containes all routes those are related to takeoff-sheet charges add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import charges_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.charges_schemas import ProjectTakeOffSheetCharges
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/charges", tags=["Charges APIs"])


@router.post("/add_take_off_sheet_charge/{project_id}", status_code=status.HTTP_201_CREATED)
@logger.catch
async def add_take_off_sheet_charge(
    request_data: ProjectTakeOffSheetCharges,
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db),
    
):
    """
    Endpoint to add a take-off sheet charge for a specific project.

    Args:
        project_id (str): Identifier of the project.
        request_data (ProjectTakeOffSheetCharges): Request data for the take-off sheet charge.
        current_member (Members, optional): Current member performing the operation. Defaults to None.
        db (Session, optional): Database session object. Defaults to None.
    """
    try:
        return await charges_controller.add_take_off_sheet_charge(db, project_id, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/take_off_sheet/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_sheet_charges(
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator", "Project Manager", "Chief Project Manager"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db),
    
):
    """**Summary:**
    
    fetch all charges (Useful for fetching the added charges to a project).

    **Args:**
    - `project_id` (str): The project_id of the take_off_sheet for which we want charges.
    - `verified_token` (bool, optional): Dependency to verify the authentication token.
    - `db` (Session): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing all charges of a take off sheet.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await charges_controller.get_take_off_sheet_charges(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/add_installation_charge/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def add_installation_charge(
    project_id: str = Path(..., title="Project ID", description="The ID of the project"),
    takeoff_sheet_section_area_item_id: str = Form(..., title="Section Area Item ID", description="The ID of the section area item within the take-off sheet"),
    charge_amount: float = Form(..., title="Installation Charge Amount", description="The amount to set as the installation charge"),
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    # project_access = Depends(project_access_required()),  # Check if the user has access to the project
    db: Session = Depends(get_db),
):
    """
    Endpoint to add or update an installation charge for a specific section area item within a project's take-off sheet.

    This endpoint allows authorized members (Admin, Estimator, Chief Estimator) to set or update the installation charge for a 
    specified section area item in a project's take-off sheet. User access to the project is verified before proceeding.

    Args:
        project_id (str): The unique identifier of the project.
        takeoff_sheet_section_area_item_id (str): The identifier of the section area item within the take-off sheet where the charge is being applied.
        charge_amount (float): The installation charge amount to be added or updated.
        current_member (Members): The current member performing the operation, automatically provided through dependency injection.
        role_required: Dependency ensuring the user has a required role to perform the operation.
        project_access: Dependency that checks if the user has access to the specified project.
        db (Session): The database session object, provided through dependency injection.

    Returns:
        JSONResponse: A success message upon updating the installation charge or an error message if the operation fails.
    """
    try:
        return await charges_controller.update_installation_charge(db, project_id, takeoff_sheet_section_area_item_id, charge_amount, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
