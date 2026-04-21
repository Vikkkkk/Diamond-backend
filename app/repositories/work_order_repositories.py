

from datetime import datetime, time, timezone
import json
import os
from loguru import logger

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from sqlalchemy.exc import SQLAlchemyError

from sqlalchemy import or_, func
from models.work_order import WorkOrder
from models.wo_assignee import WoAssignee
from models.wo_assignee_time_log import WoAssigneeTimeLog
from models.wo_schedules import WoSchedules
from models.project_members import ProjectMembers
from models.member_role import MemberRole
from models.members import Members
from models.schedules import Schedules
import math
import traceback
from models.work_order import WorkOrderStatusEnum
from models.clients import Clients
from models.schedule_installation_mapping import ScheduleInstallationMapping
from models.projects import Projects





async def create_work_order(db: Session, data: dict, created_by: str):
    try:
        project_id = data["project_id"]
        msg = "Work order created successfully."
        wo_number = data.get("wo_number")

        # --- Validation 1: Must start with DIA ---
        if wo_number and not wo_number.startswith("DIA"):
            return None, "Work order number must start with 'DIA'."

        # --- Validation 2: Must be unique ---
        if wo_number:
            existing_wo = db.query(WorkOrder).filter(
                WorkOrder.wo_number == wo_number
            ).first()
            if existing_wo:
                return None, f"Work order number '{wo_number}' already exists."

        # Create WorkOrder
        wo = WorkOrder(
            request_no=data["request_no"],
            wo_number=data.get("wo_number"),
            wo_date=data["wo_date"],
            wo_status=data["wo_status"],
            site_name=data.get("site_name"),
            site_address=data.get("site_address"),
            site_location=data.get("site_location"),
            site_city=data.get("site_city"),
            bill_to_name=data.get("bill_to_name"),
            cutomer_email=data.get("cutomer_email"),
            customer_contact_name=data.get("customer_contact_name"),
            customer_phone=data.get("customer_phone"),
            customer_fax=data.get("customer_fax"),
            customer_po=data.get("customer_po"),
            job_number=data.get("job_number"),
            job_desc=data.get("job_desc"),
            completion_date=data.get("completion_date"),
            priority=data.get("priority"),
            due_date=data.get("due_date"),
            estimated_hours=data.get("estimated_hours"),
            scheduled_arrival=data.get("scheduled_arrival"),
            dispatched_date=data.get("dispatched_date"),
            dispatcher=data.get("dispatcher"),
            work_requested=data.get("work_requested"),
            dispatch_note=data.get("dispatch_note"),
            project_id=project_id,
            client_id=data.get("client_id"),
        )
        db.add(wo)
        db.flush()

        # Parse comma-separated IDs
        assignee_ids = [i.strip() for i in data.get("assignee_ids", "").split(",") if i.strip()]
        schedule_ids = [i.strip() for i in data.get("schedule_ids", "").split(",") if i.strip()]

        # Handle Assignees and ProjectMembers
        for member_id in assignee_ids:
            member_role = db.query(MemberRole).filter_by(
                member_id=member_id,
                active_role=True
            ).first()

            if not member_role:
                msg = "No active role found for given member_id."
                return None,msg

            # Check if ProjectMembers entry already exists
            project_member_exists = db.query(ProjectMembers).filter_by(
                project_id=project_id,
                member_role_id=member_role.id
            ).first()

            if not project_member_exists:
                db.add(ProjectMembers(
                    project_id=project_id,
                    member_role_id=member_role.id,
                    is_active=True,
                    created_by=created_by
                ))

            # Add to WoAssignee
            db.add(WoAssignee(
                wo_id=wo.id,
                member_id=member_id,
                created_by=created_by
            ))

        # Add Wo Schedules
        for schedule_id in schedule_ids:
            # Check if this schedule_id is already assigned to *any* work order
            already_assigned = db.query(WoSchedules).filter_by(
                schedule_id=schedule_id
            ).first()

            if already_assigned:
                msg = "Opening is already assigned to another work order."
                return None, msg

            # Safe to add
            db.add(WoSchedules(
                wo_id=wo.id,
                schedule_id=schedule_id,
                created_by=created_by
            ))

        db.flush()
        db.refresh(wo)
        return wo.id, msg

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred during work order creation.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error during work order creation: {str(e)}")



async def update_work_order(db: Session, work_order_id: str, data: dict, updated_by: str):
    try:
        project_id = data["project_id"]
        message = "Work order updated successfully."

         # --- Validation: wo_number ---
        wo_number = data.get("wo_number")
        if wo_number:
            # Must start with DIA
            if not wo_number.startswith("DIA"):
                return None, "Work order number must start with 'DIA'."

            # Must be unique (ignore current WO itself)
            existing_wo = db.query(WorkOrder).filter(
                WorkOrder.wo_number == wo_number,
                WorkOrder.id != work_order_id
            ).first()
            if existing_wo:
                return None, f"Work order number '{wo_number}' already exists."

        # Fetch the existing work order
        wo = db.query(WorkOrder).filter_by(id=work_order_id).first()
        if not wo:
            message = "Work order not found."
            return None,message

        # Update fields
        for field in [
            "request_no", "wo_number", "wo_date", "site_name", "client_id","site_address", "site_location", "site_city",
            "bill_to_name", "cutomer_email", "customer_contact_name", "customer_phone", "customer_fax",
            "customer_po", "job_number", "job_desc", "completion_date", "priority", "due_date",
            "estimated_hours", "scheduled_arrival", "dispatched_date", "dispatcher",
            "work_requested", "dispatch_note", "wo_status"
        ]:
            setattr(wo, field, data.get(field))

        wo.updated_by = updated_by

        # Parse comma-separated strings
        raw_assignees = data.get("assignee_ids", "")
        raw_schedules = data.get("schedule_ids", "")
        new_assignees = set(i.strip() for i in raw_assignees.split(",") if i.strip())
        new_schedules = set(i.strip() for i in raw_schedules.split(",") if i.strip())

        # Update WoAssignees
        existing_assignees = {
            assignee.member_id: assignee for assignee in db.query(WoAssignee).filter_by(wo_id=work_order_id).all()
        }

        # Delete removed assignees
        for member_id in existing_assignees:
            if member_id not in new_assignees:
                db.delete(existing_assignees[member_id])

        # Add only new assignees
        for member_id in new_assignees:
            if member_id not in existing_assignees:
                member_role = db.query(MemberRole).filter_by(member_id=member_id, active_role=True).first()

                if not member_role:
                    message = f"No active role for member_id: {member_id}"

                    return None,message

                # Ensure ProjectMember exists
                exists = db.query(ProjectMembers).filter_by(
                    project_id=project_id,
                    member_role_id=member_role.id
                ).first()

                if not exists:
                    db.add(ProjectMembers(
                        project_id=project_id,
                        member_role_id=member_role.id,
                        is_active=True,
                        created_by=updated_by
                    ))

                # Add WoAssignee
                db.add(WoAssignee(
                    wo_id=work_order_id,
                    member_id=member_id,
                    created_by=updated_by
                ))

        # Update WoSchedules
        existing_schedules = {
            schedule.schedule_id: schedule for schedule in db.query(WoSchedules).filter_by(wo_id=work_order_id).all()
        }

        # Only delete mappings if status is PENDING or FAILED
        for schedule_id in existing_schedules:
            if schedule_id not in new_schedules:
                wo_schedule_obj = existing_schedules[schedule_id]

                if wo_schedule_obj and wo_schedule_obj.id:
                    # Get all mappings for this wo_schedule_id
                    mappings = db.query(ScheduleInstallationMapping).filter(
                        ScheduleInstallationMapping.wo_schedule_id == wo_schedule_obj.id
                    ).all()

                    # Check for any invalid status
                    for mapping in mappings:
                        if mapping.status.value not in ["PENDING", "FAILED"]:

                            message = f"Cannot remove opening as it has installation mapping(s) in {mapping.status.value} status."
                            return None, message

                    # Safe to delete all mappings
                    db.query(ScheduleInstallationMapping).filter(
                        ScheduleInstallationMapping.wo_schedule_id == wo_schedule_obj.id
                    ).delete(synchronize_session=False)

                # Then delete the WoSchedule itself
                db.delete(wo_schedule_obj)

        # Add only new schedules
        for schedule_id in new_schedules:
            if schedule_id not in existing_schedules:
                db.add(WoSchedules(
                    wo_id=work_order_id,
                    schedule_id=schedule_id,
                    created_by=updated_by
                ))

        db.flush()
        db.refresh(wo)
        return wo,message

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during work order update.")
    except Exception as e:
        import traceback
        print(traceback.print_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")




async def get_work_order_by_id(db: Session, work_order_id: str):
    try:
        work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found.")

        # Convert main work order fields to dict
        result = work_order.to_dict if hasattr(work_order, 'to_dict') else work_order.__dict__

        # Get assignees with member_name
        assignees_data = []
        assignees = db.query(WoAssignee).filter_by(wo_id=work_order_id).all()
        for assignee in assignees:
            member = db.query(Members).filter_by(id=assignee.member_id).first()
            assignee_dict = assignee.to_dict
            assignee_dict["member_name"] = f"{member.first_name} {member.last_name}" if member else None
            assignee_dict["work_logs"] = [elm.to_dict for elm in assignee.wo_assignee_time_logs]
            assignees_data.append(assignee_dict)

        # Get schedules with schedule_name
        schedules_data = []
        wo_schedules = db.query(WoSchedules).filter_by(wo_id=work_order_id).all()
        for schedule in wo_schedules:
            schedule_record = db.query(Schedules).filter_by(id=schedule.schedule_id).first()
            schedule_dict = schedule.to_dict
            schedule_dict["opening_number"] = schedule_record.opening_number if schedule_record else None
            schedule_dict["area"] = schedule_record.area if schedule_record else None
            schedules_data.append(schedule_dict)

        # Get client info
        client_id = result.get("client_id")
        if client_id:
            client_info = db.query(Clients).filter_by(id=client_id).first()
            result.pop("client_id")
            result["client"] = client_info.to_dict if client_info and hasattr(client_info, 'to_dict') else client_info.__dict__ if client_info else {}

        result["wo_assignees"] = assignees_data
        result["wo_schedules"] = schedules_data
        result["accepted_range_in_meters"] = os.getenv("ACCEPTED_RANGE_IN_METERS", 1000)
        return result

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error while fetching work order.")
    
    except Exception as e:
        logger.exception(f"get_material_series:: An unexpected error occurred: {e}")
        import traceback
        print(traceback.print_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")




async def get_all_work_orders(
    db: Session,
    project_id: str,
    is_completed: bool,
    page: int ,
    page_size: int ,
    keyword: str = None,
):
    """
    Retrieve a paginated list of work orders with optional status filtering and keyword search.

    Args:
        db (Session): SQLAlchemy DB session.
        project_id (str): ID of the project.
        is_completed (bool): Flag indicating if only completed work orders should be fetched.
        page (int): Page number.
        page_size (int): Number of records per page.
        keyword (str): Optional search keyword.

    Returns:
        dict: Paginated list of work orders and metadata.
    """
    try:
        # Determine status filter based on completion flag
        if is_completed:
            status_filter = [
                WorkOrderStatusEnum.COMPLETED.value,
                WorkOrderStatusEnum.FAILED.value,
                WorkOrderStatusEnum.CANCELLED.value,
            ]
        else:
            status_filter = [
                WorkOrderStatusEnum.PENDING.value,
                WorkOrderStatusEnum.DISPATCHED.value,
                WorkOrderStatusEnum.IN_PROGRESS.value,
            ]

        # Base query
        query = db.query(WorkOrder).filter(
            WorkOrder.project_id == project_id,
            WorkOrder.wo_status.in_(status_filter)
        )

        # Apply keyword filter if provided
        if keyword:
            keyword_filter = f"%{keyword.lower()}%"
            query = query.filter(
                or_(
                    func.lower(WorkOrder.request_no).like(keyword_filter),
                    func.lower(WorkOrder.id).like(keyword_filter)
                )
            )

        total_items = query.count()

        if page_size:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            page = 1
            page_size = total_items

        # Final ordered query
        work_orders = query.order_by(WorkOrder.created_at.desc()).all()

        result_data = []
        for wo in work_orders:
            wo_data = wo.to_dict if hasattr(wo, 'to_dict') else wo.__dict__
            result_data.append(wo_data)

        page_count = math.ceil(total_items / page_size) if page_size > 0 else 0

        return result_data,page_count,total_items

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error while listing work orders.")

    except Exception as e:
        logger.exception(f"get_all_work_orders:: Unexpected error - {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def list_all_work_orders(
    db: Session,
    statuses: str,
    page: int,
    page_size: int,
    keyword: str,
    current_member: Members
):
    """
    Retrieve a paginated list of work orders assigned to the current member,
    with optional status filtering, keyword search, and project name.
    Adds `has_started_working_at` if assignee has started working, based on latest time log.
    """
    try:
        member_id = current_member.id

        # Parse statuses
        status_list = [s.strip().upper() for s in statuses.split(",") if s.strip()]
        valid_statuses = [
            status for status in WorkOrderStatusEnum.__members__ if status in status_list
        ]

        # Base query with join to WoAssignee and Projects
        query = (
            db.query(WorkOrder, Projects.name.label("project_name"))
            .join(WoAssignee, WorkOrder.id == WoAssignee.wo_id)
            .outerjoin(Projects, WorkOrder.project_id == Projects.id)
            .filter(WoAssignee.member_id == member_id)
        )

        # Status filter
        if valid_statuses:
            query = query.filter(
                WorkOrder.wo_status.in_(
                    [WorkOrderStatusEnum[s] for s in valid_statuses]
                )
            )

        # Keyword search
        if keyword:
            keyword_filter = f"%{keyword.lower()}%"
            query = query.filter(
                or_(
                    func.lower(WorkOrder.request_no).like(keyword_filter),
                    func.lower(WorkOrder.id).like(keyword_filter),
                )
            )

        # Total count before pagination
        total_items = query.count()

        # Pagination
        if page_size:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            page = 1
            page_size = total_items

        # Order and execute
        rows = query.order_by(WorkOrder.created_at.desc()).all()

        # Format result
        result_data = []
        for wo, project_name in rows:
            wo_dict = wo.to_dict
            wo_dict["project_name"] = project_name

            # Check if any assignee started working
            has_started = False
            started_at = None

            for assignee in wo.wo_assignees:
                if assignee.has_started_working:
                    has_started = True

                    # latest log created_at for this assignee
                    latest_log = (
                        db.query(WoAssigneeTimeLog.created_at)
                        .filter(WoAssigneeTimeLog.wo_assignee_id == assignee.id)
                        .order_by(WoAssigneeTimeLog.created_at.desc())
                        .first()
                    )
                    if latest_log and (started_at is None or latest_log[0] > started_at):
                        started_at = latest_log[0]

            wo_dict["has_started_working"] = has_started
            wo_dict["has_started_working_at"] = (
                started_at.strftime("%Y-%m-%d %H:%M:%S") if started_at else None
            )

            result_data.append(wo_dict)

        page_count = math.ceil(total_items / page_size) if page_size > 0 else 0

        return result_data, page_count, total_items

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Database error while listing work orders."
        )

    except Exception as e:
        logger.exception(f"get_all_work_orders:: Unexpected error - {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


async def delete_work_order_by_id(db: Session, work_order_id: str):
    try:
        message = "Work order deleted successfully."
        work_order = db.query(WorkOrder).filter_by(id=work_order_id).first()
        if not work_order:
            message = "Work order not found."

            return None, message

        # Prevent deletion if status is IN_PROGRESS or COMPLETED
        if work_order.wo_status.value in ["IN_PROGRESS", "COMPLETED"]:
            message = f"Cannot delete work order in '{work_order.wo_status.value}' state."
            return None, message

        # Fetch all WoSchedules linked to this work order
        schedule_infos = db.query(WoSchedules).filter_by(wo_id=work_order_id).all()
        wo_schedule_ids = [schedule.id for schedule in schedule_infos]

        # Delete all ScheduleInstallationMapping related to wo_schedule_ids
        if wo_schedule_ids:
            db.query(ScheduleInstallationMapping).filter(
                ScheduleInstallationMapping.wo_schedule_id.in_(wo_schedule_ids)
            ).delete(synchronize_session=False)

        # Delete WoAssignee entries
        db.query(WoAssignee).filter_by(wo_id=work_order_id).delete()

        # Delete WoSchedules entries
        db.query(WoSchedules).filter_by(wo_id=work_order_id).delete()

        # Delete the WorkOrder itself
        db.delete(work_order)
        db.commit()

        return 1,message

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error while deleting work order.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



async def get_wo_id_from_schedule_id(db: Session, schedule_id: str):
    try:
        # Get schedules with schedule_name
        schedules_data = []
        wo_schedule = db.query(WoSchedules).filter(WoSchedules.schedule_id==schedule_id).order_by(WoSchedules.created_at.desc()).first()
        if wo_schedule:
            return wo_schedule.wo_id
        else:
            return None
    except Exception as e:
        logger.exception(f"get_wo_id_from_schedule_id:: Unexpected error - {e}")
        db.rollback()
        raise e



async def log_work_order_assignee_time(db: Session, work_order_id: str, member_id: str):
    try:
        wo_assignee_time_log_id = None
        # Get today's UTC start and end
        today = datetime.now()
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        work_order_assignee = db.query(WoAssignee).filter(WoAssignee.member_id==member_id, WoAssignee.wo_id==work_order_id).first()
        if work_order_assignee:
            work_order_assignee_log = (
                db.query(WoAssigneeTimeLog)
                .filter(WoAssigneeTimeLog.wo_assignee_id==work_order_assignee.id)
                .filter(WoAssigneeTimeLog.created_at >= start_of_day, WoAssigneeTimeLog.created_at <= end_of_day)
                .order_by(WoAssigneeTimeLog.created_at.desc())
                .first()
            )
            if not work_order_assignee_log:
                wo_assignee_time_log = WoAssigneeTimeLog(
                    wo_assignee_id=work_order_assignee.id,
                    duration=0,
                    created_by=member_id
                )
                db.add(wo_assignee_time_log)
                db.flush()
                wo_assignee_time_log_id = wo_assignee_time_log.id
            else:
                now = datetime.now()
                current_working_duration = (now - work_order_assignee_log.created_at).total_seconds()
                stored_duration = work_order_assignee_log.duration or 0
                work_order_assignee_log.duration = max(0, current_working_duration - stored_duration)
                db.flush()
                wo_assignee_time_log_id = work_order_assignee_log.id
        return wo_assignee_time_log_id
    except SQLAlchemyError:
        db.rollback()
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e


async def start_or_end_installation(db: Session, work_order_id: str, member_id: str, has_started: bool, location_details: dict = {}):
    try:
        start_status = False
        work_order_assignee = db.query(WoAssignee).filter(WoAssignee.member_id==member_id, WoAssignee.wo_id==work_order_id).first()
        if work_order_assignee:
            if has_started:
                # if user starts the task then it will simply add entry to log table
                wo_assignee_time_log = WoAssigneeTimeLog(
                    wo_assignee_id=work_order_assignee.id,
                    duration=0,
                    created_by=member_id
                )
                db.add(wo_assignee_time_log)
                db.flush()
                start_status = True
            else:
                # if user ends the task then we need to check if they forgot to stop it last working day or not 
                today = datetime.now()
                start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                work_order_assignee_log = (
                    db.query(WoAssigneeTimeLog)
                    .filter(WoAssigneeTimeLog.wo_assignee_id==work_order_assignee.id)
                    .filter(WoAssigneeTimeLog.created_at >= start_of_day, WoAssigneeTimeLog.created_at <= end_of_day)
                    .order_by(WoAssigneeTimeLog.created_at.desc())
                    .first()
                )
                if not work_order_assignee_log:
                    # this means user is here for the first time today and didnt start actually
                    # so need to start logging for the day
                    wo_assignee_time_log = WoAssigneeTimeLog(
                        wo_assignee_id=work_order_assignee.id,
                        duration=0,
                        created_by=member_id
                    )
                    db.add(wo_assignee_time_log)
                    db.flush()
                    start_status = True
                else:
                    now = datetime.now()
                    current_working_duration = (now - work_order_assignee_log.created_at).total_seconds()
                    stored_duration = work_order_assignee_log.duration or 0
                    work_order_assignee_log.duration = max(0, current_working_duration - stored_duration)
                    db.flush()
            work_order_assignee.has_started_working = has_started
            work_order_assignee.location_details = location_details
        return start_status
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e

async def is_work_order_assignee_started_working(db: Session, work_order_id: str, member_id: str):
    try:
        work_order_assignee = db.query(WoAssignee).filter(WoAssignee.member_id==member_id, WoAssignee.wo_id==work_order_id).first()
        if work_order_assignee:
            work_order_assignee_logs = (
                db.query(WoAssigneeTimeLog)
                .filter(WoAssigneeTimeLog.wo_assignee_id==work_order_assignee.id)
                .all()
            )
            if len(work_order_assignee_logs) > 0:
                work_order_data = db.query(WorkOrder).get(work_order_id)
                work_order_data.wo_status = "IN_PROGRESS"
                db.flush()
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e



async def get_assignee_logs(db: Session, work_order_id: str, assignee_id: str = None):
    try:
        # Join WoAssignee with Members
        query = (
            db.query(WoAssignee, Members)
            .join(Members, Members.id == WoAssignee.member_id, isouter=True)
            .filter(WoAssignee.wo_id == work_order_id)
        )

        if assignee_id:
            query = query.filter(WoAssignee.created_by == assignee_id)

        assignee_rows = query.order_by(WoAssignee.created_at.desc()).all()

        response_data = []

        for assignee, member in assignee_rows:
            assignee_dict = assignee.to_dict
            assignee_dict["member_name"] = f"{member.first_name} {member.last_name}" if member else None

            # Fetch logs for each assignee
            logs = (
                db.query(WoAssigneeTimeLog)
                .filter(WoAssigneeTimeLog.wo_assignee_id == assignee.id)
                .order_by(WoAssigneeTimeLog.created_at.desc())
                .all()
            )
            assignee_dict["work_logs"] = [log.to_dict for log in logs]

            response_data.append(assignee_dict)

        return response_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e




async def get_all_assignee_logs(db: Session, work_order_id: str):
    try:
        assignees_data = []

        # Fetch all assignees for the given work order
        assignees = db.query(WoAssignee).filter_by(wo_id=work_order_id).all()

        for assignee in assignees:
            # Fetch the logs related to the current assignee
            logs = (
                db.query(WoAssigneeTimeLog)
                .filter(WoAssigneeTimeLog.wo_assignee_id == assignee.id)
                .order_by(WoAssigneeTimeLog.created_at.desc())
                .all()
            )

            # Fetch the member info
            member = db.query(Members).filter_by(id=assignee.member_id).first()

            assignee_dict = assignee.to_dict
            assignee_dict["member_name"] = f"{member.first_name} {member.last_name}" if member else None
            assignee_dict["work_logs"] = [log.to_dict for log in logs]

            assignees_data.append(assignee_dict)

        return assignees_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e


def update_time_log(db: Session, log_id: str, started_at: str, ended_at: str,current_member):
    try:
        message = "Time log updated successfully."
        log = db.query(WoAssigneeTimeLog).filter_by(id=log_id).first()
        if not log:
            message = "Time log not found."

            return None, message

        # Convert string to datetime
        started_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
        ended_dt = datetime.strptime(ended_at, "%Y-%m-%d %H:%M:%S")

        # Duration in hours
        duration = (ended_dt - started_dt).total_seconds()
        log.duration = round(duration, 2)

        db.flush()
    

        return log,message
    except Exception as e:
        import traceback
        print(traceback.print_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def add_time_log(db: Session, wo_id: str, started_at: str, ended_at: str, member_id: str, current_member):
    try:
        message = "Time log created successfully."

        # Find or create the assignee for this wo_id + member_id
        wo_assignee = (
            db.query(WoAssignee)
            .filter_by(wo_id=wo_id, member_id=member_id)
            .first()
        )

        if not wo_assignee:
            return None, "Work order assignee not found."

        # Convert string inputs to datetime
        started_dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S")
        ended_dt = datetime.strptime(ended_at, "%Y-%m-%d %H:%M:%S")

        # Calculate duration in seconds
        duration = (ended_dt - started_dt).total_seconds()

        # Create new WoAssigneeTimeLog
        log = WoAssigneeTimeLog(
            wo_assignee_id=wo_assignee.id,
            duration=round(duration, 2),
            created_by=current_member.id
        )

        db.add(log)
        db.flush()

        return log, message

    except Exception as e:
        import traceback
        print(traceback.print_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



def delete_time_log(db: Session, log_id: str, current_member):
    try:
        message = "Time log deleted successfully."
        log = db.query(WoAssigneeTimeLog).filter_by(id=log_id).first()

        if not log:
            message = "Time log not found."
            return None, message

        db.delete(log)
        return log, message
    except Exception as e:
        import traceback
        print(traceback.print_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def get_next_possible_work_order_number(db: Session) -> str:
    try:
        # Fetch the latest wo_number starting with "DIA-"
        latest_wo = (
            db.query(WorkOrder.wo_number)
            .filter(WorkOrder.wo_number.like("DIA-%"))
            .order_by(WorkOrder.wo_number.desc())
            .first()
        )

        if latest_wo and latest_wo[0]:
            # Extract numeric part safely
            try:
                latest_number = int(latest_wo[0].split("-")[1])
            except (IndexError, ValueError):
                latest_number = 0

            next_number = latest_number + 1
        else:
            # Start fresh if no work orders exist
            next_number = 1

        # Always at least 3 digits, but can grow beyond
        next_wo_number = f"DIA-{next_number:03d}"

        return next_wo_number

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e



