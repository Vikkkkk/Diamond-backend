from collections import defaultdict
from copy import deepcopy
from loguru import logger
from sqlalchemy import and_, func, case, select,or_
from utils.schedule_data_helper import fill_missing_values_in_schedule_data, get_component_wise_price_details, build_schedule_data_dict
from utils.schedule_hardware_data_helper import build_schedule_hardware_dict
from models.adon_opening_fields import AdonOpeningFields
from repositories.schedule_repositories import get_hing_locations, set_location_data, update_schedule_stats
from schemas.ordered_item_schema import COMPONENT_TYPE
from repositories.schedule_summary_repositories import get_schedule_fetaure_data_summary, get_schedule_hardware_fetaure_data_summary
from sqlalchemy.orm import Session,aliased
from fastapi import UploadFile, HTTPException
from models.change_order import ChangeOrder,ChangeOrderStatusEnum
from models.change_order_docs import ChangeOrderDocs
from models.co_schedules import CoSchedules
from utils.common import generate_uuid, upload_to_s3, delete_from_s3
from sqlalchemy.exc import SQLAlchemyError
from models.change_order_status_logs import ChangeOrderStatusLogs
from models.schedules import Schedules
from models.projects import Projects
from models.schedule_data import ScheduleData
from schemas.schedule_data_schema import changeOrderScheduleDataBulkSaveSchema
from utils.common import set_all_priceing_breakdown,get_all_pricing_breakdown
from utils.description_generartor import get_hardware_description
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from models.opening_hardware_materials import OpeningHardwareMaterials
from schemas.hardware_group_material_schema import ScheduleHardwarMaterialRequest
import math
import traceback
 

async def create_change_order(db: Session, data: dict, files: dict, created_by: str):
    try:
        msg = "Change Order created successfully."
        co_number = data["co_number"]
        # --- Validation 1: Must start with DIA-CO ---
        if co_number and not co_number.startswith("DIA-CO"):
            return None, "Change order number must start with 'DIA-CO'."

        # Create ChangeOrder
        co = ChangeOrder(
            project_id=data["project_id"],
            co_number=co_number,
            description=data["description"],
            priority=data.get("priority", 1),
            current_status=data.get("current_status"),
            created_by=created_by,
        )
        db.add(co)
        db.flush()

        # Handle files (only si_type and cca_type)
        for doc_type, file in files.items():
            if doc_type not in ["si_type", "cca_type"]:
                continue

            upload_path = f"change_order/{data['project_id']}/{co.id}/{doc_type}"
            file_path = await upload_to_s3(file, upload_path)

            doc = ChangeOrderDocs(
                co_id=co.id,
                doc_type=doc_type,
                file_name=file.filename,
                file_type=file.content_type,
                file_path=file_path,
                created_by=created_by,
            )
            db.add(doc)

        # Handle schedules
        schedule_ids = [
            i.strip()
            for i in (data.get("schedule_ids") or "").split(",")
            if i.strip()
        ]
        if schedule_ids:
            schedules = db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).all()

            for sched in schedules:
                sched.is_in_change_order = True
                db.add(sched)
                # schedule_data
                schedule_data_records = db.query(ScheduleData).filter_by(
                    schedule_id=sched.id, latest_data=True
                ).all()
                schedule_data_json = {
                    "current_version": {},
                    "change_trace": {
                        "v0": {}
                    }
                }
                hardware_data_json = {
                    "current_version": {},
                    "change_trace": {
                        "v0": {}
                    }
                }
                schedule_data_record, schedule_price_details = await build_schedule_data_dict(schedule_data_records, sched.quantity)
                schedule_data_json["current_version"] = schedule_data_record
                schedule_data_json["change_trace"]["v0"] = schedule_data_record

                # schedule_hardware_data
                hardware_records = db.query(ScheduleOpeningHardwareMaterials).filter_by(
                    schedule_id=sched.id
                ).all()
                hardware_record_dict = { hr.opening_hardware_material_id: hr.quantity for hr in hardware_records}
                hardware_record = await build_schedule_hardware_dict(db, hardware_record_dict, sched.id)
                hardware_data_json["current_version"] = hardware_record
                hardware_data_json["change_trace"]["v0"] = hardware_record
                schedule_pricing_details = schedule_price_details
                hardware_pricing_details =  hardware_record.get("price_details", {})

                co_schedule = CoSchedules(
                    co_id=co.id,
                    schedule_id=sched.id,
                    current_version="v0",

                    frame_section_file_path=sched.frame_section_file_path,
                    frame_section_file_type=sched.frame_section_file_type,
                    total_amount= schedule_pricing_details.get("total_amount", 0) + hardware_pricing_details.get("total_amount", 0),
                    total_sell_amount= schedule_pricing_details.get("total_sell_amount", 0) + hardware_pricing_details.get("total_sell_amount", 0),
                    total_base_amount=schedule_pricing_details.get("total_base_amount", 0) + hardware_pricing_details.get("total_base_amount", 0),
                    total_extended_sell_amount=schedule_pricing_details.get("total_extended_sell_amount", 0) + hardware_pricing_details.get("total_extended_sell_amount", 0),
                    quantity=sched.quantity,
                    final_amount=schedule_pricing_details.get("final_amount", 0) + hardware_pricing_details.get("final_amount", 0),
                    final_sell_amount=schedule_pricing_details.get("final_sell_amount", 0) + hardware_pricing_details.get("final_sell_amount", 0),
                    final_base_amount=schedule_pricing_details.get("final_base_amount", 0) + hardware_pricing_details.get("final_base_amount", 0),
                    final_extended_sell_amount=schedule_pricing_details.get("final_extended_sell_amount", 0) + hardware_pricing_details.get("final_extended_sell_amount", 0),
                    installation_amount=sched.installation_amount,

                    schedule_data=schedule_data_json,
                    schedule_hardware_data=hardware_data_json,
                    opening_number=sched.opening_number,
                    area=sched.area,
                    location_1=sched.location_1,
                    from_to=sched.from_to,
                    location_2=sched.location_2,
                    door_qty=sched.door_qty,
                    frame_qty=sched.frame_qty,
                    door_material_id=sched.door_material_id,
                    door_material_code=sched.door_material_code,
                    frame_material_id=sched.frame_material_id,
                    frame_material_code=sched.frame_material_code,
                    extra_attributes=sched.extra_attributes,
                    door_type=sched.door_type,
                    swing=sched.swing,

                    created_by=created_by,
                )
                db.add(co_schedule)

        db.flush()
        db.refresh(co)
        return co.id, msg

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error occurred during change order creation."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during change order creation: {str(e)}"
        )


# --------------------------------------------
# Transition rules and flags
# --------------------------------------------
STATUS_TRANSITIONS = {
    ChangeOrderStatusEnum.PENDING: {
        ChangeOrderStatusEnum.IN_REVIEW,
        ChangeOrderStatusEnum.CANCELLED,
    },
    ChangeOrderStatusEnum.IN_REVIEW: {
        ChangeOrderStatusEnum.APPROVED,
        ChangeOrderStatusEnum.REJECTED,
        ChangeOrderStatusEnum.CANCELLED,
    },
    ChangeOrderStatusEnum.APPROVED: set(),
    ChangeOrderStatusEnum.REJECTED: set(),
    ChangeOrderStatusEnum.CANCELLED: set(),
    ChangeOrderStatusEnum.COMPLETED: set(),
}


def is_valid_status_transition(old_status: ChangeOrderStatusEnum, new_status: ChangeOrderStatusEnum) -> bool:
    allowed_next = STATUS_TRANSITIONS.get(old_status, set())
    return new_status in allowed_next


def get_schedule_flags(status: ChangeOrderStatusEnum) -> dict:
    return {
        "is_in_change_order": status in {
            ChangeOrderStatusEnum.PENDING,
            ChangeOrderStatusEnum.IN_REVIEW,
            ChangeOrderStatusEnum.APPROVED,
        },
        "is_freezed": status in {
            ChangeOrderStatusEnum.IN_REVIEW,
            ChangeOrderStatusEnum.APPROVED,
        },
    }


def update_schedule_flags(schedule, status: ChangeOrderStatusEnum, db: Session):
    flags = get_schedule_flags(status)
    schedule.is_in_change_order = flags["is_in_change_order"]
    schedule.is_freezed = flags["is_freezed"]
    db.add(schedule)


async def update_change_order(
    db: Session,
    project_id: str,
    change_order_id: str,
    data: dict,
    files: dict,
    updated_by: str,
):
    try:
        msg = "Change Order updated successfully."

        # --- Validation: wo_number ---
        wo_number = data.get("wo_number")
        if wo_number and not wo_number.startswith("DIA-CO"):
            return None, "Change order number must start with 'DIA-CO'."

        # --- Fetch ChangeOrder ---
        co = (
            db.query(ChangeOrder)
            .filter_by(id=change_order_id, project_id=project_id)
            .first()
        )
        if not co:
            return None, "Change Order not found for this project."

        # --- Update basic fields ---
        if data.get("description") is not None:
            co.description = data["description"]
        if data.get("priority") is not None:
            co.priority = data["priority"]

        if data.get("current_status") is not None:
            new_status = ChangeOrderStatusEnum(data["current_status"])

            if co.current_status != new_status:
                # validate only if actual status is changing
                if not is_valid_status_transition(co.current_status, new_status):
                    return None, f"Invalid status transition: {co.current_status.value} → {new_status.value}"

                co.current_status = new_status

                log_entry = ChangeOrderStatusLogs(
                    co_id=co.id,
                    status=new_status,
                    created_by=updated_by,
                )
                db.add(log_entry)

                # --- Update flags for linked schedules ---
                linked_schedules = db.query(CoSchedules).filter_by(co_id=co.id).all()
                for co_sched in linked_schedules:
                    sched = db.query(Schedules).filter_by(id=co_sched.schedule_id).first()
                    if sched:
                        update_schedule_flags(sched, new_status, db)

        # --- Replace docs (si_type / cca_type only) ---
        for doc_type, file in files.items():
            if not file or doc_type not in ["si_type", "cca_type"]:
                continue

            old_docs = (
                db.query(ChangeOrderDocs)
                .filter_by(co_id=change_order_id, doc_type=doc_type)
                .all()
            )

            # Delete old docs from S3
            for old_doc in old_docs:
                if old_doc.file_path:
                    try:
                        await delete_from_s3(old_doc.file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete {old_doc.file_path} from S3: {e}")

            # Delete old DB entries
            db.query(ChangeOrderDocs).filter_by(co_id=change_order_id, doc_type=doc_type).delete()

            # Upload new file
            upload_path = f"change_order/{project_id}/{co.id}/{doc_type}"
            file_path = await upload_to_s3(file, upload_path)

            new_doc = ChangeOrderDocs(
                co_id=co.id,
                doc_type=doc_type,
                file_name=file.filename,
                file_type=file.content_type,
                file_path=file_path,
                created_by=updated_by,
            )
            db.add(new_doc)

        # --- Update schedules if schedule_ids provided ---
        if data.get("schedule_ids") is not None:
            # Remove old co_schedules
            db.query(CoSchedules).filter_by(co_id=change_order_id).delete()

            schedule_ids = [i.strip() for i in data["schedule_ids"].split(",") if i.strip()]
            if schedule_ids:
                schedules = db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).all()
                for sched in schedules:
                    update_schedule_flags(sched, co.current_status, db)

                    # --- Build schedule_data ---
                    schedule_data_records = db.query(ScheduleData).filter_by(
                        schedule_id=sched.id, latest_data=True
                    ).all()

                    schedule_data_json = {"current_version": {}, "change_trace": {"v0": {}}}
                    hardware_data_json = {"current_version": {}, "change_trace": {"v0": {}}}

                    schedule_data_record, schedule_price_details = await build_schedule_data_dict(
                        schedule_data_records, sched.quantity
                    )
                    schedule_data_json["current_version"] = schedule_data_record
                    schedule_data_json["change_trace"]["v0"] = schedule_data_record

                    # --- Build hardware_data ---
                    hardware_records = db.query(ScheduleOpeningHardwareMaterials).filter_by(
                        schedule_id=sched.id
                    ).all()
                    hardware_record_dict = {hr.opening_hardware_material_id: hr.quantity for hr in hardware_records}
                    hardware_record = await build_schedule_hardware_dict(db, hardware_record_dict, sched.id)
                    hardware_data_json["current_version"] = hardware_record
                    hardware_data_json["change_trace"]["v0"] = hardware_record

                    hardware_pricing_details = hardware_record.get("price_details", {})

                    # --- Create CoSchedules entry ---
                    co_schedule = CoSchedules(
                        co_id=co.id,
                        schedule_id=sched.id,
                        current_version="v0",

                        frame_section_file_path=sched.frame_section_file_path,
                        frame_section_file_type=sched.frame_section_file_type,
                        total_amount=schedule_price_details.get("total_amount", 0) + hardware_pricing_details.get("total_amount", 0),
                        total_sell_amount=schedule_price_details.get("total_sell_amount", 0) + hardware_pricing_details.get("total_sell_amount", 0),
                        total_base_amount=schedule_price_details.get("total_base_amount", 0) + hardware_pricing_details.get("total_base_amount", 0),
                        total_extended_sell_amount=schedule_price_details.get("total_extended_sell_amount", 0) + hardware_pricing_details.get("total_extended_sell_amount", 0),
                        quantity=sched.quantity,
                        final_amount=schedule_price_details.get("final_amount", 0) + hardware_pricing_details.get("final_amount", 0),
                        final_sell_amount=schedule_price_details.get("final_sell_amount", 0) + hardware_pricing_details.get("final_sell_amount", 0),
                        final_base_amount=schedule_price_details.get("final_base_amount", 0) + hardware_pricing_details.get("final_base_amount", 0),
                        final_extended_sell_amount=schedule_price_details.get("final_extended_sell_amount", 0) + hardware_pricing_details.get("final_extended_sell_amount", 0),
                        installation_amount=sched.installation_amount,

                        schedule_data=schedule_data_json,
                        schedule_hardware_data=hardware_data_json,

                        opening_number=sched.opening_number,
                        area=sched.area,
                        location_1=sched.location_1,
                        from_to=sched.from_to,
                        location_2=sched.location_2,
                        door_qty=sched.door_qty,
                        frame_qty=sched.frame_qty,
                        door_material_id=sched.door_material_id,
                        door_material_code=sched.door_material_code,
                        frame_material_id=sched.frame_material_id,
                        frame_material_code=sched.frame_material_code,
                        extra_attributes=sched.extra_attributes,
                        door_type=sched.door_type,
                        swing=sched.swing,

                        created_by=updated_by,
                    )
                    db.add(co_schedule)

        db.flush()
        db.refresh(co)
        return co.id, msg

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error occurred during change order update.",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during change order update: {str(e)}",
        )

async def delete_change_order(
    db: Session,
    project_id: str,
    change_order_id: str,
):
    try:
        msg = "Change Order deleted successfully."

        # Fetch the ChangeOrder scoped by project
        co = db.query(ChangeOrder).filter_by(id=change_order_id, project_id=project_id).first()
        if not co:
            return None, "Change Order not found for this project."

        # Delete docs from S3 + DB
        docs = db.query(ChangeOrderDocs).filter_by(co_id=co.id).all()
        for doc in docs:
            if doc.file_path:
                try:
                    await delete_from_s3(doc.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete {doc.file_path} from S3: {e}")

        db.query(ChangeOrderDocs).filter_by(co_id=co.id).delete()

        # Get all schedule IDs linked to this change order
        schedule_ids = [
            s.schedule_id for s in db.query(CoSchedules.schedule_id)
            .filter(CoSchedules.co_id == co.id)
            .all()
        ]

        # Update them without join
        if schedule_ids:
            db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).update(
                {
                    Schedules.is_freezed: False,
                    Schedules.is_in_change_order: False
                },
                synchronize_session=False
            )

        # Delete schedules linked to the change order
        db.query(CoSchedules).filter_by(co_id=co.id).delete()

        # Delete status logs
        db.query(ChangeOrderStatusLogs).filter_by(co_id=co.id).delete()

        # Finally, delete the ChangeOrder
        db.delete(co)

        db.flush()
        return co.id, msg

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemy error during change order deletion: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred during change order deletion.")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during change order deletion: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during change order deletion: {str(e)}")


async def get_all_change_orders(
    db: Session,
    project_id: str,
    is_completed: bool,
    page: int = None,
    page_size: int = None,
):
    """
    Retrieve a paginated list of change orders for a given project_id,
    filtered by completion status. Includes no_of_openings.
    """
    try:
        # Determine status filter based on completion flag
        if is_completed:
            status_filter = [
                ChangeOrderStatusEnum.COMPLETED,
                ChangeOrderStatusEnum.REJECTED,
                ChangeOrderStatusEnum.CANCELLED,
            ]
        else:
            status_filter = [
                ChangeOrderStatusEnum.APPROVED,
                ChangeOrderStatusEnum.PENDING,
                ChangeOrderStatusEnum.IN_REVIEW,
            ]

        # Base query with schedule count
        query = (
            db.query(
                ChangeOrder,
                Projects.name.label("project_name"),
                func.count(CoSchedules.schedule_id).label("openings_count"),
            )
            .join(Projects, Projects.id == ChangeOrder.project_id)
            .outerjoin(CoSchedules, CoSchedules.co_id == ChangeOrder.id)
            .filter(
                ChangeOrder.project_id == project_id,
                ChangeOrder.current_status.in_(status_filter),
            )
            .group_by(ChangeOrder.id, Projects.name)
        )

        total_items = query.count()

        # Default pagination values
        if not page:
            page = 1
        if not page_size:
            page_size = total_items if total_items > 0 else 1

        offset = (page - 1) * page_size

        # Apply order_by BEFORE pagination
        change_orders = (
            query.order_by(ChangeOrder.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        result_data = []
        for co, project_name, openings_count in change_orders:
            co_data = co.to_dict
            co_data["project_name"] = project_name
            co_data["openings_count"] = openings_count
            result_data.append(co_data)

        page_count = math.ceil(total_items / page_size) if page_size > 0 else 0

        return result_data, page_count, total_items

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error while listing change orders.")
    except Exception as e:
        logger.exception(f"get_all_change_orders:: Unexpected error - {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



async def get_change_order_detail(db: Session, change_order_id: str):
    try:
        # Fetch ChangeOrder
        co = (
            db.query(ChangeOrder)
            .filter(ChangeOrder.id == change_order_id)
            .first()
        )
        if not co:
            return None

        # Fetch related docs
        docs = (
            db.query(ChangeOrderDocs)
            .filter(ChangeOrderDocs.co_id == co.id)
            .all()
        )

        # Map docs by doc_type
        doc_map = {
            doc.doc_type: {
                "id": doc.id,
                "doc_type": doc.doc_type,
                "file_name": doc.file_name,
                "file_type": doc.file_type,
                "file_path": doc.file_path,
            }
            for doc in docs
        }

        co_schedules = (
            db.query(CoSchedules)
            .filter(CoSchedules.co_id == co.id)
            .all()
        )

        schedules_data = []
        for sched in co_schedules:
            schedules_data.append({
                "schedule_id": sched.schedule_id,
                "frame_section_file_path": sched.frame_section_file_path,
                "frame_section_file_type": sched.frame_section_file_type,
                "opening_number":sched.opening_number,
                "area": sched.area,
                "location_1": sched.location_1,
                "from_to": sched.from_to,
                "location_2": sched.location_2,
                "door_qty": sched.door_qty,
                "frame_qty": sched.frame_qty,
                "door_material_id": sched.door_material_id,
                "door_material_code": sched.door_material_code,
                "frame_material_id": sched.frame_material_id,
                "frame_material_code": sched.frame_material_code,
                "extra_attributes": sched.extra_attributes,
                "door_type": sched.door_type,
                "swing": sched.swing,
            })

        # Final CO dict
        co_data = co.to_dict
        co_data.update({
            "si_type": doc_map.get("si_type"),
            "cca_type": doc_map.get("cca_type"),
            "schedules": schedules_data,
        })

        return co_data

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred during change order fetch.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error during change order fetch: {str(e)}")



async def get_next_possible_change_order_number(db: Session) -> str:
    try:
        # Fetch latest co_number starting with "DIA-CO-"
        latest_co = (
            db.query(ChangeOrder.co_number)
            .filter(ChangeOrder.co_number.like("DIA-CO-%"))
            .order_by(ChangeOrder.co_number.desc())
            .first()
        )

        if latest_co and latest_co[0]:
            # Extract numeric part
            try:
                latest_number = int(latest_co[0].split("-")[-1])
            except (IndexError, ValueError):
                latest_number = 0

            next_number = latest_number + 1
        else:
            # Start fresh if no change orders exist
            next_number = 1

        # Always at least 3 digits
        next_co_number = f"DIA-CO-{next_number:03d}"

        return next_co_number

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e



async def get_change_order_openings_info(db: Session, project_id: str):
    """
    Fetch openings (schedules from CoSchedules) only for approved/rejected/partially_approved/cancelled change orders,
    and include schedules that have any shipped items.
    """
    try:
        not_allowed_statuses = [
            ChangeOrderStatusEnum.PENDING,
            ChangeOrderStatusEnum.IN_REVIEW,
        ]

        # Get schedules linked to certain change orders
        query = (
            db.query(CoSchedules)
            .join(ChangeOrder, CoSchedules.co_id == ChangeOrder.id)
            .filter(
                ChangeOrder.project_id == project_id,
                ChangeOrder.current_status.in_(not_allowed_statuses)
            )
            .order_by(ChangeOrder.created_at.desc())
        )

        openings = query.all()
        change_order_openings = []

        if openings:
            for co_schedule in openings:
                change_order_openings.append(co_schedule.schedule_id)
            change_order_openings = list(set(change_order_openings))

        print("change_order_openings:: ", change_order_openings)

        # Filter Schedules
        query = (
            db.query(Schedules)
            .filter(
                Schedules.project_id == project_id,
                Schedules.id.notin_(change_order_openings)
            )
            .order_by(Schedules.created_at.desc())
        )
        return query.all()
    except Exception as error:
        print("error:: ", error)
        raise

async def get_frame_hardware_prep_data(db: Session, schedule_id: str, component: str):
    try:
        if component == "FRAME":
            await set_location_data(db, schedule_id)
            location_data = await get_hing_locations(db, schedule_id, component)
            if location_data is not None:
                hing_loc_data = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == "hinge_location_on_frame").first()
                return {
                        "schedule_id": schedule_id,
                        "name": hing_loc_data.name, 
                        "desc": hing_loc_data.desc, 
                        "component": COMPONENT_TYPE.HARDWARE.value,
                        "part_number": None,
                        "value": location_data,
                        "adon_field_id": hing_loc_data.id,
                        "is_adon_field": True,
                        "has_price_dependancy": False,
                        "margin": 0,
                        "markup": 0,
                        "discount": 0,
                        "quantity": 1,
                        "is_manual": False,
                        "surcharge": 0,
                        "price_data": [],
                        "option_code": None,
                        "feature_code": None,
                        "feature_data": {},
                        "discount_type": "PERCENTAGE",
                        "is_table_data": False,
                        "surcharge_type": "PERCENTAGE",
                        "additional_data": None,
                        "is_basic_discount": False,
                        "adon_field_option_id": None,
                        "total_amount": 0,
                        "total_sell_amount": 0,
                        "total_base_amount": 0,
                        "total_extended_sell_amount": 0,
                        "final_amount": 0,
                        "final_sell_amount": 0,
                        "final_base_amount": 0,
                        "final_extended_sell_amount": 0
                    }
        return None
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"set_hardware_prep_data:: Error : {e}")
        raise e



async def update_co_schedule_data(
    db: Session, co_id: str, payload: changeOrderScheduleDataBulkSaveSchema, updated_by: str
):
    try:
        co_schedule = (
            db.query(CoSchedules)
            .filter(
                CoSchedules.co_id == co_id,
                CoSchedules.schedule_id == payload.schedule_id
            )
            .first()
        )
        if not co_schedule:
            return None
        # Always deepcopy to avoid in-place mutation issues with JSON
        hardware_data = deepcopy(
            co_schedule.schedule_hardware_data or {"current_version": {}, "change_trace": {}}
        )
        schedule_data = deepcopy(
            co_schedule.schedule_data or {"current_version": {}, "change_trace": {}}
        )
        # print("hardware_data:: ", hardware_data["change_trace"].keys())
        # print("schedule_data:: ", schedule_data["change_trace"].keys())
        component_key = f'{payload.component or "GENERAL"} {payload.part_number or ""}'.strip()
        current_version_data = {component_key: payload.fields}
        schedule_data_version = {}
        if component_key not in schedule_data["current_version"]:
            schedule_data["current_version"][component_key] = {}
            next_version = co_schedule.current_version or "v0"
            old_data = schedule_data["current_version"]
            old_data = {component_key: details["fields"] for component_key, details in old_data.items()}
            schedule_data_version = {**old_data, **current_version_data}
        else:
            current_version = co_schedule.current_version or "v0"
            next_version = f'v{(int(current_version.replace("v", ""))+1)}'
            old_data = schedule_data["change_trace"][co_schedule.current_version]
            old_data = {component_key: details["fields"] for component_key, details in old_data.items()}
            schedule_data_version = {**old_data, **current_version_data}
        # Fill missing values from v0 if any
        schedule_data_version = await fill_missing_values_in_schedule_data(schedule_data_version, schedule_data.get("change_trace", {}).get("v0", {}))
        # --- Calculate component-wise and overall pricing ---
        schedule_data_version = await set_all_priceing_breakdown(schedule_data_version)
        component_wise_schedule_data, total_pricing = await get_component_wise_price_details(schedule_data_version, co_schedule.quantity or 1)
        # Update schedule_data
        schedule_data["change_trace"][next_version] = component_wise_schedule_data
        schedule_data["current_version"] = component_wise_schedule_data
        hardware_data["change_trace"][next_version] = hardware_data.get("current_version", {})
        schedule_pricing_details =  total_pricing
        hardware_pricing_details =  hardware_data.get("current_version", {}).get("price_details", {})
        # --- Assign into co_schedule ---
        co_schedule.schedule_data = schedule_data
        co_schedule.schedule_hardware_data = hardware_data
        co_schedule.current_version = next_version
        co_schedule.total_amount = schedule_pricing_details.get("total_amount", 0) + hardware_pricing_details.get("total_amount", 0)
        co_schedule.total_base_amount = schedule_pricing_details.get("total_base_amount", 0) + hardware_pricing_details.get("total_base_amount", 0)
        co_schedule.total_sell_amount = schedule_pricing_details.get("total_sell_amount", 0) + hardware_pricing_details.get("total_sell_amount", 0)
        co_schedule.total_extended_sell_amount = schedule_pricing_details.get("total_extended_sell_amount", 0) + hardware_pricing_details.get("total_extended_sell_amount", 0)
        co_schedule.final_amount = schedule_pricing_details.get("final_amount", 0) + hardware_pricing_details.get("final_amount", 0)
        co_schedule.final_base_amount = schedule_pricing_details.get("final_base_amount", 0) + hardware_pricing_details.get("final_base_amount", 0)
        co_schedule.final_sell_amount = schedule_pricing_details.get("final_sell_amount", 0) + hardware_pricing_details.get("final_sell_amount", 0)
        co_schedule.final_extended_sell_amount = schedule_pricing_details.get("final_extended_sell_amount", 0) + hardware_pricing_details.get("final_extended_sell_amount", 0)
        co_schedule.created_by = updated_by
        # Persist
        db.add(co_schedule)
        db.flush()
        db.refresh(co_schedule)
        return co_schedule.to_dict
    except Exception as e:
        db.rollback()
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error updating schedule data: {str(e)}")



async def get_change_order_schedule_data(db: Session, co_id: str, opening_type: str, part_number: str, schedule_id: str):
    try:
        co_schedule = (
            db.query(CoSchedules)
            .filter(CoSchedules.co_id == co_id, CoSchedules.schedule_id == schedule_id)
            .first()
        )
        if not co_schedule or not co_schedule.schedule_data:
            return []
        component_key = f'{opening_type} {part_number or ""}'.strip()
        schedule_data_current_version = co_schedule.schedule_data.get("current_version", {})
        schedule_data_current_version = schedule_data_current_version.get(component_key) if component_key in schedule_data_current_version else {}
        schedule_data_current_version_fields = schedule_data_current_version.get("fields", {})
        response = []
        for field_key, item in schedule_data_current_version_fields.items():
            response.append(item)
        return response
    except Exception as e:
        logger.exception(f"get_change_order_schedule_data:: Error: {str(e)}")
        raise e



async def update_co_hardware_data(
    db: Session, co_id: str, schedule_id: str, payload: ScheduleHardwarMaterialRequest, updated_by: str
):
    try:
        co_schedule = (
            db.query(CoSchedules)
            .filter(
                CoSchedules.co_id == co_id,
                CoSchedules.schedule_id == schedule_id
            )
            .first()
        )
        if not co_schedule:
            return None
        # Always deepcopy to avoid in-place mutation issues and set safe defaults
        hardware_data = deepcopy(co_schedule.schedule_hardware_data or {"current_version": {}, "change_trace": {}})
        schedule_data = deepcopy(co_schedule.schedule_data or {"current_version": {}, "change_trace": {}})
        # Versioning
        current_version = co_schedule.current_version or "v0"
        try:
            current_num = int(current_version.replace("v", ""))
        except ValueError:
            current_num = 0
        next_version = f"v{current_num + 1}"
        # Build new version dict
        price_breakdown_enriched_data = await build_schedule_hardware_dict(db, payload.hardware_materials, schedule_id)
        # Update JSON
        if "change_trace" in hardware_data:
            hardware_data["change_trace"][next_version] = price_breakdown_enriched_data
        else:
            hardware_data["change_trace"] = {}
            hardware_data["change_trace"][next_version] = price_breakdown_enriched_data
        hardware_data["current_version"] = price_breakdown_enriched_data
        if "change_trace" in schedule_data:
            schedule_data["change_trace"][next_version] = schedule_data.get("current_version", {})
        else:
            schedule_data["change_trace"] = {}
            schedule_data["change_trace"][next_version] = schedule_data.get("current_version", {})
        schedule_pricing_details =  schedule_data.get("current_version", {}).get("price_details", {})
        hardware_pricing_details =  price_breakdown_enriched_data.get("price_details", {})
        # --- Assign back ---
        co_schedule.schedule_hardware_data = hardware_data
        co_schedule.schedule_data = schedule_data
        co_schedule.current_version = next_version
        co_schedule.total_amount = schedule_pricing_details.get("total_amount", 0) + hardware_pricing_details.get("total_amount", 0)
        co_schedule.total_base_amount = schedule_pricing_details.get("total_base_amount", 0) + hardware_pricing_details.get("total_base_amount", 0)
        co_schedule.total_sell_amount = schedule_pricing_details.get("total_sell_amount", 0) + hardware_pricing_details.get("total_sell_amount", 0)
        co_schedule.total_extended_sell_amount = schedule_pricing_details.get("total_extended_sell_amount", 0) + hardware_pricing_details.get("total_extended_sell_amount", 0)
        co_schedule.final_amount = schedule_pricing_details.get("final_amount", 0) + hardware_pricing_details.get("final_amount", 0)
        co_schedule.final_base_amount = schedule_pricing_details.get("final_base_amount", 0) + hardware_pricing_details.get("final_base_amount", 0)
        co_schedule.final_sell_amount = schedule_pricing_details.get("final_sell_amount", 0) + hardware_pricing_details.get("final_sell_amount", 0)
        co_schedule.final_extended_sell_amount = schedule_pricing_details.get("final_extended_sell_amount", 0) + hardware_pricing_details.get("final_extended_sell_amount", 0)
        co_schedule.created_by = updated_by
        db.add(co_schedule)
        db.flush()
        db.refresh(co_schedule)
        return co_schedule.to_dict
    except Exception as e:
        print(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating hardware data: {str(e)}")



async def get_change_order_hardware_data(db: Session, co_id: str, schedule_id: str):
    try:
        co_schedule = (
            db.query(CoSchedules)
            .filter(CoSchedules.co_id == co_id, CoSchedules.schedule_id == schedule_id)
            .first()
        )
        if not co_schedule or not co_schedule.schedule_data:
            return []
        hardware_data_current_version = co_schedule.schedule_hardware_data.get("current_version", {})
        hardware_data_current_version_fields = hardware_data_current_version.get("fields", {})
        response = []
        for field_key, item in hardware_data_current_version_fields.items():
            response.append(item)
        return response
    except Exception as e:
        logger.exception(f"get_change_order_hardware_data:: Error: {str(e)}")
        raise e



async def get_change_order_schedule_data_versions(db: Session, co_id: str, schedule_id: str, version: str = "current", is_latest: bool = False):
    try:
        print("version:: ", version, " is_latest:: ", is_latest)
        print("co_id:: ", co_id, " schedule_id:: ", schedule_id)
        co_schedule = (
            db.query(CoSchedules)
            .filter(CoSchedules.co_id == co_id, CoSchedules.schedule_id == schedule_id)
            .first()
        )
        if not co_schedule or not co_schedule.schedule_data:
            return None, None, None
        if not co_schedule or not co_schedule.schedule_hardware_data:
            return None, None, None
        if is_latest:
            version = co_schedule.current_version or "v0"
        else:
            version = version or co_schedule.current_version or "v0"
        print("final version:: ", version)
        hardware_data_version = co_schedule.schedule_hardware_data.get("change_trace", {})
        hardware_data_current_version_fields = hardware_data_version.get(version, {}) if version in hardware_data_version else co_schedule.schedule_hardware_data.get("current_version", {})
        schedule_data_version = co_schedule.schedule_data.get("change_trace", {})
        schedule_data_current_version_fields = schedule_data_version.get(version, {}) if version in schedule_data_version else co_schedule.schedule_data.get("current_version", {})
        return hardware_data_current_version_fields, schedule_data_current_version_fields, {"opening_number": co_schedule.opening_number, "schedule_id": co_schedule.schedule_id}
    except Exception as e:
        print(traceback.format_exc())
        logger.exception(f"get_change_order_hardware_data:: Error: {str(e)}")
        raise e




async def prepare_current_version_data_to_schedule(
    schedule_id: str,
    current_schedule_hardware_data: dict,
    current_schedule_data: dict,
):
    """
    Prepare current_version data from schedule_data and schedule_hardware_data
    """
    try:
        # Flatten nested dict {component: {field_name: field_data}}
        flattened_schedule_door_data_records = []
        flattened_schedule_frame_data_records = []
        flattened_schedule_hardware_data_records = []

        for component, fields in current_schedule_data.items():
            fields = fields.get("fields", {})
            for _, field_val in fields.items():
                if "HARDWARE" in component:
                    flattened_schedule_hardware_data_records.append({
                        "desc": field_val.get("desc"),
                        "opening_hardware_material_id": field_val.get("opening_hardware_material_id"),
                        "schedule_id": schedule_id,
                        "total_amount": field_val.get("total_amount", 0),
                        "total_sell_amount": field_val.get("total_sell_amount", 0),
                        "total_base_amount": field_val.get("total_base_amount", 0),
                        "total_extended_sell_amount": field_val.get("total_extended_sell_amount", 0),
                        "quantity": field_val.get("quantity", 1),
                        "final_amount": field_val.get("final_amount", 0),
                        "final_sell_amount": field_val.get("final_sell_amount", 0),
                        "final_base_amount": field_val.get("final_base_amount", 0),
                        "final_extended_sell_amount": field_val.get("final_extended_sell_amount", 0),
                    })
                if "DOOR" in component:
                    flattened_schedule_door_data_records.append({
                        "schedule_id": schedule_id,
                        "name": field_val.get("name"),
                        "desc": field_val.get("desc"),
                        "value": field_val.get("value"),
                        "component": field_val.get("component"),
                        "part_number": field_val.get("part_number"),
                        "feature_code": field_val.get("feature_code"),
                        "option_code": field_val.get("option_code"),
                        "feature_data": field_val.get("feature_data"),
                        "price_data": field_val.get("price_data"),
                        "additional_data": field_val.get("additional_data"),
                        "total_amount": field_val.get("total_amount", 0),
                        "total_sell_amount": field_val.get("total_sell_amount", 0),
                        "total_base_amount": field_val.get("total_base_amount", 0),
                        "total_extended_sell_amount": field_val.get("total_extended_sell_amount", 0),
                        "quantity": field_val.get("quantity", 1),
                        "final_amount": field_val.get("final_amount", 0),
                        "final_sell_amount": field_val.get("final_sell_amount", 0),
                        "final_base_amount": field_val.get("final_base_amount", 0),
                        "final_extended_sell_amount": field_val.get("final_extended_sell_amount", 0),
                        "markup": field_val.get("markup", 0),
                        "margin": field_val.get("margin", 0),
                        "is_basic_discount": field_val.get("is_basic_discount", True),
                        "discount": field_val.get("discount", 0),
                        "discount_type": field_val.get("discount_type"),
                        "surcharge": field_val.get("surcharge", 0),
                        "surcharge_type": field_val.get("surcharge_type"),
                        "adon_field_id": field_val.get("adon_field_id"),
                        "adon_field_option_id": field_val.get("adon_field_option_id"),
                        "is_manual": field_val.get("is_manual", False),
                        "is_table_data": field_val.get("is_table_data", False),
                        "is_adon_field": field_val.get("is_adon_field", False),
                        "has_price_dependancy": field_val.get("has_price_dependancy", False),
                        "is_active": True,
                    })
                elif "FRAME" in component:
                    flattened_schedule_frame_data_records.append({
                        "schedule_id": schedule_id,
                        "name": field_val.get("name"),
                        "desc": field_val.get("desc"),
                        "value": field_val.get("value"),
                        "component": field_val.get("component"),
                        "part_number": field_val.get("part_number"),
                        "feature_code": field_val.get("feature_code"),
                        "option_code": field_val.get("option_code"),
                        "feature_data": field_val.get("feature_data"),
                        "price_data": field_val.get("price_data"),
                        "additional_data": field_val.get("additional_data"),
                        "total_amount": field_val.get("total_amount", 0),
                        "total_sell_amount": field_val.get("total_sell_amount", 0),
                        "total_base_amount": field_val.get("total_base_amount", 0),
                        "total_extended_sell_amount": field_val.get("total_extended_sell_amount", 0),
                        "quantity": field_val.get("quantity", 1),
                        "final_amount": field_val.get("final_amount", 0),
                        "final_sell_amount": field_val.get("final_sell_amount", 0),
                        "final_base_amount": field_val.get("final_base_amount", 0),
                        "final_extended_sell_amount": field_val.get("final_extended_sell_amount", 0),
                        "markup": field_val.get("markup", 0),
                        "margin": field_val.get("margin", 0),
                        "is_basic_discount": field_val.get("is_basic_discount", True),
                        "discount": field_val.get("discount", 0),
                        "discount_type": field_val.get("discount_type"),
                        "surcharge": field_val.get("surcharge", 0),
                        "surcharge_type": field_val.get("surcharge_type"),
                        "adon_field_id": field_val.get("adon_field_id"),
                        "adon_field_option_id": field_val.get("adon_field_option_id"),
                        "is_manual": field_val.get("is_manual", False),
                        "is_table_data": field_val.get("is_table_data", False),
                        "is_adon_field": field_val.get("is_adon_field", False),
                        "has_price_dependancy": field_val.get("has_price_dependancy", False),
                        "is_active": True,
                    })
        for field_name, field_val in current_schedule_hardware_data.items():
            flattened_schedule_hardware_data_records.append({
                "desc": field_val.get("desc"),
                "opening_hardware_material_id": field_val.get("opening_hardware_material_id"),
                "schedule_id": schedule_id,
                "total_amount": field_val.get("total_amount", 0),
                "total_sell_amount": field_val.get("total_sell_amount", 0),
                "total_base_amount": field_val.get("total_base_amount", 0),
                "total_extended_sell_amount": field_val.get("total_extended_sell_amount", 0),
                "quantity": field_val.get("quantity", 1),
                "final_amount": field_val.get("final_amount", 0),
                "final_sell_amount": field_val.get("final_sell_amount", 0),
                "final_base_amount": field_val.get("final_base_amount", 0),
                "final_extended_sell_amount": field_val.get("final_extended_sell_amount", 0),
            })
        return flattened_schedule_frame_data_records, flattened_schedule_hardware_data_records, flattened_schedule_door_data_records
    except Exception as e:
        logger.exception(f"prepare_current_version_data_to_schedule:: Error: {str(e)}")
        raise e



async def set_Schedule_door_data_records(
    db: Session,
    schedule_id: str,
    comparison_data_json: dict,
    current_version: dict,
    flattened_schedule_door_data_records: list,
    has_door_ordered: bool = False,
    set_all: bool = True
):
    try:
        if has_door_ordered:
            print("Door has been ordered, creating new versions...")
            if set_all:
                print("set_all is True...")
                # If door has not been ordered, we can simply delete previous da and new records will be for current version
                # Remove old records for this schedule and component "DOOR" only the latest version
                [latest_version] = db.query(ScheduleData.version).filter(
                    ScheduleData.schedule_id == schedule_id, 
                    ScheduleData.latest_data == True, 
                    ScheduleData.component == "DOOR"
                ).first()
                db.query(ScheduleData).filter(
                    ScheduleData.schedule_id == schedule_id, 
                    ScheduleData.latest_data == True, 
                    ScheduleData.component == "DOOR"
                ).update({
                    "latest_data": False
                })
                db.flush()
                # Get next version
                next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                print("next_version:: ", next_version)
                schedule_door_data_records = [ScheduleData(**{**elm, "version": next_version, "latest_data": True}) for elm in flattened_schedule_door_data_records]
                #perform bulk insert
                for itm in schedule_door_data_records:
                    db.add(itm)
                    db.flush()
                # db.bulk_save_objects(schedule_door_data_records)
                print("all data inserted...")
            else:
                print("set_all is False...")
                # If frame has been ordered,we need to create new version for frame 
                # In case we need to add the chnages only for the fields that were changed in the change order
                # comparison_data_json contains only the fields that were changed in the change order
                for component, comp_data in comparison_data_json.items():
                    if "DOOR" in component:
                        print("comparison door data found...")
                        for field_name, field_val in comp_data.items():
                            current_version_field_val = current_version.get(component, {}).get("fields", {}).get(field_name, {})
                            if current_version_field_val:
                                latest_schedule_door_data = db.query(ScheduleData).filter(
                                    ScheduleData.schedule_id == schedule_id,
                                    ScheduleData.name == field_name,
                                    ScheduleData.latest_data == True, 
                                    ScheduleData.component == "DOOR"
                                ).first()
                                print("latest_schedule_door_data:: ", latest_schedule_door_data)
                                if latest_schedule_door_data:
                                    latest_version = latest_schedule_door_data.version
                                    next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                                    db.query(ScheduleData).filter(
                                        ScheduleData.id == latest_schedule_door_data.id
                                    ).update({
                                        "latest_data": False,
                                    })
                                    db.flush()
                                    print("update is done...")
                                else:
                                    [latest_version] = db.query(ScheduleData.version).filter(
                                        ScheduleData.schedule_id == schedule_id, 
                                        ScheduleData.latest_data == True, 
                                        ScheduleData.component == "DOOR"
                                    ).first()
                                    next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                                print("next_version:: ", next_version)
                                if 'id' in current_version_field_val:
                                    del current_version_field_val['id']
                                ScheduleData_record = ScheduleData(
                                    **current_version_field_val,
                                    version=next_version,
                                    latest_data=True,
                                )
                                db.add(ScheduleData_record)
                                db.flush()
                                print("insert is done...")
        else:
            print("Door has NOT been ordered, overwriting old records...")
            # If door has not been ordered, we can simply delete previous da and new records will be for current version
            # Remove old records for this schedule and component "DOOR" only the latest version
            [latest_version] = db.query(ScheduleData.version).filter(
                ScheduleData.schedule_id == schedule_id, 
                ScheduleData.latest_data == True, 
                ScheduleData.component == "DOOR"
            ).first()
            db.query(ScheduleData).filter(
                ScheduleData.schedule_id == schedule_id, 
                ScheduleData.latest_data == True, 
                ScheduleData.component == "DOOR"
            ).delete()
            db.flush()
            schedule_door_data_records = [ScheduleData(**{**elm, "version": latest_version, "latest_data": True}) for elm in flattened_schedule_door_data_records]
            #perform bulk insert
            for itm in schedule_door_data_records:
                db.add(itm)
                db.flush()
            # db.bulk_save_objects(schedule_door_data_records)
            print("all data inserted...")
    except Exception as e:
        logger.exception(f"set_Schedule_door_data_records:: Error: {str(e)}")
        raise e
    


async def set_Schedule_frame_data_records(
    db: Session,
    schedule_id: str,
    comparison_data_json: dict,
    current_version: dict,
    flattened_schedule_frame_data_records: list,
    has_frame_ordered: bool = False,
    set_all: bool = True
):  
    try:
        if has_frame_ordered:
            print("Frame has been ordered, creating new versions...")
            if set_all:
                print("set_all is True...")
                # If frame has not been ordered, we can simply delete previous da and new records will be for current version
                # Remove old records for this schedule and component "FRAME" only the latest version
                [latest_version] = db.query(ScheduleData.version).filter(
                    ScheduleData.schedule_id == schedule_id, 
                    ScheduleData.latest_data == True, 
                    ScheduleData.component == "FRAME"
                ).first()
                db.query(ScheduleData).filter(
                    ScheduleData.schedule_id == schedule_id, 
                    ScheduleData.latest_data == True, 
                    ScheduleData.component == "FRAME"
                ).update({
                    "latest_data": False
                })
                db.flush()
                # Get next version
                next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                print("next_version:: ", next_version)
                db.flush()
                schedule_frame_data_records = [ScheduleData(**{**elm, "version": next_version, "latest_data": True}) for elm in flattened_schedule_frame_data_records]
                #perform bulk insert
                for itm in schedule_frame_data_records:
                    db.add(itm)
                    db.flush()
                # db.bulk_save_objects(schedule_frame_data_records)
                print("all frame data inserted...")
            else:
                print("set_all is False...")
                # If frame has been ordered,we need to create new version for frame 
                comparison_frame_data_json  = comparison_data_json.get("FRAME", {})
                for field_name, field_val in comparison_frame_data_json.items():
                    current_version_field_val = current_version.get("FRAME", {}).get("fields", {}).get(field_name, {})
                    if current_version_field_val:
                        latest_schedule_frame_data = db.query(ScheduleData).filter(
                            ScheduleData.schedule_id == schedule_id,
                            ScheduleData.name == field_name,
                            ScheduleData.latest_data == True, 
                            ScheduleData.component == "FRAME"
                        ).first()
                        if latest_schedule_frame_data:
                            latest_version = latest_schedule_frame_data.version
                            next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                            db.query(ScheduleData).filter(
                                ScheduleData.id == latest_schedule_frame_data.id
                            ).update({
                                "latest_data": False,
                            })
                            db.flush()
                            print("update is done...")
                        else:
                            [latest_version] = db.query(ScheduleData.version).filter(
                                ScheduleData.schedule_id == schedule_id, 
                                ScheduleData.latest_data == True, 
                                ScheduleData.component == "FRAME"
                            ).first()
                            next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                        print("next_version:: ", next_version)
                        if 'id' in current_version_field_val:
                            del current_version_field_val['id']
                        ScheduleData_record = ScheduleData(
                            **current_version_field_val,
                            version=next_version,
                            latest_data=True,
                        )
                        db.add(ScheduleData_record)
                        db.flush()
                        print("insert is done...")
        else:
            print("Frame has NOT been ordered, overwriting old records...")
            # If frame has not been ordered, we can simply delete previous da and new records will be for current version
            [latest_version] = db.query(ScheduleData.version).filter(
                ScheduleData.schedule_id == schedule_id, 
                ScheduleData.latest_data == True, 
                ScheduleData.component == "FRAME"
            ).first()
            db.query(ScheduleData).filter(
                ScheduleData.schedule_id == schedule_id, 
                ScheduleData.latest_data == True, 
                ScheduleData.component == "FRAME"
            ).delete()
            db.flush()
            print("all frame data deleted...")
            schedule_frame_data_records = [ScheduleData(**{**elm, "version": latest_version}) for elm in flattened_schedule_frame_data_records]
            #perform bulk insert
            for itm in schedule_frame_data_records:
                db.add(itm)
                db.flush()
            # db.bulk_save_objects(schedule_frame_data_records)
            print("all frame data inserted...")
    except Exception as e:
        logger.exception(f"set_Schedule_frame_data_records:: Error: {str(e)}")
        raise e



async def set_Schedule_hardware_data_records(
    db: Session,
    schedule_id: str,
    comparison_data_json: dict,
    schedule_hardware_data_json_current_version: dict,
    flattened_schedule_hardware_data_records: list,
    has_hw_ordered: bool = False
):
    """
    Set schedule hardware data records. If hardware has been ordered, create new versions.
    If not, overwrite old records for that schedule_id.
    1. Check if hardware has been ordered.
    2. If ordered, create new version for each hardware item in comparison_data_json.
    3. If not ordered, delete old records and insert new records with the latest version.
    4. Use flattened_schedule_hardware_data_records for inserting new records.
    """
    try:
        if has_hw_ordered:
            print("Hardware has been ordered, creating new versions...")
            # If hardware has been ordered,we need to create new version for hardware
            comparison_hw_data_json  = comparison_data_json.get("HARDWARE", {})
            for field_name, field_val in comparison_hw_data_json.items():
                current_version_field_val = schedule_hardware_data_json_current_version.get(field_name, {})
                if current_version_field_val:
                    latest_schedule_hw_data = db.query(ScheduleOpeningHardwareMaterials).filter(
                        ScheduleOpeningHardwareMaterials.schedule_id == schedule_id,
                        ScheduleOpeningHardwareMaterials.opening_hardware_material_id == current_version_field_val.get("opening_hardware_material_id"),
                        ScheduleOpeningHardwareMaterials.latest_data == True
                    ).first()
                    if latest_schedule_hw_data:
                        # If latest schedule hardware data exists, get the latest version and increment it
                        latest_version = latest_schedule_hw_data.version
                        next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                        db.query(ScheduleOpeningHardwareMaterials).filter(
                            ScheduleOpeningHardwareMaterials.id == latest_schedule_hw_data.id
                        ).update({
                            "latest_data": False,
                        })
                        db.flush()
                        print("update is done...")
                    else:
                        latest_schedule_hw_data = db.query(ScheduleOpeningHardwareMaterials).filter(
                            ScheduleOpeningHardwareMaterials.schedule_id == schedule_id,
                            ScheduleOpeningHardwareMaterials.latest_data == True
                        ).first()
                        latest_version = latest_schedule_hw_data.version
                        next_version = f"v{(int(latest_version.replace('v', ''))+1)}"
                    schedule_hardware_data_record = {
                        "desc": current_version_field_val.get("desc"),
                        "opening_hardware_material_id": current_version_field_val.get("opening_hardware_material_id"),
                        "schedule_id": schedule_id,
                        "total_amount": current_version_field_val.get("total_amount", 0),
                        "total_sell_amount": current_version_field_val.get("total_sell_amount", 0),
                        "total_base_amount": current_version_field_val.get("total_base_amount", 0),
                        "total_extended_sell_amount": current_version_field_val.get("total_extended_sell_amount", 0),
                        "quantity": current_version_field_val.get("quantity", 1),
                        "final_amount": current_version_field_val.get("final_amount", 0),
                        "final_sell_amount": current_version_field_val.get("final_sell_amount", 0),
                        "final_base_amount": current_version_field_val.get("final_base_amount", 0),
                        "final_extended_sell_amount": current_version_field_val.get("final_extended_sell_amount", 0),
                    }
                    ScheduleData_record = ScheduleOpeningHardwareMaterials(
                        **schedule_hardware_data_record,
                        version=next_version,
                        latest_data=True,
                    )
                    db.add(ScheduleData_record)
                    db.flush()
                    print("insert is done...")
        else:
            print("Hardware has NOT been ordered, overwriting old records...")
            # If frame has not been ordered, we can simply delete previous da and new records will be for current version
            [latest_version] = db.query(ScheduleOpeningHardwareMaterials.version).filter(
                ScheduleOpeningHardwareMaterials.schedule_id == schedule_id, 
                ScheduleOpeningHardwareMaterials.latest_data == True
            ).first()
            db.query(ScheduleOpeningHardwareMaterials).filter(
                ScheduleOpeningHardwareMaterials.schedule_id == schedule_id, 
                ScheduleOpeningHardwareMaterials.latest_data == True
            ).delete()
            db.flush()
            schedule_hardware_data_records = [ScheduleOpeningHardwareMaterials(**{**elm, "version": latest_version}) for elm in flattened_schedule_hardware_data_records]
            #perform bulk insert
            for itm in schedule_hardware_data_records:
                print("itm:: ", itm.to_dict or None)
                db.add(itm)
                db.flush()
            # db.bulk_save_objects(schedule_hardware_data_records)
            # db.flush()
            print("all data inserted...")
    except Exception as e:
        logger.exception(f"set_Schedule_hardware_data_records:: Error: {str(e)}")
        raise e
    


async def save_current_version_to_schedule(
    db: Session,
    schedule_id: str,
    schedule_data_json: dict,
    schedule_hardware_data_json: dict,
    schedule_info,
    comparison_data_json: dict,
):
    """
    Save current_version from schedule_data_json into ScheduleData table for the given schedule.
    Overwrites old records for that schedule_id.
    """
    try:
        print("save_current_version_to_schedule:: schedule_id:: ", schedule_id, schedule_info.opening_number)
        current_version = schedule_data_json.get("current_version", {})
        schedule_hardware_data_json_current_version = schedule_hardware_data_json.get("current_version", {})
        schedule_hardware_data_json_current_version = schedule_hardware_data_json_current_version.get("fields", {})
        if not current_version:
            return
        # Flatten nested dict {component: {field_name: field_data}}
        flattened_schedule_door_data_records = []
        flattened_schedule_frame_data_records = []
        flattened_schedule_hardware_data_records = []


        flattened_schedule_frame_data_records, flattened_schedule_hardware_data_records, flattened_schedule_door_data_records = await prepare_current_version_data_to_schedule(
            schedule_id,
            schedule_hardware_data_json_current_version,
            current_version
        )
        if schedule_info:
            await set_Schedule_door_data_records(
                db,
                schedule_id,
                comparison_data_json,
                current_version,
                flattened_schedule_door_data_records,
                has_door_ordered=schedule_info.has_door_ordered,
                set_all=True
            )
            print("Door has been ordered, creating new versions...")
            await set_Schedule_frame_data_records(
                db,
                schedule_id,
                comparison_data_json,
                current_version,
                flattened_schedule_frame_data_records,
                has_frame_ordered=schedule_info.has_frame_ordered,
                set_all=True
            )
            print("Frame has been ordered, creating new versions...")
            await set_Schedule_hardware_data_records(
                db,
                schedule_id,
                comparison_data_json,
                schedule_hardware_data_json_current_version,
                flattened_schedule_hardware_data_records,
                has_hw_ordered=schedule_info.has_hw_ordered
            )
            print("Hardware has been ordered, creating new versions...")
        print("All data saved successfully.")
        db.flush()
        return True
    except Exception as e:
        logger.exception(
            f"save_current_version_to_schedule_data:: Error for schedule {schedule_id}: {e}"
        )
        raise
