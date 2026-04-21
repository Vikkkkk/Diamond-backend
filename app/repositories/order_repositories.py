"""
This file contains all order releated used repositories.
"""
from typing import Optional
from loguru import logger
from repositories.update_stats_repositories import calulate_adons, update_area_item_stats, update_section_stats, update_take_off_sheet_stats, update_raw_material_stats
from models.ordered_items import OrderedItems
from models.active_po import ActivePo
import uuid
from sqlalchemy import or_, and_, update, func, text, case, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from schemas.ordered_item_schema import OrderInsert
from sqlalchemy.exc import SQLAlchemyError
from models.schedules import Schedules


def get_unrequested_items(db, project_id, component_type = "DOOR"):
    query = text("""
        SELECT 
            s.id AS schedule_id, 
            s.opening_number, 
            s.location_1, 
            s.from_to, 
            s.location_2, 
            s.door_qty, 
            s.frame_qty, 
            s.door_material_code, 
            s.frame_material_code, 
            s.door_type, 
            s.swing, 
            s.is_in_change_order, 
            s.is_freezed, 
            JSON_ARRAYAGG(
                JSON_OBJECT(
                    'id', sd.id,
                    'name', sd.name,
                    'value', sd.value,
                    'component', sd.component,
                    'part_number', sd.part_number
                )
            ) AS schedule_details
        FROM schedules s 
        JOIN schedule_data sd 
            ON s.id = sd.schedule_id 
            AND sd.component = :component_type
            AND sd.is_adon_field = false
            AND sd.has_ordered = false
        LEFT JOIN ordered_items o 
            ON s.id = o.schedule_id
            AND o.component_type = :component_type
        WHERE s.project_id = :project_id
        AND (
            o.schedule_id IS NULL
            OR 
            sd.has_ordered = FALSE
        )
        GROUP BY s.id;
    """)
    
    result = db.execute(query, {"project_id": project_id, "component_type": component_type})
    schedules = result.mappings().all()
    return schedules


def get_unrequested_hwd_items(db, project_id):
    query = text("""
        SELECT 
        s.id AS schedule_id, 
        s.opening_number, 
        s.location_1, 
        s.from_to, 
        s.location_2, 
        s.door_qty, 
        s.frame_qty, 
        s.door_material_code, 
        s.frame_material_code, 
        s.door_type, 
        s.swing,
        s.is_in_change_order, 
        s.is_freezed, 
        JSON_ARRAYAGG(
            JSON_OBJECT(
                'id', ohm.id,
                'short_code', ohm.short_code,
                'product_code', ohm.desc,
                'quantity', sohm.quantity,
                'manufacture_id', m.id
            )
        ) AS hardware_details
        FROM schedules s 
        join schedule_opening_hardware_materials sohm 
            on sohm.schedule_id = s.id
        join opening_hardware_materials ohm 
            on ohm.id=sohm.opening_hardware_material_id
        LEFT JOIN ordered_items o 
            ON s.id = o.schedule_id
            AND o.component_type = "HARDWARE"
        JOIN manufacturers m
            ON m.id = ohm.manufacturer_id
        where s.project_id = :project_id
        AND (
            o.schedule_id IS NULL
            OR 
            sohm.has_ordered = FALSE
        ) GROUP BY s.id;
    """)

    result = db.execute(query, {"project_id": project_id})
    schedules = result.mappings().all()
    return schedules


def insert_orders(db: Session, orders: list):
    """
    Inserts a list of orders into the database.

    :param db: SQLAlchemy Session instance
    :param orders: List of order dictionaries
    """
    try:
        # print("order_objects>>>>>", orders)
        order_objects = [
            OrderedItems(**OrderInsert(**order).model_dump()) for order in orders
        ]

        db.add_all(order_objects)  # Add all orders to the session
        db.commit()  # Commit the transaction
        return {"message": "Orders inserted successfully", "count": len(orders)}
    except Exception as e:
        db.rollback()  # Rollback in case of error
        return {"error": str(e)}


def update_schedules_requested(
    db: Session,
    schedule_ids: list,
    component_type: str,
    project_id: Optional[str] = None,
) -> int:
    """
    Mark requested component type on `schedules`.

    We only set the requested flag to True (we do not reset other flags),
    so requesting multiple component types for the same schedule works.
    """
    if component_type not in ["DOOR", "FRAME", "HARDWARE"]:
        raise HTTPException(status_code=400, detail="Invalid component type.")

    values = {}
    if component_type == "DOOR":
        values["has_door_requested"] = True
    elif component_type == "FRAME":
        values["has_frame_requested"] = True
    elif component_type == "HARDWARE":
        values["has_hw_requested"] = True

    stmt = (
        Schedules.__table__.update()
        .where(Schedules.id.in_(schedule_ids))
        .values(**values)
    )
    if project_id:
        stmt = stmt.where(Schedules.project_id == project_id)

    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
    

def prepare_data_for_order(db, project_id, schedule_ids, component_type):
    # print("schedule_ids", schedule_ids)
    # print("project_id", project_id)
    query = text("""
        SELECT 
			p.id AS project_id,
            p.project_code,
            p.name AS project_name,
            s.id AS schedule_id, 
            s.opening_number, 
            s.location_1, 
            s.from_to, 
            s.location_2, 
            s.door_qty, 
            s.frame_qty, 
            s.door_material_code, 
            s.frame_material_code, 
            s.door_type, 
            JSON_ARRAYAGG(
                JSON_OBJECT(
                    'id', sd.id,
                    'name', sd.name,
                    'value', sd.value,
                    'component', sd.component,
                    'amount', sd.final_extended_sell_amount,
                    'part_number', sd.part_number,
                    'is_adon_field', sd.is_adon_field,
                    'feature_data', sd.feature_data
                )
            ) AS schedule_details,
            s.swing
        FROM schedules s 
        JOIN schedule_data sd 
            ON s.id = sd.schedule_id 
            AND sd.component = :component_type
		JOIN projects p 
			ON p.id = s.project_id
        WHERE s.project_id = :project_id AND s.id IN :schedule_ids
        GROUP BY s.id, sd.part_number;
    """)
    print(query)
    result = db.execute(query, {"project_id": project_id, "schedule_ids": schedule_ids, "component_type": component_type})
    schedules = result.mappings().all()
    return schedules


def prepare_hwd_data_for_order(db, project_id, schedule_ids):
    query = text("""
            SELECT 
                s.id AS schedule_id, 
                s.opening_number, 
                s.location_1, 
                s.from_to, 
                s.location_2, 
                s.door_qty, 
                s.frame_qty, 
                s.door_material_code, 
                s.frame_material_code, 
                s.door_type, 
                s.swing,
                p.id as project_id,
                p.name as project_name,
                p.project_code,
                ohm.manufacturer_id,
                ohm.brand_id,
                sohm.total_amount,
                sohm.total_base_amount,
                sohm.quantity,
                sohm.final_amount,
                sohm.final_base_amount,
                ohm.desc,
                ohm.short_code
        FROM schedules s
        join schedule_opening_hardware_materials sohm 
            on sohm.schedule_id = s.id
        join opening_hardware_materials ohm 
            on ohm.id=sohm.opening_hardware_material_id
        JOIN projects p 
			ON p.id = s.project_id
        where s.project_id = :project_id AND s.id IN :schedule_ids;
    """)

    result = db.execute(query, {"project_id": project_id, "schedule_ids": schedule_ids})
    schedules = result.mappings().all()
    return schedules


def get_requested_grouped_items(db, component_type: str, project_id: int = None):
    # Validate component_type to prevent SQL injection
    if component_type not in ["DOOR", "FRAME", "HARDWARE"]:
        raise ValueError("Invalid component_type")

    # Dynamically handle material field
    material_field = None
    if component_type == "DOOR":
        material_field = "o.door_mat"
        material_alias = "door_mat"
    elif component_type == "FRAME":
        material_field = "o.frame_mat"
        material_alias = "frame_mat"

    query = f"""
    SELECT 
        CONCAT(o.required_by_date,'-',o.manufacturer_id) as group_id,
        o.manufacturer_id,
        o.manufacturer_name,
        COUNT(DISTINCT o.project_id) AS project_count,
        COUNT(o.quantity) AS quantity,
        SUM(o.final_price) AS sum_final_price,
        JSON_ARRAYAGG(
            JSON_OBJECT(
                'id', o.id,
                'manufacturer_id', o.manufacturer_id,
                'manufacturer_name', o.manufacturer_name,
                'brand_id', o.brand_id,
                'brand_name', o.brand_name,
                'project_id', o.project_id,
                'project_name', o.project_name,
                'project_number', o.project_number,
                'schedule_id', o.schedule_id,
                'opening_number', o.opening_number,
                'door_type', o.door_type,
                'hand', o.hand,
                {f"'{material_alias}', {material_field}," if material_field else ""}
                'quantity', o.quantity,
                'final_price', o.final_price,
                'required_by_date', o.required_by_date,
                'ordered_metadata', o.ordered_metadata
            )
        ) AS order_items,
    o.required_by_date
    FROM ordered_items o 
    WHERE o.component_type = :component_type
    AND o.active_po_id IS NULL
    { "AND o.project_id = :project_id" if project_id else "" }
    GROUP BY o.manufacturer_id, o.manufacturer_name, o.required_by_date;
    """

    params = {"component_type": component_type}
    if project_id:
        params["project_id"] = project_id

    # print(">>>>>>", query)

    result = db.execute(text(query), params)
    return result.fetchall()



def get_requested_items(db, component_type: str, project_id: int = None):
    # Validate component_type to prevent SQL injection
    if component_type not in ["DOOR", "FRAME", "HARDWARE"]:
        raise ValueError("Invalid component_type")

    query = f"""
        SELECT 
        s.id as schedule_id, 
        s.opening_number,
        s.location_1,
        s.from_to,
        s.location_2,
        s.door_type,
        s.swing,
        s.door_material_code,
        s.frame_material_code,
        o.required_by_date,
        o.manufacturer_id,
        CONCAT('[', 
        GROUP_CONCAT(
            CASE 
                WHEN o.component_type = 'FRAME' THEN 
                    JSON_OBJECT(
                        'jamb_depth', o.ordered_metadata->>'$.jamb_depth',
                        'width', o.ordered_metadata->>'$.width',
                        'height', o.ordered_metadata->>'$.height',
                        'part_number', o.part_number
                    ) 
                WHEN o.component_type = 'DOOR' THEN 
                    JSON_OBJECT(
                        'gauge', o.ordered_metadata->>'$.gauge',
                        'width', o.ordered_metadata->>'$.width',
                        'height', o.ordered_metadata->>'$.height'
                    ) 
                WHEN o.component_type = 'HARDWARE' THEN 
                    JSON_OBJECT(
                        'short_code', o.ordered_metadata->>'$.short_code',
                        'product_code', o.ordered_metadata->>'$.code'
                    ) 
            END
            ORDER BY o.part_number
            SEPARATOR ','
        ), 
    ']') AS order_items,
    SUM(o.quantity) as quantity,
    SUM(o.final_base_price) as final_price
    FROM ordered_items o
    JOIN schedules s ON s.id = o.schedule_id
    WHERE o.component_type = :component_type
    AND active_po_id IS NULL
    AND s.project_id = :project_id
    GROUP BY s.id, o.required_by_date, o.manufacturer_id;
    """

    params = {"component_type": component_type, "project_id": project_id}

    result = db.execute(text(query), params)
    return result.fetchall()


def get_active_purchase_orders(db: Session, component_type: str, project_id: str = None):

    if component_type not in ["DOOR", "FRAME", "HARDWARE"]:
        raise ValueError("Invalid component_type")
    
    query = text("""
    SELECT 
        o.active_po_id,
        o.required_by_date,
        o.estimated_delivery_date,
        ap.po_number,
        ap.ordered_date,
        o.door_mat,
        o.frame_mat,
        o.manufacturer_name,
        o.project_number,
        o.project_name,
        ap.ordered_item_quantity,
        ap.final_price
    FROM 
        (
        SELECT
            o1.active_po_id as active_po_id,
            MAX(o1.required_by_date) as required_by_date,
            MAX(o1.estimated_delivery_date) as estimated_delivery_date,
            MAX(o1.component_type) as component_type,
            MAX(o1.is_received) as is_received,
            MAX(o1.is_damaged) as is_damaged,
            MAX(o1.is_missing) as is_missing,
            GROUP_CONCAT(DISTINCT o1.door_mat) as door_mat,
            GROUP_CONCAT(DISTINCT o1.frame_mat) as frame_mat,
            GROUP_CONCAT(DISTINCT o1.manufacturer_name) as manufacturer_name,
            GROUP_CONCAT(DISTINCT o1.project_number) as project_number,
            GROUP_CONCAT(DISTINCT o1.project_id) as project_id,
            GROUP_CONCAT(DISTINCT o1.project_name) as project_name
        FROM
            ordered_items o1
        GROUP BY
            o1.active_po_id
        ) o 
    JOIN 
        active_po ap ON o.active_po_id = ap.id
    WHERE 
        o.component_type = :component_type
    AND 
        (
            o.is_received = false
            OR
            (
                o.is_received = true
                AND o.is_damaged = true
            )
            OR o.is_missing = true     
        )
    """ + (f""" AND FIND_IN_SET(:project_id, o.project_id) > 0""" if project_id else "") + """ 
    GROUP BY 
        o.active_po_id;
    """)

    params = {"component_type": component_type}
    if project_id:
        params["project_id"] = project_id

    result = db.execute(query, params)
    orders = result.mappings().all()
    return orders


def get_active_purchase_order_items(db: Session, active_po_id: str):

    query = text("""
    SELECT o.*, ap.po_number
    FROM active_po ap
    JOIN ordered_items o 
        ON o.active_po_id = ap.id
    WHERE o.active_po_id= :active_po_id;
    """)

    params = {"active_po_id": active_po_id}

    result = db.execute(query, params)
    order_items = result.mappings().all()
    return order_items


def validate_schedule_ids(db: Session, schedule_ids: list, component_type: str, project_id: str):
    """Check if all schedule_ids exist for the given component_type"""
    existing_schedules = db.scalars(
        select(OrderedItems.schedule_id)
        .where(OrderedItems.schedule_id.in_(schedule_ids), OrderedItems.component_type == component_type, OrderedItems.project_id == project_id)
    ).all()

    return set(existing_schedules) == set(schedule_ids)


def update_order_dates(db: Session, required_by_date, schedule_ids, component_type, project_id):
    """Update order dates for the given schedule_ids and component_type"""
    try:
        result = db.execute(
            OrderedItems.__table__.update()
            .where(
                OrderedItems.schedule_id.in_(schedule_ids),
                OrderedItems.component_type == component_type,
                OrderedItems.project_id == project_id
            )
            .values(required_by_date=required_by_date)
        )
        db.commit()
        return result.rowcount
    except SQLAlchemyError:
        db.rollback()
        return None



def is_active_po_fully_received(db: Session, active_po_id: str) -> bool:
    """
    Checks if all ordered items associated with a given Active PO are received.

    Args:
        db (Session): Database session.
        active_po_id (str): The ID of the Active PO.

    Returns:
        bool: True if all ordered items are received, False otherwise.
    """
    try:
        # Query all ordered items for the given active_po_id
        result = db.execute(
            select(OrderedItems.is_received)
            .where(OrderedItems.active_po_id == active_po_id)
        ).scalars().all()
        
        # for i in result:
        #     print(">>>>>>>", i)

        # If no ordered items exist, return False
        if not result:
            return False

        # Return True only if all ordered items have is_received=True
        return all(result)

    except Exception as error:
        print(f"Error checking PO received status: {error}")
        return False


def get_purchase_order_history_data(db: Session):

    query = text("""
    SELECT 
        o.active_po_id,
        MAX(o.required_by_date) as required_by_date, 
        MAX(o.estimated_delivery_date) as estimated_delivery_date, 
        ap.po_number,
        ap.ordered_date,
        GROUP_CONCAT(DISTINCT o.door_mat) as door_mat,
        GROUP_CONCAT(DISTINCT o.frame_mat) as frame_mat,
        GROUP_CONCAT(DISTINCT o.manufacturer_name) as manufacturer_name, 
        GROUP_CONCAT(DISTINCT o.project_number) as project_number, 
        GROUP_CONCAT(DISTINCT o.project_name) as project_name, 
        ap.ordered_item_quantity,
        ap.final_price
    FROM 
        ordered_items o 
    JOIN 
        active_po ap ON o.active_po_id = ap.id
    WHERE 
        ap.is_received = true
    GROUP BY 
        o.active_po_id;
    """)

    params = {}

    result = db.execute(query, params)
    orders = result.mappings().all()
    return orders

def check_for_po_edit_grant(db, order_ids):
    query = text("""
    SELECT 
    o.id
    FROM 
        ordered_items o 
    LEFT JOIN 
        (
            SELECT od.order_item_id, COUNT(*) AS image_count
            FROM ordered_item_docs od
            GROUP BY od.order_item_id
        ) x 
        ON x.order_item_id = o.id
    WHERE 
        o.is_received = true
        OR o.is_damaged = true
        OR o.is_missing = true     
        OR COALESCE(x.image_count, 0) > 0; 
    """)

    params = {}

    result = db.execute(query, params)
    orders = result.mappings().all()
    return True if len(orders) > 0 else False