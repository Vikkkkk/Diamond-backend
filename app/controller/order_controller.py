"""
This module contains all logical operations and db operations related to projects.
"""
from typing import List, Optional, Dict, Any
from utils.common import get_utc_time, generate_uuid, get_random_hex_code, generate_uuid
from loguru import logger
from models.projects import Projects
from models.project_status_logs import ProjectStatusLogs
from models.status import Status
from models.roles import Roles
from models.clients import Clients
from models.client_projects import ClientProjects
from models.members import Members
from models.member_role import MemberRole
from models.project_members import ProjectMembers
from utils.common import generate_uuid, delete_file, save_uploaded_file, format_project_code
from models.tender_documents import TenderDocuments
from models.quotation_revision import QuotationRevision
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, text, and_, not_, asc, desc
import math
from utils.common import get_user_time, get_estimated_delivery_date, get_aws_full_path, delete_from_s3, get_order_by_date
import os
from sqlalchemy.orm import Session, joinedload
from fastapi import UploadFile
from schemas.project_schemas import ProjectListResponse, ProjectAssignResponse, MembersResponse, ProjectList
from models.ordered_items import OrderedItems
from models.ordered_item_docs import OrderedItemDocs
from models.active_po import ActivePo
from fastapi import HTTPException, status
from datetime import datetime, date
import datetime as dt
import json
import time
from utils.common import upload_to_s3, delete_from_s3, download_from_s3, get_max_date
from utils.order import generate_po_number
from models.ordered_items import OrderedItems, SHIPPING_STATUS
import json
from sqlalchemy.future import select
import re
from collections import defaultdict
from utils.order import get_part_waise_door_filtered_data, get_door_filtered_data, get_frame_filtered_data, split_by_schedule_and_catalog, extract_price_data
from repositories.order_repositories import get_unrequested_items, get_unrequested_hwd_items, insert_orders, prepare_data_for_order, prepare_hwd_data_for_order, \
    get_requested_grouped_items, get_requested_items, get_active_purchase_orders, validate_schedule_ids, update_order_dates, update_schedules_requested, get_active_purchase_order_items, \
    is_active_po_fully_received, get_purchase_order_history_data, check_for_po_edit_grant
from repositories.catelog_repositories import get_catalog_details, get_manufacturer_name, get_brand_name
from repositories.active_po_repositories import check_order_ids_exist, get_order_totals, create_purchase_order, update_order_items, get_purchese_orders, \
    update_purchase_order, get_received_item_listing, requested_shipping_grouped_items, get_shipped_grouped_item_listing, get_shipped_item_listing, \
    shipping_grouped_items,update_has_order,update_has_shipped
from repositories.manufacturer_repositories import get_manufacture_by_id
from setuptools._distutils.util import strtobool

load_dotenv()


async def get_unrequested_frame(
        db: Session, 
        project_id: str
    ) -> Dict[str, Any]:
    try:
        schedules = get_unrequested_items(db, project_id, component_type="FRAME")
        if not schedules:
            return {
            "status": "success",
            "message": "Unrequested frames retrieved successfully.",
            "data": [],
            "total_records": 0
        }

        schedule_items = []
        for schedule in schedules:
            try:
                schedule_details = json.loads(schedule.schedule_details)  # Convert JSON string to list
            except json.JSONDecodeError:
                schedule_details = [] 

            data = {
                'id': schedule.schedule_id,
                'schedule_id': schedule.schedule_id,
                'opening_number': schedule.opening_number,
                'location_1': schedule.location_1,
                'from_to': schedule.from_to,
                'location_2': schedule.location_2,
                'quantity': schedule.frame_qty,
                'door_material_code': schedule.door_material_code,
                'frame_material_code': schedule.frame_material_code,
                'door_type': schedule.door_type,
                'swing': schedule.swing,
                'is_freezed': bool(schedule.is_freezed),
                'is_in_change_order': bool(schedule.is_in_change_order)
            }
            
            schedule_details = get_frame_filtered_data(schedule_details)
            print("schedule_details", schedule_details)
            data['height'] = schedule_details.get('height', None)
            data['width'] = schedule_details.get('width', None)
            data['jamb_depth'] = schedule_details.get('jamb_depth', None)

            catelog = schedule_details.get('frame_catalog', None)
            
            if catelog:
                catalog_details = get_catalog_details(db, catelog)
                manufacturer_id = catalog_details.get('manufacturer_id', None)
                manufacture_info = get_manufacture_by_id(db, manufacturer_id)

                estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)
                data['estimated_delivery_date'] = estimated_delivery_date

            schedule_items.append(data)

        return {
            "status": "success",
            "message": "Unrequested frames retrieved successfully.",
            "data": schedule_items,
            "total_records": len(schedule_items)
        }
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


async def get_unrequested_door(
        db: Session, 
        project_id: str
    ) -> Dict[str, Any]:
    try:
        schedules = get_unrequested_items(db, project_id, component_type="DOOR")
        if not schedules:
            return {
            "status": "success",
            "message": "Unrequested doors retrieved successfully.",
            "data": [],
            "total_records": 0
        }

        schedule_items = []
        for schedule in schedules:
            try:
                schedule_details = json.loads(schedule.schedule_details)  # Convert JSON string to list
            except json.JSONDecodeError:
                schedule_details = [] 

            data = {
                'schedule_id': schedule.schedule_id,
                'opening_number': schedule.opening_number,
                'location_1': schedule.location_1,
                'from_to': schedule.from_to,
                'location_2': schedule.location_2,
                'quantity': schedule.door_qty,
                'door_material_code': schedule.door_material_code,
                'frame_material_code': schedule.frame_material_code,
                'door_type': schedule.door_type,
                'swing': schedule.swing,
                'is_freezed': bool(schedule.is_freezed),
                'is_in_change_order': bool(schedule.is_in_change_order)
            }

            schedule_details = get_part_waise_door_filtered_data(schedule_details)
            data['schedule_data'] = schedule_details
            # print("schedule_details>>>>", schedule_details)
            values_list = list(schedule_details.values())
            # print("values_list", values_list)
            catalog_list = set([value['door_catalog'] for value in values_list])
            catelog = values_list[0].get('door_catalog', None)
            if catalog_list:
                delivery_date_lst = []
                for catelog in catalog_list:
                    catalog_details = get_catalog_details(db, catelog)
                    manufacturer_id = catalog_details.get('manufacturer_id', None)
                    manufacture_info = get_manufacture_by_id(db, manufacturer_id)

                    estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)
                    delivery_date_lst.append(estimated_delivery_date)
                # Convert strings to datetime objects and find the max date
                max_date = get_max_date(delivery_date_lst)
                
                data['estimated_delivery_date'] = max_date
            
            schedule_items.append(data)
        
        schedule_items = split_by_schedule_and_catalog(schedule_items)
        
        return {
            "status": "success",
            "message": "Unrequested doors retrieved successfully.",
            "data": schedule_items,
            "total_records": len(schedule_items)
        }
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")



async def get_unrequested_hardware(
        db: Session, 
        project_id: str
    ) -> Dict[str, Any]:
    try:
        schedules = get_unrequested_hwd_items(db, project_id)
        if not schedules:
            return {
            "status": "success",
            "message": "Unrequested hardware retrieved successfully.",
            "data": [],
            "total_records": 0
        }

        schedule_items = []
        for schedule in schedules:
            try:
                hardware_details = json.loads(schedule.hardware_details)  # Convert JSON string to list
            except json.JSONDecodeError:
                hardware_details = [] 
            
            total_quantity = sum(item['quantity'] for item in hardware_details)
            
            data = {
                'schedule_id': schedule.schedule_id,
                'opening_number': schedule.opening_number,
                'location_1': schedule.location_1,
                'from_to': schedule.from_to,
                'location_2': schedule.location_2,
                'door_material_code': schedule.door_material_code,
                'frame_material_code': schedule.frame_material_code,
                'door_type': schedule.door_type,
                'swing': schedule.swing,
                'quantity': total_quantity,
                'is_freezed': bool(schedule.is_freezed),
                'is_in_change_order': bool(schedule.is_in_change_order)
            }
            delivery_dates = []
            hardware_data = []
            for hardware in hardware_details:
                manufacturer_id = hardware['manufacture_id']
                manufacture_info = get_manufacture_by_id(db, manufacturer_id)

                delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)
                delivery_dates.append(delivery_date)
                hardware_configuration = {
                    "id": hardware['id'],
                    "quantity": hardware['quantity'],
                    "short_code": hardware['short_code'],
                    "product_code": hardware['product_code']
                }

                hardware_data.append(hardware_configuration)
            data['estimated_delivery_date'] = get_max_date(delivery_dates)
            data["hardware_details"] = hardware_data

            schedule_items.append(data)
        
        return {
            "status": "success",
            "message": "Unrequested hardware retrieved successfully.",
            "data": schedule_items,
            "total_records": len(schedule_items)
        }
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")



async def request_order(
        db: Session, 
        project_id: str, 
        data
    ) -> Dict[str, Any]:
    try:
        required_by_date = data.required_by_date
        component_type = data.component_type
        schedule_ids = data.schedule_ids

        if component_type not in ["DOOR", "FRAME", "HARDWARE"]:
            raise HTTPException(status_code=400, detail="Invalid component type.")



        if component_type in ["DOOR", "FRAME"]:
            response = await prepare_door_frame_data(db, project_id, required_by_date, component_type, schedule_ids)
        elif component_type == "HARDWARE":
            response = await prepare_hardware_data(db, project_id, required_by_date, component_type, schedule_ids)

        # Insert into database
        insert_orders(db, response)

        # Update requested flags on `schedules`
        update_schedules_requested(db, schedule_ids, component_type, project_id)


        return {
            "status": "success",
            "message": "Orders inserted successfully.",
            "count": len(response)
        }
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")



async def update_request_order(
        db: Session, 
        project_id: str, 
        data
    ) -> Dict[str, Any]:
    try:

        if data.component_type not in ["DOOR", "FRAME", "HARDWARE"]:
            raise HTTPException(status_code=400, detail="Invalid component type.")

        # Step 1: Validate schedule_ids
        if not validate_schedule_ids(db, data.schedule_ids, data.component_type,  project_id):
            raise HTTPException(status_code=400, detail="Some schedule IDs are invalid or do not match the component type.")

        # Step 2: Update order dates
        updated_count = update_order_dates(db, data.required_by_date, data.schedule_ids, data.component_type, project_id)

        if updated_count is None:
            raise HTTPException(status_code=500, detail="Database update failed")

        # Step 3: Return response
        return {
            "status": "success",
            "message": "Order dates updated successfully",
            "updated_count": updated_count
        }
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


async def prepare_hardware_data(
    db: Session, 
    project_id: str, 
    required_by_date: str, 
    component_type: str, 
    schedule_ids: List[str]
) -> Dict[str, Any]:
    try:
        schedules = prepare_hwd_data_for_order(db, project_id, schedule_ids)
        if not schedules:
            return []

        response = []
        for schedule in schedules:
            manufacture_info = get_manufacture_by_id(db, schedule.manufacturer_id)
            estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)

            data = {
                'project_id': schedule.project_id,
                'project_name': schedule.project_name,
                'project_number': schedule.project_code,
                'schedule_id': schedule.schedule_id,
                'opening_number': schedule.opening_number,
                'door_type': schedule.door_type,
                'hand': schedule.swing,
                'door_mat': schedule.door_material_code,
                'frame_mat': schedule.frame_material_code,
                'component_type': component_type,
                'required_by_date': required_by_date,
                'estimated_delivery_date': estimated_delivery_date,
                'manufacturer_id': schedule.manufacturer_id,
                'manufacturer_name': await get_manufacturer_name(db, schedule.manufacturer_id),
                'brand_id': schedule.brand_id,
                'brand_name': await get_brand_name(db, schedule.brand_id),
                'total_price': schedule.total_amount,
                'total_base_price': schedule.total_base_amount,
                'quantity': schedule.quantity,
                'final_price': schedule.final_amount,
                'final_base_price': schedule.final_base_amount,
                'ordered_metadata': {"code": schedule.desc, "short_code": schedule.short_code},
                'shipping_status': "PENDING"
            }
            response.append(data)

        return response
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


async def prepare_door_frame_data(
    db, 
    project_id, 
    required_by_date, 
    component_type, 
    schedule_ids
    ):
    
    schedules = prepare_data_for_order(db, project_id, schedule_ids, component_type)
    if not schedules:
        return []

    response = []
    for schedule in schedules:
        data = {
            'project_id': schedule.project_id,
            'project_name': schedule.project_name,
            'project_number': schedule.project_code,
            'schedule_id': schedule.schedule_id,
            'opening_number': schedule.opening_number,
            'door_type': schedule.door_type,
            'hand': schedule.swing,
            'door_mat': schedule.door_material_code,
            'frame_mat': schedule.frame_material_code,
            'component_type': component_type,
            'required_by_date': required_by_date,
            'shipping_status': "PENDING"
        }

        try:
            schedule_details = json.loads(schedule.schedule_details)  # Convert JSON string to list
        except json.JSONDecodeError:
            schedule_details = [] 

        price_data = extract_price_data(schedule_details)
        base_price = price_data.get("base_price", 0) 
        adon_price = price_data.get("adon_price", 0) 
        base_with_adon_price = base_price + adon_price
        
        total_price = base_with_adon_price
        total_base_price = base_with_adon_price
        quantity = schedule.door_qty
        final_base_price = total_base_price * quantity
        final_price = total_price * quantity

        data.update({
            'total_base_price': total_base_price,
            'total_price': total_price,
            'quantity': quantity,
            'final_price': final_price,
            'final_base_price': final_base_price
        })
        
        output = {item["name"]: item["value"] for item in schedule_details}

        if component_type == "DOOR":
            door_catalog = output.get('door_catalog')
            catalog_details = get_catalog_details(db, door_catalog)
            ordered_metadata = get_door_filtered_data(schedule_details)
            data['part_number'] = schedule_details[0].get('part_number') if schedule_details else None
        elif component_type == "FRAME":
            frame_catalog = output.get('frame_catalog')
            catalog_details = get_catalog_details(db, frame_catalog)
            ordered_metadata = get_frame_filtered_data(schedule_details)
        
        data['ordered_metadata'] = ordered_metadata
        manufacturer_id = catalog_details.get('manufacturer_id', None)

        # manufacture_info = get_manufacture_by_id(db, manufacturer_id)
        # estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)
        # data['estimated_delivery_date'] = estimated_delivery_date

        data['manufacturer_id'] = manufacturer_id
        data['manufacturer_name'] = catalog_details.get('manufacturer_name', None)
        
        if 'brand_id' in catalog_details:
            data['brand_id'] = catalog_details.get('brand_id', None)
            data['brand_name'] = catalog_details.get('brand_name', None)
        
        response.append(data)
    
    return response



async def get_door_requested_grouped_orders(db: Session, project_id: str = None) -> Dict[str, Any]:
    try:
        component_type = "DOOR"
        orders = get_requested_grouped_items(db, component_type, project_id)
        if not orders:
            return {
            "status": "success",
            "message": "Door requested grouped orders fetched successfully.",
            "data": [],
            "total_records": 0
        }

        response = []
        for order in orders:
            # manufacture_info = get_manufacture_by_id(db, order.manufacturer_id)
            # estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)

            data = {
                'group_id': order.group_id,
                'project_count': order.project_count,
                'quantity': order.quantity,
                'manufacturer_name': order.manufacturer_name,
                'required_by_date': order.required_by_date,
                'sum_final_price': round(order.sum_final_price,2)
            }

            # if component_type == "DOOR":
            #     data['material_type'] = order.door_mat
            # elif component_type == "FRAME":
            #     data['material_type'] = order.frame_mat

            try:
                ordered_items = json.loads(order.order_items)  # Convert JSON string to list
            except json.JSONDecodeError:
                ordered_items = [] 

            items = []
            for ordered_item in ordered_items:

                manufacture_info = get_manufacture_by_id(db, ordered_item['manufacturer_id'])

                item_data = {
                    'id': ordered_item['id'],
                    'manufacturer_id': ordered_item['manufacturer_id'],
                    'manufacturer_name': ordered_item['manufacturer_name'],
                    'brand_id': ordered_item['brand_id'],
                    'brand_name': ordered_item['brand_name'],
                    'project_id': ordered_item['project_id'],
                    'project_name': ordered_item['project_name'],
                    'project_number': ordered_item['project_number'],
                    'schedule_id': ordered_item['schedule_id'],
                    'opening_number': ordered_item['opening_number'],
                    'door_type': ordered_item['door_type'],
                    'hand': ordered_item['hand'],
                    'quantity': ordered_item['quantity'],
                    'final_price': round(ordered_item['final_price'],2),
                    'required_by_date': ordered_item['required_by_date'],
                    # 'estimated_delivery_date': estimated_delivery_date,
                    'order_by_date': get_order_by_date(ordered_item['required_by_date'], manufacture_info.expected_delivery_days),
                    'ordered_metadata': ordered_item['ordered_metadata']
                }
                if component_type == "DOOR":
                    item_data['door_mat'] = ordered_item['door_mat']
                elif component_type == "FRAME":
                    item_data['frame_mat'] = ordered_item['frame_mat']

                items.append(item_data)
            
            data['items'] = items
            response.append(data)
        
        return {
            "status": "success",
            "message": "Door requested grouped orders fetched successfully.",
            "data": response,
            "total_records": len(response)
        }
    
    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


async def get_frame_requested_grouped_orders(db: Session, project_id: str = None):
    try:
        component_type = "FRAME"
        orders = get_requested_grouped_items(db, component_type, project_id)
        
        if not orders:
            return {
            "status": "success",
            "message": "Frame requested grouped orders fetched successfully.",
            "data": [],
            "total_records": 0
        }
        
        response = []
        for order in orders:
            # manufacture_info = get_manufacture_by_id(db, order.manufacturer_id)
            # estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)

            data = {
                'group_id': order.group_id,
                'project_count': order.project_count,
                'quantity': order.quantity,
                'manufacturer_name': order.manufacturer_name,
                'required_by_date': order.required_by_date,
                'sum_final_price': round(order.sum_final_price,2),
            }
            
            try:
                ordered_items = json.loads(order.order_items)  # Convert JSON string to list
                if not isinstance(ordered_items, list):
                    raise ValueError("Invalid format for order_items")
            except (json.JSONDecodeError, ValueError) as e:
                ordered_items = []  # Default to empty list if parsing fails
                
            items = []
            for ordered_item in ordered_items:
                try:
                    manufacture_info = get_manufacture_by_id(db, ordered_item['manufacturer_id'])
                    item_data = {
                        'id': ordered_item['id'],
                        'manufacturer_id': ordered_item['manufacturer_id'],
                        'manufacturer_name': ordered_item['manufacturer_name'],
                        'brand_id': ordered_item['brand_id'],
                        'brand_name': ordered_item['brand_name'],
                        'project_id': ordered_item['project_id'],
                        'project_name': ordered_item['project_name'],
                        'project_number': ordered_item['project_number'],
                        'schedule_id': ordered_item['schedule_id'],
                        'opening_number': ordered_item['opening_number'],
                        'door_type': ordered_item['door_type'],
                        'hand': ordered_item['hand'],
                        'frame_mat': ordered_item['frame_mat'],
                        'quantity': ordered_item['quantity'],
                        'final_price': round(ordered_item['final_price'],2),
                        'required_by_date': ordered_item['required_by_date'],
                        # 'estimated_delivery_date': estimated_delivery_date,
                        'ordered_metadata': ordered_item.get('ordered_metadata', {}),
                        'order_by_date': get_order_by_date(ordered_item['required_by_date'], manufacture_info.expected_delivery_days),
                    }
                    items.append(item_data)
                except KeyError as ke:
                    continue  # Skip items with missing keys
            
            data['items'] = items
            response.append(data)
        
        return {
            "status": "success",
            "message": "Frame requested grouped orders fetched successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def get_hwd_requested_grouped_orders(db: Session, project_id: str = None):
    try:
        component_type = "HARDWARE"
        orders = get_requested_grouped_items(db, component_type, project_id)
        
        if not orders:
            return {
            "status": "success",
            "message": "Hardware requested grouped orders fetched successfully.",
            "data": [],
            "total_records": 0
        }
        
        response = []
        for order in orders:
            # manufacture_info = get_manufacture_by_id(db, order.manufacturer_id)
            # estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)

            data = {
                'group_id': order.group_id,
                'project_count': order.project_count,
                'manufacturer_name': order.manufacturer_name,
                # 'order_by_date': order.order_by_date,
                'required_by_date': order.required_by_date,
                'sum_final_price': round(order.sum_final_price,2),
            }
            
            try:
                ordered_items = json.loads(order.order_items)  # Convert JSON string to list
                if not isinstance(ordered_items, list):
                    raise ValueError("Invalid format for order_items")
            except (json.JSONDecodeError, ValueError) as e:
                ordered_items = []  # Default to empty list if parsing fails
                
            items = []
            for ordered_item in ordered_items:
                try:
                    manufacture_info = get_manufacture_by_id(db, ordered_item['manufacturer_id'])
                    item_data = {
                        'id': ordered_item['id'],
                        'manufacturer_id': ordered_item['manufacturer_id'],
                        'manufacturer_name': ordered_item['manufacturer_name'],
                        'brand_id': ordered_item['brand_id'],
                        'brand_name': ordered_item['brand_name'],
                        'project_id': ordered_item['project_id'],
                        'project_name': ordered_item['project_name'],
                        'project_number': ordered_item['project_number'],
                        'schedule_id': ordered_item['schedule_id'],
                        'opening_number': ordered_item['opening_number'],
                        'door_type': ordered_item['door_type'],
                        'hand': ordered_item['hand'],
                        'quantity': ordered_item['quantity'],
                        'final_price': round(ordered_item['final_price'],2),
                        'required_by_date': ordered_item['required_by_date'],
                        # 'estimated_delivery_date': estimated_delivery_date,
                        'ordered_metadata': ordered_item.get('ordered_metadata', {}),
                        'order_by_date': get_order_by_date(ordered_item['required_by_date'], manufacture_info.expected_delivery_days),
                    }
                    items.append(item_data)
                except KeyError as ke:
                    continue  # Skip items with missing keys
            
            data['items'] = items
            response.append(data)
        
        return {
            "status": "success",
            "message": "Hardware requested grouped orders fetched successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# TODO: component_type with orderids checking
async def purchase_order(data, db: Session):
    try:
        data = data.model_dump(exclude_unset=True)

        order_ids = data['order_ids']
        po_info = data['po_info']
        component_type = data['component_type']

        # Remove keys with empty string or None values from po_info dictionary
        po_info = {k: v for k, v in po_info.items() if v not in ("", None)}

        with db.begin():  # Start transaction
            # Step 1: Check if order IDs exist
            valid_order_ids = check_order_ids_exist(db, order_ids)

            # Step 2: Get total quantity and price
            totals = get_order_totals(db, valid_order_ids)

            # Step 3: Generate PO Number and create a new purchase order
            # TODO: Check if PO already exists for these order_ids
            new_po = create_purchase_order(db, po_info, totals['total_quantity'], totals['total_price'])

            # Get all schedule_ids from OrderedItems
            schedule_ids = (
                db.query(OrderedItems.schedule_id)
                .filter(OrderedItems.id.in_(valid_order_ids))
                .distinct()
                .all()
            )
            schedule_ids = [sid[0] for sid in schedule_ids if sid[0]]

            # Update schedules with component_type flag
            update_has_order(db, schedule_ids, component_type)

            # Update ordered items with new PO ID
            update_order_items(db, valid_order_ids, new_po.id)

            return {
                "message": "Purchase order created successfully",
                "po_id": new_po.id,
                "po_number": new_po.po_number
            }

    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return {"error": "Failed to create purchase order"}

    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

    

async def modify_purchase_order(active_po_id, data, db: Session):
    try:
        data = data.model_dump(exclude_unset=True)
        order_ids = data['order_ids']
        po_info = data['po_info']
        # Remove keys with empty string or None values from po_info dictionary
        po_info = {k: v for k, v in po_info.items() if v not in ("", None)}
        with db.begin():  # Start transaction

            # Step 1: Check if active PO item already received/missing/damaged/images added
            edit_grant_status = check_for_po_edit_grant(db, order_ids)
            # print(">>>>>>>>", edit_grant_status)
            if edit_grant_status:
                raise Exception("You can't modify this order as recever already initiate the receiving process for this PO!")

            # Step 2: Check if order IDs exist
            valid_order_ids = check_order_ids_exist(db, order_ids)
            
            # Step 3: Get total quantity and price
            totals = get_order_totals(db, valid_order_ids)
            
            # Step 4 & 5: Generate PO Number and create a new purchase order
            new_po = update_purchase_order(db, active_po_id, po_info, totals['total_quantity'], totals['total_price'])
            
            # Step 6: Update ordered items with new PO ID
            update_order_items(db, valid_order_ids, new_po.id)

            return {
                "message": "Purchase order modified successfully",
                "po_id": new_po.id,
                "po_number": new_po.po_number
            }
            
    except SQLAlchemyError as e:
        print(f"Database error: {e}")  # Log the error
        return {"error": "Failed to create purchase order"}

    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=500)
        # print(str(e))
        # logger.exception(str(e))
        # raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")


async def get_purchase_order_list(
    project_id: str, 
    component_type: str,
    db: Session
) -> Dict[str, Any]:
    try:
        ordered_items = get_purchese_orders(db, project_id, component_type)
        if not ordered_items:
            return {
            "status": "success",
            "message": "Purchase orders retrieved successfully.",
            "data": [],
            "total_records": 0
        }
        
        response = []
        for ordered_item in ordered_items:
            item_data = {
                'schedule_id': ordered_item.get('schedule_id'),
                'opening_number': ordered_item.get('opening_number'),
                'required_by_date': ordered_item.get('required_by_date'),
                'estimated_delivery_date': ordered_item.get('estimated_delivery_date'),
                'door_mat': ordered_item.get('door_mat'),
                'frame_mat': ordered_item.get('frame_mat'),
                'hand': ordered_item.get('hand'),
                'door_type': ordered_item.get('door_type'),
                'po_id': ordered_item.get('po_id'),
                'po_number': ordered_item.get('po_number'),
                'ordered_date': ordered_item.get('ordered_date'),
                'final_price': ordered_item.get('final_price'),
                'ordered_item_quantity': ordered_item.get('ordered_item_quantity'),
                'location_1': ordered_item.get('location_1')
            }
            
            try:
                item_data['ordered_metadata'] = json.loads(ordered_item.get('feature', '[]'))
            except json.JSONDecodeError:
                item_data['ordered_metadata'] = []  # Default to empty list if JSON is invalid
            
            response.append(item_data)
        
        return {
            "status": "success",
            "message": "Purchase orders retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


async def get_requested_orders(db: Session, project_id: str, component_type: str):
    try:
        requested_orders = get_requested_items(db, component_type, project_id)

        if not requested_orders:
            return {
                "status": "success",
                "message": "Requested orders retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for ordered_item in requested_orders:

            manufacture_info = get_manufacture_by_id(db, ordered_item.manufacturer_id)
            estimated_delivery_date = get_estimated_delivery_date(manufacture_info.expected_delivery_days)

            item_data = {
                'schedule_id': ordered_item.schedule_id,
                'opening_number': ordered_item.opening_number,
                'location_1': ordered_item.location_1,
                'from_to': ordered_item.from_to,
                'location_2': ordered_item.location_2,
                'door_type': ordered_item.door_type,
                'hand': ordered_item.swing,
                'door_material_code': ordered_item.door_material_code,
                'frame_material_code': ordered_item.frame_material_code,
                'final_price': ordered_item.final_price,
                'required_by_date': ordered_item.required_by_date,
                'estimated_delivery_date': estimated_delivery_date,
            }
            
            try:
                ordered_items = json.loads(ordered_item.order_items)  # Convert JSON string to list
                if not isinstance(ordered_items, list):
                    raise ValueError("Invalid format for order_items")
            except (json.JSONDecodeError, ValueError) as e:
                ordered_items = []  # Default to empty list if parsing fails
        
            for items in ordered_items: 
                if "part_number" in items and component_type in ["FRAME", "HARDWARE"]:
                    del items['part_number']
                
            item_data['order_items'] = ordered_items
            item_data['quantity'] = ordered_item.quantity
            response.append(item_data)
        
        return {
            "status": "success",
            "message": "Requested orders retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_active_purchase_order_list(
    db: Session,
    component_type: str,
    project_id: str = None, 
):
    try:
        orders = get_active_purchase_orders(db, component_type, project_id)
        
        if not orders:
            return {
                "status": "success",
                "message": "Active purchase orders retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for order in orders:
            item_data = {
                'active_po_id': order.active_po_id,
                'po_number': order.po_number,
                'required_by_date': order.required_by_date,
                'estimated_delivery_date': order.estimated_delivery_date,
                'ordered_date': order.ordered_date,
                'door_mat': order.door_mat,
                'frame_mat': order.frame_mat,
                'manufacturer_name': order.manufacturer_name,
                'project_number': order.project_number,
                'project_name': order.project_name,
                'ordered_item_quantity': order.ordered_item_quantity,
                'final_price': order.final_price
            }
            response.append(item_data)
        
        return {
            "status": "success",
            "message": "Active purchase orders retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def get_active_purchase_order_item_list(db, active_po_id):
    try:
        order_items = get_active_purchase_order_items(db, active_po_id)
        
        if not order_items:
            return {
                "status": "success",
                "message": "Active purchase order items retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for order in order_items:

            try:
                ordered_metadata = json.loads(order.ordered_metadata)  # Convert JSON string to list
                if not isinstance(ordered_metadata, dict):
                    raise ValueError("Invalid format for ordered_metadata")
            except (json.JSONDecodeError, ValueError) as e:
                ordered_metadata = {}  # Default to empty list if parsing fails

            item_data = {
                'id': order.id,
                'po_number': order.po_number,
                'active_po_id': order.active_po_id,
                'quantity': order.quantity,
                'manufacturer_id': order.manufacturer_id,
                'manufacturer_name': order.manufacturer_name,
                'project_name': order.project_name,
                'project_number': order.project_number,
                'opening_number': order.opening_number,
                'door_type': order.door_type,
                'hand': order.hand,
                'door_mat': order.door_mat,
                'frame_mat': order.frame_mat,
                'ordered_metadata': ordered_metadata,
                'final_base_price': order.final_base_price,
                'is_received': order.is_received,
                'is_missing': order.is_missing,
                'is_damaged': order.is_damaged
            }
            response.append(item_data)
        
        return {
            "status": "success",
            "message": "Active purchase order items retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

async def update_po_status(db, payload, active_po_id):
    try:
        # Start transaction
        with db.begin():

            # Convert payload to dictionary & remove null values
            payload_dict = payload.dict(exclude_none=True)  

            order_items = payload_dict.get("order_items", {})

            if not order_items:
                raise HTTPException(status_code=400, detail="No valid order items provided.")

            active_po = db.query(ActivePo).filter(ActivePo.id == active_po_id).first()
            if not active_po:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid active PO IDs: {active_po_id}"
                )

            order_ids = list(order_items.keys())

            # Query database for existing order item IDs
            existing_items = db.query(OrderedItems).filter(OrderedItems.id.in_(order_ids), OrderedItems.active_po_id == active_po_id).all()
            existing_ids = {item.id for item in existing_items}

            # Find missing IDs
            missing_ids = set(order_ids) - existing_ids
            if missing_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid order item IDs: {', '.join(map(str, missing_ids))}"
                )
            
            # Update order items
            notify_items = []
            for item in existing_items:
                status = order_items[item.id]

                is_received = status.get("is_received", None)
                is_missing = status.get("is_missing", None)
                is_damaged = status.get("is_damaged", None)

                if is_received == True:
                    item.is_received = is_received
                    message = "Item received"

                elif is_missing == True:
                    item.is_missing = is_missing
                    message = "Item marked as missing"
                    notify_items.append(("missing", item))

                elif is_missing == False:
                    item.is_missing = is_missing
                    message = "Item unmarked as missing"

                elif is_damaged == True:
                    item.is_damaged = is_damaged
                    message = "Item marked as damaged"
                    notify_items.append(("damaged", item))

                elif is_damaged == False:
                    item.is_damaged = is_damaged
                    message = "Item unmarked as damaged"

                db.flush()
            
            # Debug: print missing/damaged items with full OrderedItems column values
            # print(
            #     "notify_items",
            #     [
            #         (status, {col.key: getattr(item, col.key) for col in item.__table__.columns})
            #         for status, item in notify_items
            #     ],
            # )

            # Send notification email only when items are marked missing/damaged and email notification is enabled
            if notify_items and strtobool(os.environ.get("IS_EMAIL_NOTIFICATION_ENABLED", "0")):
                recipient_emails: List[str] = []

                # 1) Find the project for this active_po_id
                project_id_row = (
                    db.query(OrderedItems.project_id)
                    .filter(OrderedItems.active_po_id == active_po_id)
                    .distinct()
                    .first()
                )
                project_id = project_id_row[0] if project_id_row else None

                # 2) Fetch emails for the project's assigned manager
                #    (using the role "Chief Project Manager" as the assigned project manager)
                if project_id:
                    project_manager_emails = (
                        db.query(Members.email)
                        .select_from(ProjectMembers)
                        .join(
                            MemberRole,
                            ProjectMembers.member_role_id == MemberRole.id,
                        )
                        .join(Roles, MemberRole.role_id == Roles.id)
                        .join(Members, Members.id == MemberRole.member_id)
                        .filter(
                            ProjectMembers.project_id == project_id,
                            ProjectMembers.is_active == True,
                            Roles.name == "Chief Project Manager",
                            MemberRole.active_role == True,
                            Members.email.isnot(None),
                            Members.email != "",
                        )
                        .distinct()
                        .all()
                    )
                    recipient_emails.extend(
                        [row[0] for row in project_manager_emails if row and row[0]]
                    )

                # Deduplicate while preserving order
                recipient_emails = list[str](dict.fromkeys([e for e in recipient_emails if e]))

                print("recipient_emails", recipient_emails)

                if recipient_emails:
                    try:
                        from utils.send_mail_helper import (
                            SMTPMailService,
                            build_missing_damaged_items_table_html,
                        )
 
                        SMTPMailService().send_email(
                            email_addresses=recipient_emails,
                            subject=f"PO Update: Missing/Damaged Items ({active_po.po_number})",
                            template_data={
                                "heading": f"PO Update ({active_po.po_number})",
                                "preview_text": "Missing/Damaged item update",
                                "body_html": build_missing_damaged_items_table_html(notify_items=notify_items),
                                "footer_text": "This is an automated message from Diamond.",
                            },
                        )
                    except Exception as email_error:
                        logger.exception(f"update_po_status:: email send failed: {email_error}")
 
 


            is_po_fully_received = is_active_po_fully_received(db, active_po_id)
            if is_po_fully_received:
                update_data = {'is_received': is_po_fully_received}
                update_purchase_order(db, active_po_id, update_data)

            return {
                "status": "success",
                "message": message
                }

    except HTTPException as e:
        logger.exception(str(e))
        raise e
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    


async def get_active_po(db, po_id: str):
    try:
        # Query the database for the ActivePo record
        po_record = db.query(ActivePo).filter(ActivePo.id == po_id).first()

        # If no record is found, raise a 404 exception
        if not po_record:
            raise HTTPException(status_code=404, detail="Active PO not found")

        # Return the data as a JSON object
        response = {
            "id": po_record.id,
            "po_number": po_record.po_number,
            "company_address": po_record.company_address,
            "sold_to": po_record.sold_to,
            "ship_to": po_record.ship_to,
            "order_contact": po_record.order_contact,
            "required_by_date": po_record.required_by_date,
            "order_contact_email": po_record.order_contact_email,
            "delivery_contact_phone": po_record.delivery_contact_phone,
            # "purchase_order": po_record.purchase_order,
            "ordered_date": po_record.ordered_date,
            "material": po_record.material,
            "quote": po_record.quote,
            "scheduled_ship_date": po_record.scheduled_ship_date,
            "customer": po_record.customer,
            "description": po_record.description,
            "po_acknowledgement": po_record.po_acknowledgement,
            "ship_via": po_record.ship_via,
            "ship_instructions": po_record.ship_instructions,
            "order_type": po_record.order_type,
            "order_type_description": po_record.order_type_description,
            "carrier": po_record.carrier,
            "service_center": po_record.service_center,
            "transfer_point_ship_via": po_record.transfer_point_ship_via,
            "transfer_point_carrier": po_record.transfer_point_carrier,
            "bundling_code": po_record.bundling_code,
            "prepaid_collect_code_id": po_record.prepaid_collect_code_id,
            "is_job_site": po_record.is_job_site,
            "ordered_item_quantity": po_record.ordered_item_quantity,
            "final_price": po_record.final_price
        }
    
        return {
            "status": "success",
            "message": "Active purchase order details retrieved successfully.",
            "data": response,
            "total_records": 1  # Since we are returning only one record
        }

    except HTTPException as e:
        # Handle HTTP-specific exceptions
        logger.exception(f"HTTP Exception occurred: {e.detail}")
        raise e
    except Exception as e:
        # Handle any other exceptions (e.g., database errors, unexpected errors)
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    


async def upload_ordered_item_docs(db, order_item_id, files):
    try:
        with db.begin():
            uploaded_docs = []

            for file in files:
                file_name = file.filename
                ordered_item_doc = OrderedItemDocs(
                    order_item_id=order_item_id,
                    file_name=file_name,
                    content_type=file.content_type
                )

                # Add instance to DB session
                db.add(ordered_item_doc)
                db.flush()

                # Upload file to S3
                upload_path = f"ordered_item_docs/{order_item_id}/{ordered_item_doc.id}"
                file_path = await upload_to_s3(file, upload_path)  # Upload function should return file URL
                ordered_item_doc.file_path = file_path

                uploaded_docs.append({
                    "document_id": ordered_item_doc.id,
                    "file_name": file_name,
                    "file_path": get_aws_full_path(file_path)
                })

        return {
            "message": "Files uploaded successfully",
            "documents": uploaded_docs
        }

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")
    

async def list_ordered_item_docs(db, order_item_id):
    try:
        documents = db.query(OrderedItemDocs).\
            filter(OrderedItemDocs.order_item_id == order_item_id).order_by(OrderedItemDocs.created_at.desc()).all()

        return {
            "status": "success",
            "message": "Documents retrieved successfully",
            "data": [
                {
                    "document_id": doc.id,
                    "file_name": doc.file_name,
                    "file_path": get_aws_full_path(doc.file_path),
                    "content_type": doc.content_type
                }
                for doc in documents
            ],
            "total_records": len(documents)
        }

    except SQLAlchemyError as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")
    

async def delete_ordered_item_doc(db, document_id):
    try:
        # Retrieve the document
        document = db.query(OrderedItemDocs).filter(OrderedItemDocs.id == document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")

        file_path = document.file_path

        # Delete the document
        db.delete(document)
        db.commit()

        # Attempt to delete from S3
        try:
            await delete_from_s3(file_path)
        except Exception as s3_error:
            # Log but don't fail the whole request if S3 deletion fails
            print(f"Warning: Failed to delete from S3: {str(s3_error)}")

        return {
            "status": "success",
            "message": f"Document {document_id} deleted successfully."
        }

    except SQLAlchemyError as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
    

# TODO working on it
async def get_received_items(project_id, component_type, db):

    try:
        items = get_received_item_listing(db, project_id, component_type)
        
        if not items:
            return {
                "status": "success",
                "message": "Received items retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for item in items:
            try:
                ordered_metadata = json.loads(item.ordered_metadata)  # Convert JSON string to list
                if not isinstance(ordered_metadata, dict):
                    raise ValueError("Invalid format for ordered_metadata")
            except (json.JSONDecodeError, ValueError) as e:
                ordered_metadata = {}  # Default to empty list if parsing fails

            item_data = {
                'id': item.id,
                'active_po_id': item.active_po_id,
                'quantity': item.quantity,
                'manufacturer_id': item.manufacturer_id,
                'manufacturer_name': item.manufacturer_name,
                'project_name': item.project_name,
                'project_number': item.project_number,
                'opening_number': item.opening_number,
                'location_1': item.location_1,
                'from_to': item.from_to,
                'location_2': item.location_2,
                'door_type': item.door_type,
                'hand': item.hand,
                'door_mat': item.door_mat,
                'frame_mat': item.frame_mat,
                'ordered_metadata': ordered_metadata,
                'final_base_price': item.final_base_price,
                'is_received': item.is_received,
                'is_missing': item.is_missing,
                'is_damaged': item.is_damaged,
                'shipping_status': item.shipping_status
            }
            response.append(item_data)
        
        return {
            "status": "success",
            "message": "Received items retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    


# async def request_ship_items(project_id, component_type, payload, db: Session):
#     try: 

#         # Step 1: Fetch items based on provided item IDs
#         ordered_items = db.query(OrderedItems).filter(
#             OrderedItems.is_received == True,
#             OrderedItems.project_id == project_id,
#             OrderedItems.component_type == component_type,
#             OrderedItems.id.in_(payload.items)
#         )
#         print(str(ordered_items))
#         ordered_items = ordered_items.all()

#         # Check if all requested items exist
#         fetched_item_ids = {item.id for item in ordered_items}

#         requested_item_ids = set(payload.items)

#         if fetched_item_ids != requested_item_ids:
#             missing_items = requested_item_ids - fetched_item_ids
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Some requested items were not found: {list(missing_items)}"
#             )

#         # Step 2: Update the shipping_status to "IN PROGRESS"
#         for item in ordered_items:
#             item.shipping_status = SHIPPING_STATUS.IN_PROGRESS

#         db.commit()  # Commit the transaction

#         # Step 3: Return a success response
#         return {
#             "message": "Shipping status updated to IN PROGRESS",
#             "updated_items": [item.id for item in ordered_items]
#         }

#     except SQLAlchemyError as e:
#         logger.exception(f"An error occurred: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
#     except Exception as e:
#         logger.exception(str(e))
#         raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def get_requested_shipping_grouped_items(db):
    try:
        group_items = requested_shipping_grouped_items(db)
        
        if not group_items:
            return {
                "status": "success",
                "message": "Requested shipping items retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for group_item in group_items:
            try:
                ship_items = json.loads(group_item.ship_items)  # Convert JSON string to list
                if not isinstance(ship_items, list):
                    raise ValueError("Invalid format for ordered_metadata")
            except (json.JSONDecodeError, ValueError) as e:
                ship_items = {}  # Default to empty list if parsing fails

            grouped_item_data = {
                'project_id': group_item.project_id,
                'project_name': group_item.project_name,
                'project_number': group_item.project_number,
                'items_to_ship': group_item.items_to_ship,
                'date_requested': group_item.shipping_initiate_date
            }
            item_data_lst = []
            for item in ship_items:
                item_data = {
                    'id': item['id'],
                    'opening_number': item['opening_number'],
                    'door_type': item['door_type'],
                    'hand': item['hand'],
                    'ordered_metadata': item['ordered_metadata'],
                    'location_1': item['location_1'],
                    'to_from': item['to_from'],
                    'location_2': item['location_2'],
                    'material': item['material'],
                    'crate_number': item['crate_number'],
                    'label_file_path': get_aws_full_path(item['label_file_path']) if item['label_file_path'] is not None else None
                }
                item_data_lst.append(item_data)
                
            grouped_item_data['items'] = item_data_lst
            
            response.append(grouped_item_data)
            
        return {
            "status": "success",
            "message": "Requested shipping items retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_shipping_grouped_items(db):
    try:
        group_items = shipping_grouped_items(db)
        
        if not group_items:
            return {
                "status": "success",
                "message": "Shipment items retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for group_item in group_items:
            try:
                ship_items = json.loads(group_item.ship_items)  # Convert JSON string to list
                if not isinstance(ship_items, list):
                    raise ValueError("Invalid format for ordered_metadata")
            except (json.JSONDecodeError, ValueError) as e:
                ship_items = {}  # Default to empty list if parsing fails

            grouped_item_data = {
                'project_id': group_item.project_id,
                'project_name': group_item.project_name,
                'project_number': group_item.project_number,
                'items_to_ship': group_item.items_to_ship,
                'shipment_date': group_item.shipment_date
            }
            item_data_lst = []
            for item in ship_items:
                item_data = {
                    'id': item['id'],
                    'opening_number': item['opening_number'],
                    'door_type': item['door_type'],
                    'hand': item['hand'],
                    'ordered_metadata': item['ordered_metadata'],
                    'location_1': item['location_1'],
                    'to_from': item['to_from'],
                    'location_2': item['location_2'],
                    'material': item['material'],
                    'crate_number': item['crate_number'],
                    'label_file_path': get_aws_full_path(item['label_file_path']) if item['label_file_path'] is not None else None
                }
                item_data_lst.append(item_data)
                
            grouped_item_data['items'] = item_data_lst
            
            response.append(grouped_item_data)
            
        return {
            "status": "success",
            "message": "Requested shipping items retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def request_ship_items(project_id, component_type, payload, db: Session):
    try: 
        if payload.shipping_status == "IN_PROGRESS" and payload.estimated_fulfillment_date is None:
            raise Exception("Missing estimated fulfillemnt date in the request payload !")

        # Step 1: Fetch items based on provided item IDs
        ordered_items = db.query(OrderedItems).filter(
            OrderedItems.project_id == project_id,
            OrderedItems.id.in_(payload.items)
        )
        if payload.shipping_status == "PENDING":
            ordered_items.filter(OrderedItems.is_received == True, OrderedItems.component_type == component_type)
            
        if payload.shipping_status == "IN_PROGRESS":
            ordered_items.filter(OrderedItems.shipping_status == "IN_PROGRESS")

        if payload.shipping_status == "AWAIT_SHIPPING":
            ordered_items.filter(OrderedItems.shipping_status == "AWAIT_SHIPPING")
            
        ordered_items = ordered_items.all()

        # Check if all requested items exist
        fetched_item_ids = {item.id for item in ordered_items}

        requested_item_ids = set(payload.items)

        if fetched_item_ids != requested_item_ids:
            missing_items = requested_item_ids - fetched_item_ids
            raise HTTPException(
                status_code=400,
                detail=f"Some requested items were not found: {list(missing_items)}"
            )

        # Calculate generated item count once before the loop
        generated_item_count = (
            db.query(OrderedItems)
            .filter(
                OrderedItems.project_id == project_id,
                OrderedItems.shipping_status == "IN_PROGRESS",
                OrderedItems.shipment_id == None,
            )
            .count()
        )

        # Step 2: Update the shipping_status to "IN PROGRESS"
        for item in ordered_items:
            if payload.shipping_status == "PENDING":
                item.shipping_initiate_date = dt.date.today()
                item.shipping_status = SHIPPING_STATUS.IN_PROGRESS
                message = "Shipping status updated to IN PROGRESS"
                
            if payload.shipping_status == "IN_PROGRESS":
                item.estimated_fulfillment_date = payload.estimated_fulfillment_date
                item.shipment_date = dt.date.today()
                item.shipping_status = SHIPPING_STATUS.AWAIT_SHIPPING
                message = "Shipping status updated to AWAIT SHIPPING"

                # Increment count and generate unique shipping ID
                generated_item_count += 1  # Ensure each item gets a unique number
        
                # Generate Shipping ID
                shipment_id = f"{item.project_number}-{generated_item_count:03}"
                item.shipment_id = shipment_id
                # Generate Packing info
                packing_info = f"C-{item.crate_number}"
                item.packing_info = packing_info

            if payload.shipping_status == "AWAIT_SHIPPING":

                item.shipped_date = dt.date.today()
                item.shipping_status = SHIPPING_STATUS.DONE
                message = "Shipping status updated to DONE"
                schedule_ids = [item.schedule_id] if item.schedule_id else []
                if schedule_ids:
                    update_has_shipped(db, schedule_ids, item.component_type.value)

        db.commit()  # Commit the transaction

        # Step 3: Return a success response
        return {
            "message": message,
            "updated_items": [item.id for item in ordered_items]
        }

    except SQLAlchemyError as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def get_shipped_grouped_items(db):
    try:
        group_items = get_shipped_grouped_item_listing(db)
        
        if not group_items:
            return {
                "status": "success",
                "message": "Shipped groupd items retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for group_item in group_items:

            grouped_item_data = {
                'project_id': group_item.project_id,
                'project_name': group_item.project_name,
                'project_number': group_item.project_number,
                'items_shipped': group_item.items_shipped,
                'shipped_date': group_item.shipped_date,
                'estimated_fulfillment_date': group_item.estimated_fulfillment_date
            }
            
            response.append(grouped_item_data)
            
        return {
            "status": "success",
            "message": "Shipped grouped items retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def get_shipped_items(db, project_id, component_type):
    try:
        items = get_shipped_item_listing(db, project_id, component_type)
        
        if not items:
            return {
                "status": "success",
                "message": "Shipped items retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for item in items:
            try:
                ordered_metadata = json.loads(item.ordered_metadata)  # Convert JSON string to list
                if not isinstance(ordered_metadata, dict):
                    raise ValueError("Invalid format for ordered_metadata")
            except (json.JSONDecodeError, ValueError) as e:
                ordered_metadata = {} 
                
            item_data = {
                'id': item.id,
                'opening_number': item.opening_number,
                'shipment_id': item.shipment_id,
                'packing_info': item.packing_info,
                'ordered_metadata': ordered_metadata,
                'door_type': item.door_type,
                'hand': item.hand,
                'label_file_path': get_aws_full_path(item.label_file_path) if item.label_file_path is not None else None,
                'material': item.material,
                'shipped_date': item.shipped_date
            }
            
            
            response.append(item_data)
            
        return {
            "status": "success",
            "message": "Shipped items retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



async def get_purchase_order_history(
    db: Session, 
):
    try:
        orders = get_purchase_order_history_data(db)
        
        if not orders:
            return {
                "status": "success",
                "message": "Active purchase orders retrieved successfully.",
                "data": [],
                "total_records": 0
            }
        
        response = []
        for order in orders:
            item_data = {
                'active_po_id': order.active_po_id,
                'po_number': order.po_number,
                'required_by_date': order.required_by_date,
                'estimated_delivery_date': order.estimated_delivery_date,
                'ordered_date': order.ordered_date,
                'door_mat': order.door_mat,
                'frame_mat': order.frame_mat,
                'manufacturer_name': order.manufacturer_name,
                'project_number': order.project_number,
                'project_name': order.project_name,
                'ordered_item_quantity': order.ordered_item_quantity,
                'final_price': order.final_price
            }
            response.append(item_data)
        
        return {
            "status": "success",
            "message": "Active purchase orders retrieved successfully.",
            "data": response,
            "total_records": len(response)
        }
    except Exception as e:
        logger.exception(str(e))
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    


async def get_po_information(db, item_ids, component_type):

    item_ids = [item.strip() for item in item_ids.split(",")]

    ordered_items = db.query(OrderedItems).filter(
            OrderedItems.id.in_(item_ids),
            OrderedItems.component_type == component_type
        )
    
    # Check if all requested items exist
    fetched_item_ids = []
    fetched_required_by_dates = []
    for item in ordered_items:
        fetched_item_ids.append(item.id)
        fetched_required_by_dates.append(item.required_by_date)


    fetched_item_ids = set(fetched_item_ids)
    requested_item_ids = set(item_ids)

    if fetched_item_ids != requested_item_ids:
        missing_items = requested_item_ids - fetched_item_ids
        raise HTTPException(
            status_code=400,
            detail=f"Some requested items were not found: {list(missing_items)}"
        )
    
    # Find the earliest date
    earliest_date = min(fetched_required_by_dates)

    # Convert to string (YYYY-MM-DD format)
    required_by_date = earliest_date.strftime("%Y-%m-%d")

    # Get current date
    ordered_date = date.today().strftime("%Y-%m-%d")

    # Prepare material
    if component_type == "DOOR":
        material_type =  ','.join(set([item.door_mat for item in ordered_items]))
    elif component_type == "FRAME":
        material_type =  ','.join(set([item.frame_mat for item in ordered_items]))
    else:
        material_type = "HWD"

    po_number = generate_po_number()
    data = {
        "company_info": {
            "company_address": os.getenv("COMPANY_NAME"),
            "sold_to": os.getenv("COMPANY_NAME"),
            "ship_to": os.getenv("COMPANY_ADDRESS"),
            "po_number": po_number,
            "order_contact_email": os.getenv("COMPANY_EMAIL"),
            "delivery_contact_phone": os.getenv("COMPANY_PHONE"),
            "customer": os.getenv("COMPANY_NAME"),
            "required_by_date": required_by_date,
            "ordered_date": ordered_date,
            "material": material_type
        },
        "job_site_info": {
            "company_address": os.getenv("COMPANY_NAME"),
            "sold_to": os.getenv("COMPANY_NAME"),
            "ship_to": os.getenv("COMPANY_ADDRESS"),
            "po_number": po_number,
            "order_contact_email": os.getenv("COMPANY_EMAIL"),
            "delivery_contact_phone": os.getenv("COMPANY_PHONE"),
            "customer": os.getenv("COMPANY_NAME"),
            "required_by_date": required_by_date,
            "ordered_date": ordered_date,
            "material": material_type
        }
    }

    return {
        "status": "success",
        "message": "PO infromtion retrieved successfully.",
        "data": data
    }
