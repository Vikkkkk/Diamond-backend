import json
from loguru import logger
from sqlalchemy import and_, func, case, select
from typing import Optional
from repositories.member_repositories import get_member_name_by_id
from repositories.schedule_summary_repositories import get_schedule_fetaure_data_summary, get_schedule_hardware_fetaure_data_summary
from models.schedules import Schedules
from sqlalchemy.orm import Session,aliased
from fastapi import UploadFile, HTTPException
from utils.common import upload_to_s3, delete_from_s3
from utils.description_generartor import get_opening_door_description, get_opening_frame_description
from models.project_installation_plan_docs import ProjectInstallationPlanDocs
from models.schedule_installation_mapping import ScheduleInstallationMapping
from models.members import Members
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError
from models.schedule_data import ScheduleData
from models.schedule_installation_mapping_comments import ScheduleInstallationMappingComments
from models.schedule_installation_mapping_component_data import ScheduleInstallationMappingComponentData
from models.schedule_installation_mapping_activity import ScheduleInstallationMappingActivity
import datetime
from models.schedule_installation_mapping_attachment import ScheduleInstallationMappingAttachment
from models.schedule_installation_mapping_activity import ScheduleInstallationMappingActivity
from models.wo_schedules import WoSchedules
from models.work_order import WorkOrder, WorkOrderStatusEnum
import math


async def get_installation_openings_info(db: Session, project_id: str, work_order_id: Optional[str] = None):
    """
    Retrieves schedule entries for a given project where installation_amount > 0,
    with an optional filter for work_order_id by joining the wo_schedules table.
    Adds a computed 'has_mapping' boolean using JOIN logic.

    Args:
        db (Session): SQLAlchemy database session.
        project_id (str): Project ID.
        work_order_id (Optional[str]): Optional Work Order ID.

    Returns:
        List[Tuple[Schedule, bool]]: Each item has a schedule and a has_mapping flag.
    """
    try:
        # Aliases for table joins
        mapping_alias = aliased(ScheduleInstallationMapping)
        wo_schedule_alias = aliased(WoSchedules)

        # Subquery using EXISTS
        subquery = (
            select(mapping_alias.id)
            .filter(
                mapping_alias.schedule_id == Schedules.id,
                mapping_alias.is_active.is_(True)
            )
            .exists()
        )

        # Base query
        query = db.query(
            Schedules,
            case(
                (subquery, True),
                else_=False
            ).label("has_marker")
        ).filter(
            Schedules.project_id == project_id,
            Schedules.installation_amount > 0
        )

        # Optional join + filter on work_order_id
        if work_order_id:
            query = query.join(
                wo_schedule_alias,
                wo_schedule_alias.schedule_id == Schedules.id
            ).filter(
                wo_schedule_alias.wo_id == work_order_id
            )

        return query.all()

    except Exception as error:
        print("error:: ", error)
        raise


async def get_installation_unassigned_openings_info(
    db: Session,
    project_id: str
):
    """
    Retrieves schedule entries for a given project where installation_amount > 0.
    - If schedule is NOT linked to any WorkOrder -> include it.
    - If schedule IS linked -> only include if all linked WorkOrders are FAILED or CANCELLED.
    """
    try:
        # Aliases
        mapping_alias = aliased(ScheduleInstallationMapping)
        wo_schedule_alias = aliased(WoSchedules)
        wo_alias = aliased(WorkOrder)

        # Allowed statuses for inclusion
        allowed_statuses = [WorkOrderStatusEnum.FAILED, WorkOrderStatusEnum.CANCELLED]

        # Subquery: check if schedule has active mapping
        subquery = (
            select(mapping_alias.id)
            .filter(
                mapping_alias.schedule_id == Schedules.id,
                mapping_alias.is_active.is_(True)
            )
            .exists()
        )

        # Base schedules with installation_amount > 0
        query = (
            db.query(
                Schedules,
                case((subquery, True), else_=False).label("has_marker")
            )
            .filter(
                Schedules.project_id == project_id,
                Schedules.installation_amount > 0,
                Schedules.has_door_shipped == True,
                Schedules.has_frame_shipped == True,
                Schedules.has_hw_shipped == True
            )
        )


        schedules = query.all()

        filtered_results = []
        for sched, has_marker in schedules:
            # Get all work orders linked to this schedule
            wo_statuses = (
                db.query(WorkOrder.wo_status)
                .join(WoSchedules, WoSchedules.wo_id == WorkOrder.id)
                .filter(WoSchedules.schedule_id == sched.id)
                .all()
            )

            wo_statuses = [status[0] for status in wo_statuses]

            if not wo_statuses:
                # No work order assigned -> include
                filtered_results.append((sched, has_marker))
            else:
                # Include only if all linked WOs are FAILED or CANCELLED
                if all(status in allowed_statuses for status in wo_statuses):
                    filtered_results.append((sched, has_marker))

        return filtered_results

    except Exception as error:
        print("error:: ", error)
        raise


async def save_installation_plan_doc(
    db: Session,
    project_id: str,
    area: str,
    current_member: Members,
    file: UploadFile
):
    try:
        upload_path = f"opening_document/{project_id}/installation_doc/{area}"

        # Upload to S3
        file_path = await upload_to_s3(file, upload_path)

        doc = ProjectInstallationPlanDocs(
            area=area,
            project_id=project_id,
            file_name=file.filename,
            content_type=file.content_type,
            file_path=file_path,
            created_by=current_member.id,
        )

        db.add(doc)

        return doc.id

    except SQLAlchemyError as db_err:
        raise HTTPException(status_code=500, detail="Database error occurred.")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload floor plan.")



async def get_floor_plans_info(db: Session, project_id: str, area: str):
    try:
        results = db.query(ProjectInstallationPlanDocs, Members).join(
            Members, Members.id == ProjectInstallationPlanDocs.created_by
        ).filter(
            and_(
                ProjectInstallationPlanDocs.project_id == project_id,
                ProjectInstallationPlanDocs.area == area
            )
        ).all()

        return results

    except Exception as error:
        print("error:: ", error)
        raise error




async def to_assign_opening_to_floor_plan(
    db: Session,
    project_id: str,
    request_data,
    current_member: Members
):
    try:
        # Clean input
        request_data = request_data.model_dump(exclude_unset=True)
        schedule_id = request_data["schedule_id"]

        wo_schedule_data = db.query(WoSchedules).filter(WoSchedules.schedule_id==schedule_id).first()

        # Create main schedule-installation mapping
        mapping = ScheduleInstallationMapping(
            schedule_id=schedule_id,
            schedule_installation_plan_doc_id=request_data["schedule_installation_plan_doc_id"],
            coordinate_data=request_data.get("coordinate_data"),
            wo_schedule_id=wo_schedule_data.id if wo_schedule_data else None,
            created_by=current_member.id,
        )

        db.add(mapping)
        db.flush()

        await set_schedule_installation_mapping_component_data(
            db,
            project_id=project_id,
            schedule_id=request_data["schedule_id"],
            schedule_installation_mapping_id=mapping.id,
            current_user_id=current_member.id
        )
        # db.commit()

        return mapping.id

    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign opening to floor plan.")



async def get_opening_status(db: Session, schedule_installation_mapping_id: str):
    try:
        mapping_prep_data = db.query(ScheduleInstallationMappingComponentData).filter(
            ScheduleInstallationMappingComponentData.schedule_installation_mapping_id == schedule_installation_mapping_id
        ).all()
        prep_status = [elm.status if isinstance(elm.status, str) else elm.status.value for elm in mapping_prep_data]
        print("prep_status:: ",prep_status)
        if prep_status.count("PENDING") == len(prep_status):
            return "PENDING"
        elif prep_status.count("SUCCESS") == len(prep_status):
            return "SUCCESS"
        elif prep_status.count("FAILED") == len(prep_status):
            return "FAILED"
        else:
            return "IN_PROGRESS"
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign opening to floor plan.")


async def add_comment(db, project_id, schedule_installation_mapping_id, comment, attachments, member_id):
    try:
        new_comment = ScheduleInstallationMappingComments(
            project_id=project_id,
            schedule_installation_mapping_id=schedule_installation_mapping_id,
            comment=comment,
            created_by=member_id
        )
        db.add(new_comment)

        db.flush()
        # Process attachments if any
        if attachments:
            for attachment in attachments:
                attachment_record = ScheduleInstallationMappingAttachment(
                    schedule_installation_mapping_id=schedule_installation_mapping_id,
                    schedule_installation_mapping_comment_id=new_comment.id,
                    file_name=attachment.filename,
                    file_type=attachment.content_type,
                    created_by=member_id
                )
                db.add(attachment_record)
                db.flush()

                # "upload_to_s3" to upload the attachment to S3
                upload_path = f"schedule_installation_mapping_attachment/{schedule_installation_mapping_id}/{new_comment.id}/{attachment_record.id}"
                file_path = await upload_to_s3(attachment, upload_path)
                attachment_record.file_path = file_path
        db.refresh(new_comment)
        return new_comment

    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add comment to floor plan.")


async def update_comment(db: Session, comment_id: str, schedule_installation_mapping_id: str, comment: str, attachments: list, project_id: str, deleted_attachment_ids:str, member_id:str):
    try:
        # Fetch the existing comment
        comment_record = db.query(ScheduleInstallationMappingComments).filter(
            ScheduleInstallationMappingComments.id == comment_id
        ).first()

        if not comment_record:
            return None

        # Update fields
        if comment is not None:
            comment_record.comment = comment

        # Process attachments if any
        if attachments:
            for attachment in attachments:
                attachment_record = ScheduleInstallationMappingAttachment(
                    schedule_installation_mapping_id=schedule_installation_mapping_id,
                    schedule_installation_mapping_comment_id=comment_record.id,
                    file_name=attachment.filename,
                    file_type=attachment.content_type,
                    created_by=member_id
                    
                )
                db.add(attachment_record)
                db.flush()

                # "upload_to_s3" to upload the attachment to S3
                upload_path = f"schedule_installation_mapping_attachment/{schedule_installation_mapping_id}/{comment_record.id}/{attachment_record.id}"
                file_path = await upload_to_s3(attachment, upload_path)
                attachment_record.file_path = file_path
        
        # Process deleted attachments
            if deleted_attachment_ids:
                attachment_ids = [id.strip() for id in deleted_attachment_ids.split(',')]
                for attachment_id in attachment_ids:
                    attachment = db.query(ScheduleInstallationMappingAttachment).filter(ScheduleInstallationMappingAttachment.id == attachment_id).first()
                    if attachment:
                        await delete_from_s3(attachment.file_path)

                        db.delete(attachment)
        return comment_record

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred during comment update.")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unexpected error while updating comment.")


async def get_schedule_installation_mappings_data(db: Session, mapping_id: str):
    try:
        result = (
            db.query(ScheduleInstallationMapping,Members)
            .outerjoin(
                ScheduleInstallationMappingComponentData,
                ScheduleInstallationMappingComponentData.schedule_installation_mapping_id == ScheduleInstallationMapping.id
            )
            .outerjoin(
                ScheduleInstallationMappingComments,
                ScheduleInstallationMappingComments.schedule_installation_mapping_id == ScheduleInstallationMapping.id
            )
            .outerjoin(Members, Members.id==ScheduleInstallationMappingComments.created_by)
            .outerjoin(ScheduleInstallationMappingAttachment, ScheduleInstallationMappingAttachment.schedule_installation_mapping_id==ScheduleInstallationMapping.id)
            .filter(ScheduleInstallationMapping.id == mapping_id)
            .order_by(ScheduleInstallationMappingComments.created_at.asc())
            .all()
        )
        return result
    except Exception as e:
        logger.exception(str(e))
        raise e


async def get_schedule_installation_mappings(db: Session, doc_id: str):
    try:
        result = (
            db.query(ScheduleInstallationMapping)
            .filter(ScheduleInstallationMapping.schedule_installation_plan_doc_id == doc_id)
            .all()
        )
        return result
    except Exception as e:
        logger.exception(str(e))
        raise e


async def check_schedule_installation_mapping(
    db: Session,
    schedule_id: str
):
    """
    Check if a schedule installation mapping exists for the given schedule_id.

    """
    try:
        mapping = db.query(ScheduleInstallationMapping).filter(ScheduleInstallationMapping.schedule_id==schedule_id).first()

        exists = True if mapping else False

        return exists  
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to check schedule installation mapping.")


async def set_schedule_installation_mapping_component_data(
    db: Session,
    project_id: str,
    schedule_id: str,
    schedule_installation_mapping_id: str,
    current_user_id: str
):
    try:
        inserted_ids = []
        updated_ids = []
        schedule_info = db.query(Schedules).get(schedule_id)
        schedule_info = schedule_info.to_dict
        schedule_non_hw_data = await get_schedule_fetaure_data_summary(db, schedule_id)
        schedule_data = []
        for info, details in schedule_non_hw_data.items():
            base_features = json.loads(details["base_features"]) if details["base_features"] is not None else {}
            adon_features = json.loads(details["adon_features"]) if details["adon_features"] is not None else {}
            obj = {
                "name": info,
                "base_feature": base_features,
                "adon_feature": adon_features,
                "desc": (
                    await get_opening_door_description(schedule_info, base_features, adon_features)
                    if "DOOR" in info
                    else
                    await get_opening_frame_description(schedule_info, base_features, adon_features)
                ),
                "schedule_opening_hardware_material_id": None
            }
            schedule_data.append(obj)
        schedule_hw_data = await get_schedule_hardware_fetaure_data_summary(db, schedule_id)
        schedule_data.extend(schedule_hw_data)
        for elm in schedule_data:
            existing_data = (
                db.query(ScheduleInstallationMappingComponentData)
                .filter(
                    ScheduleInstallationMappingComponentData.project_id == project_id,
                    ScheduleInstallationMappingComponentData.schedule_id == schedule_id,
                    ScheduleInstallationMappingComponentData.name == elm["name"],
                )
                .first()
            )
            component = elm["name"].replace("1", "").replace("2", "") if elm["schedule_opening_hardware_material_id"] is None else "HARDWARE"
            part_number = 1 if "1" in elm["name"] else 2 if "2" in elm["name"] else 0
            if existing_data:
                existing_data.base_feature = elm["base_feature"]
                existing_data.adon_feature = elm["adon_feature"]
                existing_data.desc = elm["desc"]
                db.flush()
                updated_ids.append(existing_data.id)
            else:
                db_data = ScheduleInstallationMappingComponentData(
                    project_id = project_id,
                    schedule_id = schedule_id,
                    base_feature = elm["base_feature"],
                    adon_feature = elm["adon_feature"],
                    schedule_installation_mapping_id = schedule_installation_mapping_id,
                    schedule_opening_hardware_material_id = elm["schedule_opening_hardware_material_id"],
                    component = component,
                    name = elm["name"],
                    desc = elm["desc"],
                    part_number = part_number,
                    created_by = current_user_id
                )
                db.add(db_data)
                db.flush()
                inserted_ids.append(db_data.id)
        return inserted_ids, updated_ids
    except Exception as e:
        logger.exception(str(e))
        raise e
    


async def log_schedule_installation_mapping_activity(db: Session, schedule_installation_mapping_id: str, activity_type: str, created_by: str, details: dict = None):
    """
    Logs an activity related to a task in the task_activity table.

    :param db: SQLAlchemy session to use for the transaction.
    :param schedule_installation_mapping_id: ID of the schedule_installation_mapping to which this activity is related.
    :param activity_type: Description of the activity.
    :param created_by: ID of the user who performed the activity.
    :param details: Optional dictionary with additional details (e.g., assigned member name, file name, status change).
    """
    try:
        current_member_name = await get_member_name_by_id(db, created_by)
        activity = None
        if activity_type == "Created Opening Marker":
            activity = f"<strong>{current_member_name}</strong> Created Marker for opening - <strong>{details.get('opening_number')}</strong>."
        elif activity_type == "Update Opening Component Installation Status":
            activity = f"""<strong>{details.get("component_name")}</strong> of opening - <strong>{details.get("opening_number")}</strong> installation status updated from <strong>{details.get("previous_status")}</strong> to <strong>{details.get("current_status")}</strong> by <strong>{current_member_name}</strong>."""
        elif activity_type == "Update Opening Installation Status":
            activity = f"""Opening - <strong>{details.get("opening_number")}</strong> installation status updated from <strong>{details.get("previous_status")}</strong> to <strong>{details.get("current_status")}</strong> by <strong>{current_member_name}</strong>."""
        elif activity_type == "Add Opening Installation Comment":
            activity = f"""<strong>{current_member_name}</strong> added new comment to the opening - <strong>{details.get("opening_number")}</strong> with <strong>{details.get("attachments")}.\nComment: <strong>{details.get("comment")}</strong>."""
        elif activity_type == "Update Opening Installation Comment":
            activity = f"""<strong>{current_member_name}</strong> updated comment from '<strong>{details.get("previous_comment")}</strong>' to '<strong>{details.get("current_comment")}</strong>' of opening - <strong>{details.get("opening_number")}</strong>."""
        elif activity_type == "Delete Opening Installation Comment":
            activity = f"""<strong>{current_member_name}</strong> deleted comment '<strong>{details.get("comment")}</strong>' of opening - <strong>{details.get("opening_number")}</strong>."""
        if activity is not None:
            activity = activity.replace("_", " ")
            new_schedule_installtion_mapping_activity = ScheduleInstallationMappingActivity(
                schedule_installation_mapping_id=schedule_installation_mapping_id,
                activity=activity,
                created_by=created_by
            )
            db.add(new_schedule_installtion_mapping_activity)
            db.flush()
            return new_schedule_installtion_mapping_activity.id
        else:
            return None
    except Exception as e:
        logger.exception(str(e))
        raise e


async def schedule_installation_mapping_activities_data(
    db:Session, 
    schedule_installation_mapping_id:str,
    page,
    page_size
):
    try:
        query = (
            db.query(
                ScheduleInstallationMappingActivity,
                func.concat(Members.first_name, ' ', Members.last_name).label("created_by_name")
            )
            .join(Members, ScheduleInstallationMappingActivity.created_by == Members.id)
            .filter(ScheduleInstallationMappingActivity.schedule_installation_mapping_id == schedule_installation_mapping_id)
            .order_by(ScheduleInstallationMappingActivity.created_at.asc())
        )

        total_activities = query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            offset = 0
            page_size = total_activities if total_activities else 1
            page = 1

        schedule_installation_activities = query.all()
        schedule_installation_activity_responses = []
        for activity, created_by_name in schedule_installation_activities:
            activity_data = activity.to_dict
            activity_data["created_by_name"] = created_by_name
            schedule_installation_activity_responses.append(
                activity_data
            )

        # Calculate page count
        page_count = math.ceil(total_activities / page_size) if page_size > 0 else 0

        return schedule_installation_activity_responses, page_count, total_activities

    except Exception as error:
        logger.exception(f"An error occurred while fetching schedule installation activities: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")

