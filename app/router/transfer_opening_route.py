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
from controller import transfer_opening_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.take_off_sheet_schemas import TakeOffSheets, TakeOffSheetRequest, TakeOffSheetSectionAreaRequest
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required, project_access_required
from fastapi import APIRouter, Depends, UploadFile, Form, File
from typing import Optional


router = APIRouter(prefix="/schedules", tags=["Transfer Opening APIs"])


@router.post("/{project_id}/transfer-opening", status_code=status.HTTP_201_CREATED)
@logger.catch
async def transfer_opening(
    project_id = str,
    db: Session = Depends(get_db),
    current_member_id: str = Depends(get_current_member)
):
    try:
        return await transfer_opening_controller.transfer_opening(db, project_id, current_member_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)



@router.get("/compare_take_off_data/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def compare_take_off_data(
    schedule_id = str,
    component = Query(title="Component Type", description="The type of the component"),
    part_number = Query(None, title="Part number", description="The Part number"),
    db: Session = Depends(get_db),
    current_member_id: str = Depends(get_current_member)
):
    try:
        return await transfer_opening_controller.compare_take_off_data(db,current_member_id, schedule_id, component, part_number)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)


@router.get("/compare_hardware_data/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def compare_hardware_data(
    schedule_id = str,
    db: Session = Depends(get_db),
    current_member_id: str = Depends(get_current_member)
):
    try:
        return await transfer_opening_controller.compare_hardware_data(db,current_member_id, schedule_id)
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)