"""
This module containes all routes those are related to schedule installation  add/update/read/delete.
"""

import json
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query,HTTPException
from starlette import status
from models import get_db
from datetime import datetime
from utils.auth import verify_token, get_current_member
from middleware.permission_middleware import role_required, project_access_required
from schemas.work_order_schema import StartORStopWorkOrder
from fastapi import APIRouter, Depends, UploadFile, Form, File
from typing import Optional, List
from controller import work_order_controller
from models.work_order import WorkOrderStatusEnum


router = APIRouter(prefix="/work_order", tags=["Work Order APIs"])




@router.post("/{project_id}/create_work_order", status_code=201)
async def create_work_order(
    project_id:str,
    request_no: str = Form(None),
    wo_number: str = Form(None),
    wo_date: str = Form(None),
    site_name: str = Form(None),
    client_id: str = Form(None),
    site_address: str = Form(None),
    site_location: Optional[str] = Form(json.dumps({"lat":43.833133,"lng":-79.335966})),
    site_city: str = Form(None),
    bill_to_name: str = Form(None),
    cutomer_email: str = Form(None),
    customer_contact_name: str = Form(None),
    customer_phone: str = Form(None),
    customer_fax: str = Form(None),
    customer_po: str = Form(None),
    job_number: str = Form(None),
    job_desc: str = Form(None),
    completion_date: str = Form(None),
    priority: int = Form(None),
    due_date: str = Form(None),
    estimated_hours: int = Form(None),
    scheduled_arrival: str = Form(None),
    dispatched_date: str = Form(None),
    dispatcher: str = Form(None),
    work_requested: str = Form(None),
    dispatch_note: str = Form(None),
    assignee_ids: str = Form(None),
    schedule_ids: str= Form(None),
    wo_status: WorkOrderStatusEnum = Form(default=WorkOrderStatusEnum.PENDING),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    Create a new work order with assignees and schedules.

    Args:
        request_no: Unique request number.
        assignee_ids: List of member IDs to assign.
        schedule_ids: List of schedule IDs to map.
        current_member: Logged-in member info (creator).

    Returns:
        JSONResponse with work order ID and success message.
    """
    try:
        return await work_order_controller.create_work_order(
            db=db,
            current_member=current_member,
            data={
                "project_id":project_id,
                "request_no": request_no,
                "wo_number": wo_number,
                "wo_date": wo_date,
                "site_name": site_name,
                "client_id": client_id,
                "site_address": site_address,
                "site_location": json.loads(site_location),
                "site_city": site_city,
                "bill_to_name": bill_to_name,
                "cutomer_email": cutomer_email,
                "customer_contact_name": customer_contact_name,
                "customer_phone": customer_phone,
                "customer_fax": customer_fax,
                "customer_po": customer_po,
                "job_number": job_number,
                "job_desc": job_desc,
                "completion_date": completion_date,
                "priority": priority,
                "due_date": due_date,
                "estimated_hours": estimated_hours,
                "scheduled_arrival": scheduled_arrival,
                "dispatched_date": dispatched_date,
                "dispatcher": dispatcher,
                "work_requested": work_requested,
                "dispatch_note": dispatch_note,
                "assignee_ids": assignee_ids,
                "schedule_ids": schedule_ids,
                "wo_status": wo_status.value,
            }
        )
    except Exception as error:
        return JSONResponse(content = {"message": str(error)}, status_code = 500)



@router.put("/{project_id}/update_work_order/{work_order_id}", status_code=200)
async def update_work_order(
    project_id: str,
    work_order_id: str,
    request_no: str = Form(None),
    wo_number: str = Form(None),
    wo_date: str = Form(None),
    site_name: str = Form(None),
    client_id: str = Form(None),
    site_address: str = Form(None),
    site_location: Optional[str] = Form(json.dumps({"lat":43.833133,"lng":-79.335966})),
    site_city: str = Form(None),
    bill_to_name: str = Form(None),
    cutomer_email: str = Form(None),
    customer_contact_name: str = Form(None),
    customer_phone: str = Form(None),
    customer_fax: str = Form(None),
    customer_po: str = Form(None),
    job_number: str = Form(None),
    job_desc: str = Form(None),
    completion_date: str = Form(None),
    priority: int = Form(None),
    due_date: str = Form(None),
    estimated_hours: int = Form(None),
    scheduled_arrival: str = Form(None),
    dispatched_date: str = Form(None),
    dispatcher: str = Form(None),
    work_requested: str = Form(None),
    dispatch_note: str = Form(None),
    assignee_ids: str = Form(None),
    schedule_ids: str = Form(None),
    wo_status: WorkOrderStatusEnum = Form(...),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    Update an existing work order, its assignees, and schedule mappings.

    Returns:
        JSONResponse with success message.
    """
    try:
        return await work_order_controller.update_work_order(
            db=db,
            current_member=current_member,
            work_order_id=work_order_id,
            data={
                "project_id": project_id,
                "request_no": request_no,
                "wo_number": wo_number,
                "wo_date": wo_date,
                "site_name": site_name,
                "client_id": client_id,
                "site_address": site_address,
                "site_location": json.loads(site_location),
                "site_city": site_city,
                "bill_to_name": bill_to_name,
                "cutomer_email": cutomer_email,
                "customer_contact_name": customer_contact_name,
                "customer_phone": customer_phone,
                "customer_fax": customer_fax,
                "customer_po": customer_po,
                "job_number": job_number,
                "job_desc": job_desc,
                "completion_date": completion_date,
                "priority": priority,
                "due_date": due_date,
                "estimated_hours": estimated_hours,
                "scheduled_arrival": scheduled_arrival,
                "dispatched_date": dispatched_date,
                "dispatcher": dispatcher,
                "work_requested": work_requested,
                "dispatch_note": dispatch_note,
                "assignee_ids": assignee_ids,
                "schedule_ids": schedule_ids,
                "wo_status": wo_status.value,
            }
        )
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/get_work_order/{work_order_id}", status_code=200)
async def get_work_order(
    work_order_id: str,
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    Get work order details including assignees and schedules.

    Args:
        work_order_id (str): ID of the work order.

    Returns:
        JSONResponse: Full details of the work order.
    """
    try:
        return await work_order_controller.get_work_order(db=db, work_order_id=work_order_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/list_work_orders", status_code=200)
async def list_work_orders(
    project_id:str = Query(default=None),
    is_completed:bool = Query(default=None),
    page: int  = Query(default=None),
    page_size: int = Query(default=None),
    keyword: str = Query(default=None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    List all work orders (summary).
    """
    try:
        return await work_order_controller.list_work_orders(db,project_id,is_completed,page,page_size,keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/list_work_orders_for_installer", status_code=200)
async def list_work_orders_for_installer(
    statuses: str = Query(..., description="Comma-separated list of statuses to list work orders"),
    page: int  = Query(default=None),
    page_size: int = Query(default=None),
    keyword: str = Query(default=None),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    List all work orders (summary).
    """
    try:
        return await work_order_controller.get_all_work_orders(db,statuses,page,page_size,keyword,current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.delete("/delete_work_order/{work_order_id}", status_code=200)
async def delete_work_order(
    work_order_id: str,
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    Delete a work order by its ID.
    """
    try:
        return await work_order_controller.delete_work_order(db=db, work_order_id=work_order_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.post("/start_or_end_installation", status_code=status.HTTP_201_CREATED)
async def start_or_end_installation(
    start_or_stop_work_order: Optional[StartORStopWorkOrder] = StartORStopWorkOrder(location_details=json.dumps({"location_details": {"lat": 0, "lng": 0}, "distance_in_meter": 1000})),
    work_order_id: str =  Query(..., description="Work Order Id"),
    has_started: bool = Query(..., description="True if starting, False if ending"),
    db: Session = Depends(get_db),
    current_member=Depends(get_current_member)
):
    """
    Start or end installation work for a work order.

    This endpoint is used by a member to mark the beginning or end of their installation task on a specific work order.
    - If `has_started` is `true`, a new time log entry is created for the current day.
    - If `has_started` is `false`, the duration is calculated and the day's log is updated accordingly.

    Args:
        work_order_id (str): The unique ID of the work order.
        has_started (bool): True if starting the work, False if ending it.
        db (Session): Database session dependency.
        current_member: Authenticated member object via dependency injection.

    Returns:
        JSONResponse: Message indicating whether installation work has started or ended.
    """
    try:
        location_details = json.loads(start_or_stop_work_order.location_details)
        return await work_order_controller.start_or_end_installation(
            db=db,
            work_order_id=work_order_id,
            member_id=current_member.id,
            has_started=has_started,
            location_details=location_details
        )
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)


@router.get("/get_logs_for_installer/{work_order_id}")
async def get_logs_for_installer(
    work_order_id: str,
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Get time logs for a specific work order.

    Optionally filters logs by the work order assignee (member).

    Args:
        work_order_id (str): The ID of the work order.
    Returns:
        List of time logs sorted by most recent first.
    """
    try:
        return await work_order_controller.get_assignee_logs(
            db=db,
            work_order_id=work_order_id,
            assignee_id=current_member.id
        )
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)


@router.get("/get_all_logs")
async def get_all_logs(
    work_order_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get time logs for a specific work order.
    Args:
        work_order_id (str): The ID of the work order.
    Returns:
        List of time logs sorted by most recent first.
    """
    try:
        return await work_order_controller.get_all_assignee_logs(
            db=db,
            work_order_id=work_order_id,
        )
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)



@router.put("/edit_time_log/{log_id}", status_code=status.HTTP_200_OK)
async def edit_time_log(
    log_id: str,
    started_at: str = Query(...),
    ended_at: str = Query(...),
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Update a WoAssigneeTimeLog entry by log ID.
    """
    try:
        return work_order_controller.update_assignee_time_log(
            db=db,
            log_id=log_id,
            started_at=started_at,
            ended_at=ended_at,
            current_member=current_member
        )
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"message": str(e)})



@router.post("/add_time_log", status_code=status.HTTP_201_CREATED)
async def add_time_log(
    wo_id: str = Query(...),
    started_at: str = Query(...),
    ended_at: str = Query(...),
    db: Session = Depends(get_db),
    member_id: str = Query(...),
    current_member = Depends(get_current_member),
):
    """
    Update a WoAssigneeTimeLog entry by log ID.
    """
    try:
        return work_order_controller.add_assignee_time_log(
            db=db,
            wo_id=wo_id,
            started_at=started_at,
            ended_at=ended_at,
            member_id=member_id,
            current_member=current_member
        )
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"message": str(e)})



@router.delete("/delete_time_log/{log_id}", status_code=status.HTTP_200_OK)
async def delete_time_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    Delete a WoAssigneeTimeLog entry by log ID.
    """
    try:
        return work_order_controller.delete_assignee_time_log(
            db=db,
            log_id=log_id,
            current_member=current_member
        )
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"message": str(e)})


@router.get("/get_next_possible_work_order_number", status_code=200)
async def get_next_possible_work_order_number(
    db: Session = Depends(get_db)
):
    """
    Get the next possible Work Order number.

    This endpoint generates the next sequential Work Order number
    in the format `DIA-XXX`. 

    Rules:
    - Starts at **DIA-001** if no existing records.
    - Always left-pads the number to 3 digits minimum.
    - Grows naturally beyond 999 (e.g., DIA-1000, DIA-12345).

    Examples:
    - No Work Orders exist → returns `DIA-001`
    - Latest is `DIA-009` → returns `DIA-010`
    - Latest is `DIA-099` → returns `DIA-100`
    - Latest is `DIA-999` → returns `DIA-1000`

    Returns:
        JSONResponse: 
        {
            "data": "DIA-XXX",   # next generated Work Order number
            "status": "success"
        }
    """
    try:
        return await work_order_controller.get_next_possible_work_order_number(db=db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)





