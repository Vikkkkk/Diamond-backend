"""
This module containes all routes those are related to schedule installation  add/update/read/delete.
"""
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import transfer_opening_controller
from controller import schedule_installation_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from middleware.permission_middleware import role_required, project_access_required
from fastapi import APIRouter, Depends, UploadFile, Form, File
from schemas.schedule_installation_opening_schema import ScheduleInstallationMappingSchema, ScheduleInstallationCommentBase
from typing import Optional, List
from models.change_order import ChangeOrderStatusEnum
from controller import change_order_controller
from schemas.schedule_data_schema import changeOrderScheduleDataBulkSaveSchema
from schemas.auth_schemas import invalid_credential_resp
from schemas.hardware_group_material_schema import ScheduleHardwarMaterialRequest
import traceback



router = APIRouter(prefix="/change_order", tags=["Change Order APIs"])

@router.post("/{project_id}/create_change_order", status_code=201)
async def create_change_order(
    project_id: str,
    co_number: str = Form(...),
    description: str = Form(...),
    priority: int = Form(default=1),
    current_status: ChangeOrderStatusEnum = Form(default=ChangeOrderStatusEnum.PENDING),
    cca_type: UploadFile = File(...),
    si_type: UploadFile = File(...),
    schedule_ids: str = Form(None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member),
):
    """
    Create a new Change Order with associated SI and CCA documents.

    Args:
        project_id (str): The project ID.
        co_number (str): Unique change order number.
        description (str): Description of the change order.
        priority (int): Priority level.
        current_status (ChangeOrderStatusEnum): Current status of change order.
        cca_type (UploadFile): CCA document file.
        si_type (UploadFile): SI document file.
        schedule_ids (str): Comma-separated schedule IDs.
        db (Session): DB session.
        current_member: Current logged-in user.

    Returns:
        JSONResponse with change order ID and success message.
    """
    try:
        return await change_order_controller.create_change_order(
            db=db,
            current_member=current_member,
            data={
                "project_id": project_id,
                "co_number": co_number,
                "description": description,
                "priority": priority,
                "current_status": current_status.value,
                "schedule_ids": schedule_ids,
            },
            files={
                "cca_type": cca_type,
                "si_type": si_type,
            }
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/{project_id}/change_orders/{change_order_id}", status_code=200)
async def update_change_order(
    project_id: str,
    change_order_id: str,
    description: str = Form(None),
    priority: int = Form(None),
    current_status: ChangeOrderStatusEnum = Form(None),
    cca_type: UploadFile = File(None),
    si_type: UploadFile = File(None),
    schedule_ids: str = Form(None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member),
):
    """
    Update an existing Change Order.

    - Updates fields like description, priority, and status.
    - Replaces documents for given doc_type (si_type, cca_type).
    - Updates schedules (removes old, adds new).
    """
    try:
        if current_status == ChangeOrderStatusEnum.COMPLETED:
            return JSONResponse(content={"message": "You Need to apply the changes of the approved Change Order to complete it."}, status_code=422)
        return await change_order_controller.update_change_order(
            db=db,
            current_member=current_member,
            project_id=project_id,
            change_order_id=change_order_id,
            data={
                "description": description,
                "priority": priority,
                "current_status": current_status.value if current_status else None,
                "schedule_ids": schedule_ids,
            },
            files={
                "cca_type": cca_type,
                "si_type": si_type,
            }
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/{project_id}/change_orders/{change_order_id}", status_code=200)
async def delete_change_order(
    project_id: str,
    change_order_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a Change Order and all related docs, schedules, and status logs.
    """
    try:
        return await change_order_controller.delete_change_order(
            db=db,
            project_id=project_id,
            change_order_id=change_order_id,
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/list_change_orders", status_code=200)
async def list_change_orders(
    project_id: str = Query(None),
    is_completed:bool = Query(default=None),
    page: int = Query(None),
    page_size: int = Query(None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member),
):
    """
    List all change orders with pagination and optional keyword search.
    """
    try:
        return await change_order_controller.list_change_orders(
            db, project_id, is_completed, page, page_size
        )
    except Exception as error:
        traceback.print_exception(error)
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_change_order/{change_order_id}", status_code=200)
async def get_change_order_detail(
    change_order_id: str,
    db: Session = Depends(get_db),
):
    """
    Get Change Order details by ID.

    Args:
        change_order_id (str): The Change Order ID.
        db (Session): DB session.

    Returns:
        JSONResponse with Change Order details.
    """
    try:
        return await change_order_controller.get_change_order_detail(
            db=db,
            change_order_id=change_order_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_next_possible_change_order_number", status_code=200)
async def get_next_possible_change_order_number(
    db: Session = Depends(get_db)
):
    """
    Get the next possible Change Order number.

    Format: `DIA-CO-XXX`

    Rules:
    - Starts at **DIA-CO-001** if no existing records.
    - Always left-pads the number to 3 digits minimum.
    - Grows naturally beyond 999 (e.g., DIA-CO-1000, DIA-CO-12345).

    Returns:
        JSONResponse: 
        {
            "data": "DIA-CO-XXX",   # next generated Change Order number
            "status": "success"
        }
    """
    try:
        return await change_order_controller.get_next_possible_change_order_number(db=db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/{project_id}/get_change_order_openings", status_code=200)
async def get_change_order_openings(
    project_id: str,
    db: Session = Depends(get_db),
):
    """
    Get all change order openings (schedules) for a project,
    but only if the Change Order status is APPROVED/REJECTED/PARTIALLY_APPROVED/CANCELLED.

    Args:
        project_id (str): Project ID
        db (Session): SQLAlchemy session

    Returns:
        JSONResponse: openings data grouped by CO
    """
    try:
        return await change_order_controller.get_change_order_openings_data(db, project_id)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{co_id}/update_change_order_schedule_data", status_code=200)
async def update_change_order_schedule_data(
    co_id: str,
    payload: changeOrderScheduleDataBulkSaveSchema,
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member),
):
    """
    Update schedule data for a specific Change Order (co_id).
    Maintains versioning (v1, v2, v3...) and recalculates totals.
    """
    try:
        return await change_order_controller.update_schedule_data(
            db=db,
            co_id=co_id,
            payload=payload,
            updated_by=current_member.id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/change_order_schedule_data/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_change_order_schedule_data(
    schedule_id:str,
    co_id: str = Query(...),
    part_number: Optional[str] = Query(default=None, title="Part Number"),
    opening_type: str = Query(title="Opening Type", description="DOOR/FRAME/HARDWARE/OPENING"),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Fetch schedule data for a Change Order (from current_version only).

    **Path Parameters:**
    - `co_id` (str): Change Order ID.

    **Query Parameters:**
    - `opening_type` (str): Opening type filter (DOOR, FRAME, HARDWARE, OPENING).
    - `part_number` (str, optional): Filter by part number.

    **Responses:**
    - 200 OK: Successfully returns current_version data.
    - 401 Unauthorized: Invalid token.
    - 500 Internal Server Error: Unexpected failure.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await change_order_controller.get_change_order_schedule_data(db, co_id, opening_type, part_number,schedule_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/{co_id}/update_change_order_hardware_data/{schedule_id}", status_code=200)
async def update_change_order_hardware_data(
    co_id: str,
    schedule_id: str,
    payload: ScheduleHardwarMaterialRequest,
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member),
):
    """
    Update hardware data for a specific Change Order (co_id).
    Maintains versioning and recalculates totals.
    """
    try:
        return await change_order_controller.update_change_order_hardware_data(
            db=db,
            co_id=co_id,
            schedule_id=schedule_id,
            payload=payload,
            updated_by=current_member.id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/change_order_hardware_data/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_change_order_hardware_data(
    schedule_id:str,
    co_id: str = Query(...),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Fetch hardware data for a Change Order (from current_version only).
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await change_order_controller.get_change_order_hardware_data(db, co_id, schedule_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/change_order_version_comparison/{schedule_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_change_order_hardware_data(
    schedule_id:str,
    co_id: str = Query(...),
    project_id: str = Query(...),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Fetch hardware data for a Change Order (from current_version only).
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await change_order_controller.get_change_order_version_comparison(
            db,
            co_id,
            project_id,
            schedule_id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/apply_change_order_changes/{co_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def apply_change_order_changes(
    co_id:str,
    project_id: str = Query(...),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member),
):
    """
    Fetch hardware data for a Change Order (from current_version only).
    """
    try:
        return await change_order_controller.apply_change_order_changes(
            db,
            co_id,
            project_id,
            current_member.id
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)










