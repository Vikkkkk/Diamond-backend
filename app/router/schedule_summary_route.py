"""
This module containes all routes those are related to takeoff-sheet estimation add/update/read/delete.
"""
from datetime import date
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from controller import schedule_summary_controller
from controller import take_off_sheet_estimation_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.take_off_sheet_schemas import TakeOffSheets, TakeOffSheetRequest, TakeOffSheetSectionAreaRequest
from schemas.auth_schemas import invalid_credential_resp
from schemas.take_off_sheet_item_schema import TakeOffSheetItem
from schemas.take_off_sheet_estimation_schemas import EstimationBreakdown
from schemas.take_off_sheet_estimation_schemas import EstimationSurcharge 
from schemas.take_off_sheet_estimation_schemas import EstimationDiscount
from middleware.permission_middleware import role_required, project_access_required


router = APIRouter(prefix="/schedule/summary", tags=["Schedule Summary APIs"])


@router.get("/get_overall_summary/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_overall_summary(
    project_id: str,
    # verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator", "Project Manager"])),  # Specify allowed roles here
    # project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    try:
        # if not verified_token:
        #     return invalid_credential_resp
        return await schedule_summary_controller.get_schedule_overall_summary(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_schedule_component_summary/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_schedule_component_summary(
    project_id: str,
    schedule_id: str = Query(..., description="schedule_id"),
    # verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator", "Project Manager"])),  # Specify allowed roles here
    # project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    try:
        # if not verified_token:
        #     return invalid_credential_resp
        return await schedule_summary_controller.get_schedule_component_breakup_summary(db, schedule_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_schedule_discount/{project_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_schedule_discount(
    project_id: str,
    # verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator"])),  # Specify allowed roles here
    # project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):
    try:
        # if not verified_token:
        #     return invalid_credential_resp
        return await schedule_summary_controller.get_schedule_discount(db, project_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.post("/{project_id}/discount/project_quote", status_code=status.HTTP_201_CREATED)
@logger.catch
async def discount_project_quote(
    project_id: str,
    discount_quote_number: str = Form(None),
    file: List[UploadFile] = File(None),
    discount: str = Form(...),
    manufacturer_id: str = Form(...),
    brand_id: str = Form(None),
    raw_material_id: str = Form(...),
    discount_type: str = Form(...),
    expiry_date: Optional[Union[str, date]] = Form(None),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator", "Project Manager", "Chief Project Manager"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):   
    """
    Endpoint to discount a project quote.

    Args:
        project_id (str): Identifier of the project.
        discount_quote_number (str, optional): Quote number for the discount (if applicable).
        file (List[UploadFile], optional): List of uploaded files (if applicable).
        discount (str): Discount value.
        manufacturer_id (str): Identifier of the manufacturer.
        raw_material_id (str): Identifier of the raw material.
        discount_type (str): Type of discount.
        db (Session, optional): Database session object. Defaults to None.
        current_member (Members, optional): Current member performing the operation. Defaults to None.
    """
    discount_project_quote = {
        "discount": discount,
        "manufacturer_id": manufacturer_id,
        "brand_id": brand_id,
        "raw_material_id": raw_material_id,
        "discount_type": discount_type,
        "expiry_date": expiry_date
    }
    if discount_quote_number is not None:
        discount_project_quote["discount_quote_number"] = discount_quote_number

    try:
        return await schedule_summary_controller.add_schedule_discount_quote(db, discount_project_quote, file, project_id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.delete("/{project_id}/discount/project_quote", status_code=status.HTTP_200_OK)
@logger.catch
async def delete_discount_project_quote(
    request_data: EstimationDiscount,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Chief Estimator", "Project Manager", "Chief Project Manager"])),  # Specify allowed roles here
    project_access = Depends(project_access_required()),
    db: Session = Depends(get_db)
):   
    """
    Endpoint to discount a project quote.

    Args:
        reqest_data (EstimationDiscount): Discount project quote data removar info.
        db (Session, optional): Database session object. Defaults to None.
        current_member (Members, optional): Current member performing the operation. Defaults to None.
    """
    try:
        return await schedule_summary_controller.delete_discount_schedule_quote(db, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
