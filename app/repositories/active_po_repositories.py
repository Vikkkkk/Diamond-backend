"""
This file contains all active po releated used repositories.
"""
from loguru import logger
from repositories.update_stats_repositories import calulate_adons, update_area_item_stats, update_section_stats, update_take_off_sheet_stats, update_raw_material_stats
from models.ordered_items import OrderedItems
from models.active_po import ActivePo
import uuid
from sqlalchemy import or_, and_, update, func, text, case, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from utils.order import generate_po_number
import traceback
from utils.common import get_user_time, get_estimated_delivery_date, get_aws_full_path, delete_from_s3, get_order_by_date
from repositories.manufacturer_repositories import get_manufacture_by_id
from models.schedules import Schedules
from models.schedule_data import ScheduleData
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials

def check_order_ids_exist(db: Session, order_ids: list[str]):
    stmt = select(OrderedItems.id).where(OrderedItems.id.in_(order_ids))
    result = db.execute(stmt).scalars().all()

    existing_ids = set(result)
    given_ids = set(order_ids)

    missing_ids = list(given_ids - existing_ids)
    
    if missing_ids:
        raise HTTPException(status_code=404, detail={"message": "Some order_ids not found", "missing_ids": missing_ids})

    return list(existing_ids)

# Function to get total quantity and total price
def get_order_totals(db: Session, order_ids: list[str]):
    stmt = select(
        func.sum(OrderedItems.quantity).label("total_quantity"),
        func.sum(OrderedItems.total_price).label("total_price")
    ).where(OrderedItems.id.in_(order_ids))
    
    result = db.execute(stmt).one()
    return {"total_quantity": result.total_quantity or 0, "total_price": result.total_price or 0.0}


# Function to create a new purchase order (without commit)
def create_purchase_order(db: Session, po_info: dict, total_quantity: float, total_price: float):
    print(">>>>>>>>>>>>>>>>>>>", po_info)
    new_po = ActivePo(
        ordered_item_quantity=total_quantity,
        final_price=total_price,
        **po_info
    )
    
    db.add(new_po)
    db.flush()  # Flush to generate new_po.id without committing
    
    return new_po  # Return the new purchase order object

# Function to update schedule flags based on component type
def update_has_order(db: Session, schedule_ids: list[str], component_type: str):
    """
    Updates the schedule flags and related data based on the component type.

    Example:
        - If component_type == "DOOR"  → has_door_ordered = True
        - If component_type == "FRAME" → has_frame_ordered = True
        - If component_type == "HW"    → has_hw_ordered = True
    """

    if not schedule_ids:
        raise ValueError("schedule_ids cannot be empty")

    # Ensure schedules exist
    schedules = db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).all()
    if not schedules:
        raise ValueError(f"No schedules found for IDs: {schedule_ids}")

    component = component_type.upper()

    # --- Update ScheduleData.has_ordered if field exists ---
    db.query(ScheduleData).filter(
        ScheduleData.component == component,
        ScheduleData.latest_data == True,
        ScheduleData.schedule_id.in_(schedule_ids)
    ).update(
        {"has_ordered": True},
        synchronize_session=False
    )

    # --- Update ScheduleOpeningHardwareMaterials.has_ordered if component is HW ---
    if component in ["HW", "HARDWARE"]:
        db.query(ScheduleOpeningHardwareMaterials).filter(
            ScheduleOpeningHardwareMaterials.schedule_id.in_(schedule_ids),
            ScheduleOpeningHardwareMaterials.latest_data == True
        ).update(
            {"has_ordered": True},
            synchronize_session=False
        )

    # --- Update flags in Schedules table ---
    update_dict = {}
    if component == "DOOR":
        update_dict["has_door_ordered"] = True
    elif component == "FRAME":
        update_dict["has_frame_ordered"] = True
    elif component in ["HW", "HARDWARE"]:
        update_dict["has_hw_ordered"] = True
    else:
        raise ValueError(f"Invalid component_type: {component_type}")

    db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).update(
        update_dict,
        synchronize_session=False
    )

    db.flush()
    return schedules



def update_has_shipped(db: Session, schedule_ids: list[str], component_type: str):
    """
    Updates the schedule flags and related data when items are shipped.

    Example:
        - If component_type == "DOOR"  → has_door_shipped = True
        - If component_type == "FRAME" → has_frame_shipped = True
        - If component_type == "HW"    → has_hw_shipped = True
    """

    if not schedule_ids:
        raise ValueError("schedule_ids cannot be empty")

    schedules = db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).all()
    if not schedules:
        raise ValueError(f"No schedules found for IDs: {schedule_ids}")

    component = component_type.upper()

    # --- Update ScheduleData.has_shipped ---
    db.query(ScheduleData).filter(
        ScheduleData.component == component,
        ScheduleData.latest_data == True,
        ScheduleData.schedule_id.in_(schedule_ids)
    ).update(
        {"has_shipped": True},
        synchronize_session=False
    )

    # --- Update ScheduleOpeningHardwareMaterials.has_shipped if component is HW ---
    if component in ["HW", "HARDWARE"]:
        db.query(ScheduleOpeningHardwareMaterials).filter(
            ScheduleOpeningHardwareMaterials.schedule_id.in_(schedule_ids),
            ScheduleOpeningHardwareMaterials.latest_data == True
        ).update(
            {"has_shipped": True},
            synchronize_session=False
        )

    # --- Update flags in Schedules table ---
    update_dict = {}
    if component == "DOOR":
        update_dict["has_door_shipped"] = True
    elif component == "FRAME":
        update_dict["has_frame_shipped"] = True
    elif component in ["HW", "HARDWARE"]:
        update_dict["has_hw_shipped"] = True
    else:
        raise ValueError(f"Invalid component_type: {component_type}")

    db.query(Schedules).filter(Schedules.id.in_(schedule_ids)).update(
        update_dict,
        synchronize_session=False
    )

    db.flush()
    return schedules

# Function to update the purchase order 

def update_purchase_order(db: Session, active_po_id, po_info: dict, total_quantity: float = None, total_price: float = None):
    """Update a purchase order's details, quantity, and price."""
    po = db.query(ActivePo).filter(ActivePo.id == active_po_id).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found.")

    # Update purchase order info dynamically
    for key, value in po_info.items():
        if hasattr(po, key):  # Ensure the attribute exists before updating
            setattr(po, key, value)

    # Update quantity and price if provided
    if total_quantity is not None:
        po.ordered_item_quantity = total_quantity

    if total_price is not None:
        po.final_price = total_price

    db.flush()
    db.refresh(po)  # Refresh to get updated values
    
    return po

# Function to update order_items with new po_id (without commit)
def update_order_items(db: Session, order_ids: list[str], po_id: str):
    try:
        # Step 1: Set active_po_id to NULL for items currently linked to this PO
        db.query(OrderedItems).filter(OrderedItems.active_po_id == po_id).update({"active_po_id": None})
        db.flush()  # ✅ Only flush, no commit

        print("order_ids", order_ids)

        # Step 2: Assign the new order IDs to the provided PO ID
        stmt = (
            update(OrderedItems)
            .where(OrderedItems.id.in_(order_ids))
            .values(active_po_id=po_id)
        )
        db.execute(stmt)

        db.flush()  # ✅ Flush to execute queries, but no commit

        # Fetch all relevant OrderedItems in one query
        ordered_items = db.query(OrderedItems).filter(OrderedItems.id.in_(order_ids)).all()

        for order_info in ordered_items:
            if not order_info:  # Prevent NoneType issues
                continue  
            manufacture_info = get_manufacture_by_id(db, order_info.manufacturer_id)
            order_info.estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)
        
        db.flush()  # ✅ Final flush to save changes before commit

    except Exception as e:
        db.rollback()  # ✅ Rollback changes on error
        print(traceback.format_exc())
        raise


def get_purchese_orders(db, project_id, component_type):
    query = text("""
    SELECT 
    o.schedule_id,
    o.opening_number,
    o.required_by_date, 
    o.estimated_delivery_date, 
    o.door_mat,
    o.frame_mat,
    o.hand,
    o.door_type,
    po.id as po_id,
    po.po_number, 
    po.ordered_date,
    s.location_1,
    po.final_price,
    po.ordered_item_quantity,
    JSON_ARRAYAGG(
            o.ordered_metadata
            ) AS feature
    FROM active_po po 
    LEFT JOIN ordered_items o ON o.active_po_id = po.id AND o.component_type = :component_type 
    JOIN schedules s ON s.id = o.schedule_id
    """ + (""" AND o.project_id = :project_id""" if project_id else "") + """
    GROUP BY o.schedule_id,  o.opening_number, o.required_by_date, o.estimated_delivery_date, o.door_mat, o.frame_mat, 
                o.hand, o.door_type, po.id, po.po_number, s.location_1, po.final_price;
    """)

    params = {"component_type": component_type}
    if project_id:
        params["project_id"] = project_id

    result = db.execute(query, params)
    ordered_items = result.mappings().all()

    return ordered_items


def get_received_item_listing(db, project_id, component_type):
    query = text("""
    SELECT o.*, s.location_1, s.from_to, s.location_2
    FROM ordered_items o
    JOIN schedules s ON o.schedule_id = s.id
    WHERE o.active_po_id IN (
        -- Select POs where all items are received
        SELECT active_po_id
        FROM ordered_items
        GROUP BY active_po_id
        HAVING COUNT(*) = SUM(CASE WHEN is_received = true THEN 1 ELSE 0 END)
    )
    AND o.project_id = :project_id
    AND o.component_type = :component_type
    AND o.shipping_status != 'DONE';
    """)

    params = {"component_type": component_type}
    if project_id:
        params["project_id"] = project_id

    result = db.execute(query, params)
    items = result.mappings().all()

    return items


def requested_shipping_grouped_items(db):
    query = text("""
    SELECT 
    o.project_id,
    o.project_name, 
    o.project_number, 
    o.shipping_initiate_date,
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', o.id,
            'opening_number', o.opening_number,
            'door_type', o.door_type,
            'hand', o.hand,
            'ordered_metadata', o.ordered_metadata,
            'location_1', s.location_1,
            'to_from', s.from_to,
            'location_2', s.location_2,
            'label_file_path', o.label_file_path,
            'crate_number', o.crate_number,
            'material', 
                CASE 
                    WHEN o.component_type = 'FRAME' THEN o.frame_mat
                    WHEN o.component_type = 'DOOR' THEN o.door_mat
                    ELSE NULL
                END
        )
    ) AS ship_items,
    COUNT(o.id) AS items_to_ship
    FROM ordered_items o
    JOIN schedules s ON o.schedule_id = s.id
    WHERE o.active_po_id IS NOT NULL 
    AND o.shipping_status = 'IN_PROGRESS'
    GROUP BY o.project_id, o.project_name, o.project_number, shipping_initiate_date;
    """)

    params = {}
    result = db.execute(query, params)
    items = result.mappings().all()

    return items



def shipping_grouped_items(db):
    query = text("""
    SELECT 
    o.project_id,
    o.project_name, 
    o.project_number, 
    o.shipment_date,
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', o.id,
            'opening_number', o.opening_number,
            'door_type', o.door_type,
            'hand', o.hand,
            'ordered_metadata', o.ordered_metadata,
            'location_1', s.location_1,
            'to_from', s.from_to,
            'location_2', s.location_2,
            'label_file_path', o.label_file_path,
            'crate_number', o.crate_number,
            'material', 
                CASE 
                    WHEN o.component_type = 'FRAME' THEN o.frame_mat
                    WHEN o.component_type = 'DOOR' THEN o.door_mat
                    ELSE NULL
                END
        )
    ) AS ship_items,
    COUNT(o.id) AS items_to_ship
    FROM ordered_items o
    JOIN schedules s ON o.schedule_id = s.id
    WHERE o.active_po_id IS NOT NULL 
    AND o.shipping_status = 'AWAIT_SHIPPING'
    GROUP BY o.project_id, o.project_name, o.project_number, shipment_date;
    """)

    params = {}
    result = db.execute(query, params)
    items = result.mappings().all()

    return items


def get_shipped_grouped_item_listing(db):
    query = text("""
    SELECT
        o.project_id,
        o.project_name, 
        o.project_number, 
        o.project_id, 
        o.shipped_date,
        o.estimated_fulfillment_date,
        COUNT(o.id) AS items_shipped
    FROM
        ordered_items o
    WHERE
        o.active_po_id IS NOT NULL 
    AND
        o.shipping_status = 'DONE'
    GROUP BY
        o.project_id, o.project_name, o.project_number, o.shipped_date, o.estimated_fulfillment_date;
    """)

    params = {}
    result = db.execute(query, params)
    items = result.mappings().all()

    return items


def get_shipped_item_listing(db, project_id, component_type):
    query = text("""
    SELECT
    o.id,
    o.opening_number,
    o.shipment_id,
    o.packing_info,
    o.ordered_metadata,
    o.door_type,
    o.hand,
    o.label_file_path,
    o.shipped_date,
    CASE 
        WHEN o.component_type = 'FRAME' THEN o.frame_mat
        WHEN o.component_type = 'DOOR' THEN o.door_mat
        ELSE NULL
    END AS material
    FROM ordered_items o
    WHERE o.shipping_status = "DONE"
    AND o.project_id = :project_id
    AND o.component_type = :component_type;
    """)

    params = {"component_type": component_type, "project_id": project_id}
    result = db.execute(query, params)
    items = result.mappings().all()

    return items