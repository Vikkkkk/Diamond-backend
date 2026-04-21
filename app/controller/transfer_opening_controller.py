import json
from utils.schedule_data_helper import build_schedule_data_dict, compare_schedule_data
from utils.schedule_hardware_data_helper import build_schedule_hardware_dict, compare_schedule_hardware_data
from models.raw_materials import RawMaterials
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_section_areas import ProjectTakeOffSheetSectionAreas
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.opening_schedules import OpeningSchedules
from models.schedules import Schedules
from models.schedule_data import ScheduleData, COMPONENT_TYPE
from models.hardware_product_category import HardwareProductCategory
from models.project_materials import ProjectMaterials
from models.hardware_group_materials import HardwareGroupMaterials
from models.opening_hardware_materials import OpeningHardwareMaterials
from models.opening_door_frame_materials import OpeningDoorFrameMaterials
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from models.schedule_opening_door_frame_material import ScheduleOpeningDoorFrameMaterials, MATERIAL_TYPE
from models.adon_opening_fields import AdonOpeningFields
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.opening_change_stats import OpeningChangeStats
from utils.common import find_best_match_dict, get_all_pricing_breakdown
import os
import traceback
from rapidfuzz import fuzz
from typing import List, Dict, Optional
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from loguru import logger
from collections import defaultdict
from datetime import datetime
from schemas.ordered_item_schema import COMPONENT_TYPE

async def transfer_opening(db, project_id, current_member_id):
    """
    Transfers opening data from a project's take-off sheet into the scheduling system.

    This function performs the following tasks:
    - Validates and fetches the take-off sheet associated with a given project.
    - Retrieves all section area items from the take-off sheet.
    - For each item:
        - Validates required adon_fields like 'hand' and 'door_type'.
        - Retrieves display names for hand and door type.
        - Checks if the schedule entry already exists.
        - Creates or updates the schedule entry.
        - Deletes any existing component data associated with the schedule.
        - Clones and attaches new component-wise data (door, frame, hardware).
        - Prepares and updates take-off and hardware data.

    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): The ID of the project for which the data is being transferred.
        current_member_id (User): The user object initiating the transfer, used for audit tracking.

    Returns:
        JSONResponse: A response object with a success message on successful cloning.

    Raises:
        HTTPException: If the take-off sheet or opening items are not found,
                       or if the adon_fields are incomplete or invalid.
        HTTPException: If any unexpected error occurs during the operation.
    """
    try:
        take_off_sheet_info = db.query(ProjectTakeOffSheets).filter(
            ProjectTakeOffSheets.project_id == project_id
        ).first()

        if not take_off_sheet_info:
            raise HTTPException(status_code=404, detail="Take-off-sheet not found")

        # Fetch the item by opening number
        items = db.query(ProjectTakeOffSheetSectionAreaItems).filter(
            ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_sheet_info.id
        ).all()

        if not items:
            raise HTTPException(status_code=404, detail="Opening not found")
        
        for item in items:

            take_off_area_item_id = item.id

            # Fetch the section area info using its ID
            section_area = db.query(ProjectTakeOffSheetSectionAreas).get(item.project_take_off_sheet_section_area_id)

            # Retrieve adon fields (e.g., hand and door type options)
            adon_fields = item.adon_fields or {}
            
            hand_id = adon_fields.get("hand")
            door_type_id = adon_fields.get("door_type")
            
            if not hand_id or not door_type_id:
                raise HTTPException(status_code=400, detail="Incomplete adon_fields information")

            # Fetch display names for hand and door type from options table
            hand_info = db.query(AdonOpeningFieldOptions).get(adon_fields['hand'])
            door_type_info = db.query(AdonOpeningFieldOptions).get(adon_fields['door_type'])

            if not hand_info or not door_type_info:
                raise HTTPException(status_code=400, detail="Invalid hand or door_type option ID")
    
            # Check if the opening already exists in the Schedules table
            schedule = db.query(Schedules).filter(
                Schedules.opening_number == item.opening_number
            ).first()

            # Prepare the schedule entry information
            schedule_info = {
                "opening_number": item.opening_number,
                "type": "OPENING",
                "take_off_area_item_id": take_off_area_item_id,
                "section_id": item.project_take_off_sheet_section_id,
                "project_id": take_off_sheet_info.project_id,
                "is_active": True,
                "area": section_area.name,
                "door_material_code": item.door_raw_material_type,
                "frame_material_code": item.frame_raw_material_type,
                "door_type": door_type_info.name,
                "swing": hand_info.name,
                "location_1": item.location_1,
                "from_to": item.from_to,
                "location_2": item.location_2,
                "frame_qty": 1,
                "door_qty": 1,
                "quantity": 1,
                "installation_amount":item.installation_charge if item.installation_charge else 0,
                "created_by": current_member_id.id  # Placeholder for user info
            }
            if "door_material_code" in schedule_info:
                door_mat_data = db.query(RawMaterials).filter(RawMaterials.code == schedule_info["door_material_code"]).first()
                door_material_id = door_mat_data.id
                schedule_info["door_material_id"] = door_material_id
            if "frame_material_code" in schedule_info:
                frame_mat_data = db.query(RawMaterials).filter(RawMaterials.code == schedule_info["frame_material_code"]).first()
                frame_material_id = frame_mat_data.id
                schedule_info["frame_material_id"] = frame_material_id
            # print("schedule_info:: ", json.dumps(schedule_info, indent=3))
            # Insert or get the existing schedule ID
            if not schedule:
                # Insert new schedule record
                new_schedule = Schedules(**schedule_info)
                db.add(new_schedule)
                db.flush()  # To get the autogenerated ID
                schedule_id = new_schedule.id
            else:
                # Use existing schedule ID
                schedule_id = schedule.id

            # Remove any existing component data linked to this schedule
            await delete_schedule_data(db, schedule_id)

            # Clone component-wise data: door, frame, hardware
            door_schedule_data = await component_wise_clone_opening(db, schedule_id, take_off_area_item_id, component_type="DOOR")
            # print("door_schedule_data", door_schedule_data)
            frame_schedule_data = await component_wise_clone_opening(db, schedule_id, take_off_area_item_id, component_type="FRAME")
            hardware_data = await hardware_cloning(db, schedule_id, take_off_area_item_id, project_id)
            
            # Catalog door and frame materials in opening_door_frame_materials table
            door_frame_materials = await door_frame_material_cataloging(db, schedule_id, take_off_area_item_id, project_id)

            # Convert dict data to SQLAlchemy model objects
            door_components = [ScheduleData(**door_item) for door_item in door_schedule_data]
            frame_components = [ScheduleData(**frame_item) for frame_item in frame_schedule_data]

            # Add new component records to the session
            db.add_all(door_components + frame_components)
            db.flush()  # Flush to persist components so they’re available in queries
            
            # Prepare take-off-data
            take_off_data = await prepare_take_off_data(db, schedule_id)

            # Prepare hardware data
            take_off_hardware_data = await prepare_hardware_data(db, schedule_id)

            # Update Schedules with prepare take-off-data
            db.query(Schedules).filter(Schedules.id == schedule_id).update({'take_off_data': take_off_data, 'take_off_hardware_data': take_off_hardware_data})

        # Commit all changes to the database
        db.commit()

        # Return success response
        return JSONResponse(content={"message": "Data Cloned Successfully", "status": "success", "door_schedule_data": door_schedule_data, "frame_schedule_data": frame_schedule_data, "hardware_data": hardware_data}, status_code=200)

    except Exception as e:
        # Log the exception and raise HTTP 500 error
        print(traceback.format_exc())
        db.rollback()
        logger.exception(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def delete_schedule_data(db, schedule_id):
    """
    Deletes all component data (e.g., door, frame, hardware) associated with a given schedule ID.

    Args:
        db: SQLAlchemy session object.
        schedule_id (int): The ID of the schedule whose data should be deleted.

    Returns:
        None
    """
    # Delete all rows from ScheduleData where the schedule_id matches
    db.query(ScheduleData).filter(ScheduleData.schedule_id == schedule_id).delete()

    # Flush the changes to the database (does not commit)
    db.flush()


async def hardware_cloning(db, schedule_id, take_off_area_item_id, project_id):
    """
    Clones hardware data from a take-off area item into a corresponding schedule.

    This function:
    - Retrieves the hardware group associated with the given take-off area item.
    - Extracts related `ProjectMaterials` and their associated data.
    - Prepares or reuses `OpeningHardwareMaterials` entries.
    - Clones relevant material financial details and metadata.
    - Inserts mapped records into the `ScheduleOpeningHardwareMaterials` table if not already present.

    Args:
        db (Session): SQLAlchemy database session.
        schedule_id (int): ID of the schedule into which hardware data will be cloned.
        take_off_area_item_id (int): ID of the take-off area item containing source hardware information.
        project_id (int): ID of the current project, used for filtering and linking data.

    Returns:
        None

    Raises:
        Exception: If any required record is missing or a database operation fails.
    """
    responses = []
    # Fetch the original hardware entry for the given take-off area item
    opening_hardware = db.query(OpeningSchedules).filter(
        OpeningSchedules.project_take_off_sheet_section_area_item_id == take_off_area_item_id,
        OpeningSchedules.component == "HARDWARE"
    ).first()

    # Extract the hardware group ID
    hardware_group_id = opening_hardware.hardware_group_id

    # Get all related ProjectMaterial IDs from the hardware group
    project_material_ids = [
        mat.hardware_group_material.id
        for mat in opening_hardware.opening_hardware_group.hardware_group_materials
    ]

    # Fetch the HardwareProductCategory object for categorizing new materials
    hardware_product_category = db.query(HardwareProductCategory).filter(
        HardwareProductCategory.name == "Miscellaneous Item"
    ).first()

    # Retrieve the actual material records from ProjectMaterials
    project_materials = db.query(ProjectMaterials).filter(
        ProjectMaterials.id.in_(project_material_ids)
    ).all()
    # print(project_material_ids)
    for project_material in project_materials:
        material_id = project_material.id
        quantity = 1  # Default quantity for cloning

        short_code = project_material.short_code
        print("basic default discount:: ",project_material.discount_is_basic)
        # Prepare data for insertion into OpeningHardwareMaterials
        material_data = {
            'short_code': short_code,
            'desc': project_material.desc,
            'series': project_material.series,
            'base_feature': project_material.base_feature,
            'base_price': project_material.base_price,
            'adon_feature': project_material.adon_feature,
            'adon_price': project_material.adon_price,
            'total_amount': project_material.total_amount,
            'total_sell_amount': project_material.total_sell_amount,
            'total_base_amount': project_material.total_base_amount,
            'total_extended_sell_amount': project_material.total_extended_sell_amount,
            'quantity': quantity,
            'final_amount': project_material.total_amount * quantity,
            'final_sell_amount': project_material.total_sell_amount * quantity,
            'final_base_amount': project_material.total_base_amount * quantity,
            'final_extended_sell_amount': project_material.total_extended_sell_amount * quantity,
            'manufacturer_id': project_material.manufacturer_id,
            'brand_id': project_material.brand_id,
            'project_id': project_material.project_id,
            'markup': project_material.markup,
            'margin': project_material.margin,
            'is_basic_discount': project_material.discount_is_basic,
            'discount': project_material.discount,
            'discount_type': project_material.discount_type.value,
            'surcharge': project_material.surcharge,
            'surcharge_type': project_material.surcharge_type.value if project_material.surcharge_type else None,
            'hardware_product_category_id': project_material.hardware_product_category_id if project_material.hardware_product_category_id else hardware_product_category.id
        }

        # Get group material information for further cloning
        hardware_group_material = db.query(HardwareGroupMaterials).filter(
            HardwareGroupMaterials.project_material_id == material_id,
            HardwareGroupMaterials.hardware_group_id == hardware_group_id
        ).first()

        # Prepare data for ScheduleOpeningHardwareMaterials entry
        group_material_data = {
            'desc': hardware_group_material.desc,
            'total_amount': hardware_group_material.total_amount,
            'total_sell_amount': hardware_group_material.total_sell_amount,
            'total_base_amount': hardware_group_material.total_base_amount,
            'total_extended_sell_amount': hardware_group_material.total_extended_sell_amount,
            'quantity': hardware_group_material.quantity,
            'final_amount': hardware_group_material.final_amount,
            'final_sell_amount': hardware_group_material.final_sell_amount,
            'final_base_amount': hardware_group_material.final_base_amount,
            'final_extended_sell_amount': hardware_group_material.final_extended_sell_amount
        }

        # Check if the material already exists in OpeningHardwareMaterials by short_code
        opening_hardware_material = db.query(OpeningHardwareMaterials).filter(
            OpeningHardwareMaterials.short_code == short_code, OpeningHardwareMaterials.project_id == project_id
        ).first()

        if opening_hardware_material:
            # Reuse the existing material record
            opening_hardware_material_id = opening_hardware_material.id
        else:
            # Insert a new OpeningHardwareMaterial record
            new_material = OpeningHardwareMaterials(**material_data)
            db.add(new_material)
            db.flush()
            opening_hardware_material_id = new_material.id

        # Add foreign keys to the group material data
        group_material_data['opening_hardware_material_id'] = opening_hardware_material_id
        group_material_data['schedule_id'] = schedule_id

        # Check if this material is already mapped to the schedule
        schedule_opening_hardware_material_count = db.query(ScheduleOpeningHardwareMaterials).filter(
            ScheduleOpeningHardwareMaterials.opening_hardware_material_id == opening_hardware_material_id,
            ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
        ).first()

        if not schedule_opening_hardware_material_count:
            # Insert into ScheduleOpeningHardwareMaterials mapping table
            print("group_material_data>>", group_material_data)
            new_group_material = ScheduleOpeningHardwareMaterials(**group_material_data)
            db.add(new_group_material)
            db.flush()
        responses.append(material_data)
    return responses


async def door_frame_material_cataloging(db, schedule_id, take_off_area_item_id, project_id):
    """
    Catalogs door and frame materials in the opening_door_frame_materials table
    and creates schedule-material mappings.

    This function:
    - Retrieves door and frame material data from the take-off area items.
    - Checks if the material already exists in the opening_door_frame_materials table.
    - Creates new entries for materials that don't already exist.
    - Creates mappings in schedule_opening_door_frame_materials junction table.
    - Serves as a master catalog of all door/frame materials used in the project.

    Args:
        db (Session): SQLAlchemy database session.
        schedule_id (str): ID of the schedule to which materials will be linked.
        take_off_area_item_id (int): ID of the take-off area item containing source material information.
        project_id (int): ID of the current project, used for filtering and linking data.

    Returns:
        list: A list of dictionaries containing information about cataloged materials.

    Notes:
        - Materials are deduplicated by short_code + project_id + material_type.
        - Creates new entries in both opening_door_frame_materials and schedule junction table.
        - Processes both DOOR and FRAME materials in the same function.
    """
    responses = []
    
    # Process both DOOR and FRAME components
    for component_type in ["DOOR", "FRAME"]:
        # Fetch the material entry for the given take-off area item and component type
        opening_material_schedules = db.query(OpeningSchedules).filter(
            OpeningSchedules.project_take_off_sheet_section_area_item_id == take_off_area_item_id,
            OpeningSchedules.component == component_type
        ).order_by(OpeningSchedules.created_at.asc()).all()
    
        for indx,  opening_material_schedule in enumerate(opening_material_schedules):
            if not opening_material_schedule:
                continue  # Skip if no material found for this component type

            # Get the project material details
            project_material = opening_material_schedule.opening_material
        
            if not project_material:
                continue  # Skip if no project material linked

            short_code = project_material.short_code
            quantity = 1  # Default quantity
        
            # Get raw_material_code from RawMaterials table using opening_material_schedule.raw_material_id
            raw_material_code = None
            if opening_material_schedule.raw_material_id:
                raw_material = db.query(RawMaterials).filter(
                    RawMaterials.id == opening_material_schedule.raw_material_id
                ).first()
                if raw_material:
                    raw_material_code = raw_material.code
            
            # Check if this material already exists in the catalog
            existing_material = db.query(OpeningDoorFrameMaterials).filter(
                OpeningDoorFrameMaterials.short_code == short_code,
                OpeningDoorFrameMaterials.project_id == project_id,
                OpeningDoorFrameMaterials.material_type == component_type
            ).first()
            if existing_material:
                # Material already cataloged, update with latest pricing data
                opening_door_frame_material_id = existing_material.id
                
                # Update raw_material_code if not set or different
                if raw_material_code and (not existing_material.raw_material_code or existing_material.raw_material_code != raw_material_code):
                    existing_material.raw_material_code = raw_material_code
                
                # Update pricing and feature data
                existing_material.desc = project_material.desc
                existing_material.base_feature = project_material.base_feature
                existing_material.base_price = project_material.base_price
                existing_material.adon_feature = project_material.adon_feature
                existing_material.adon_price = project_material.adon_price
                existing_material.markup = project_material.markup
                existing_material.margin = project_material.margin
                existing_material.is_basic_discount = project_material.discount_is_basic
                existing_material.discount = project_material.discount
                existing_material.discount_type = project_material.discount_type.value if project_material.discount_type else None
                existing_material.surcharge = project_material.surcharge
                existing_material.surcharge_type = project_material.surcharge_type.value if project_material.surcharge_type else None
                existing_material.total_amount = project_material.total_amount
                existing_material.total_sell_amount = project_material.total_sell_amount
                existing_material.total_base_amount = project_material.total_base_amount
                existing_material.total_extended_sell_amount = project_material.total_extended_sell_amount
                existing_material.final_amount = project_material.total_amount * quantity
                existing_material.final_sell_amount = project_material.total_sell_amount * quantity
                existing_material.final_base_amount = project_material.total_base_amount * quantity
                existing_material.final_extended_sell_amount = project_material.total_extended_sell_amount * quantity
                
                # Format and store schedule_master_data
                schedule_master_data = await format_material_schedule_data(db, existing_material, component_type)
                if schedule_master_data:
                    existing_material.schedule_master_data = schedule_master_data
                
                db.flush()
            else:
                # Prepare data for insertion into OpeningDoorFrameMaterials
                material_data = {
                    'name': project_material.name,
                    'short_code': short_code,
                    'desc': project_material.desc,
                    'series': project_material.series,
                    'material_type': component_type,
                    'raw_material_code': raw_material_code,  # Set from RawMaterials table
                    'base_feature': project_material.base_feature,
                    'base_price': project_material.base_price,
                    'adon_feature': project_material.adon_feature,
                    'adon_price': project_material.adon_price,
                    'manufacturer_id': project_material.manufacturer_id,
                    'brand_id': project_material.brand_id,
                    'project_id': project_id,
                    'markup': project_material.markup,
                    'margin': project_material.margin,
                    'is_basic_discount': project_material.discount_is_basic,
                    'discount': project_material.discount,
                    'discount_type': project_material.discount_type.value if project_material.discount_type else None,
                    'surcharge': project_material.surcharge,
                    'surcharge_type': project_material.surcharge_type.value if project_material.surcharge_type else None,
                    'total_amount': project_material.total_amount,
                    'total_sell_amount': project_material.total_sell_amount,
                    'total_base_amount': project_material.total_base_amount,
                    'total_extended_sell_amount': project_material.total_extended_sell_amount,
                    'quantity': quantity,
                    'final_amount': project_material.total_amount * quantity,
                    'final_sell_amount': project_material.total_sell_amount * quantity,
                    'final_base_amount': project_material.total_base_amount * quantity,
                    'final_extended_sell_amount': project_material.total_extended_sell_amount * quantity,
                    'is_active': True
                }

                # Format and add schedule_master_data to the material_data
                schedule_master_data = await format_material_schedule_data(db, material_data, component_type)
                if schedule_master_data:
                    material_data['schedule_master_data'] = schedule_master_data
                
                # Insert new material into the catalog
                new_material = OpeningDoorFrameMaterials(**material_data)
                db.add(new_material)
                db.flush()
                opening_door_frame_material_id = new_material.id

            # Check if this material is already mapped to the schedule
            schedule_door_frame_material_exists = db.query(ScheduleOpeningDoorFrameMaterials).filter(
                ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id == opening_door_frame_material_id,
                ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id
            ).first()

            is_door_material = str(component_type).upper() == "DOOR"
            part_number = None
            if is_door_material:
                if schedule_door_frame_material_exists and schedule_door_frame_material_exists.part_number:
                    part_number = schedule_door_frame_material_exists.part_number
                else:
                    existing_part_numbers = db.query(ScheduleOpeningDoorFrameMaterials.part_number).filter(
                        ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id,
                        ScheduleOpeningDoorFrameMaterials.material_type == MATERIAL_TYPE.DOOR
                    ).all()
                    numeric_part_numbers = []
                    for (pn,) in existing_part_numbers:
                        pn_str = str(pn) if pn is not None else ""
                        if pn_str.isdigit():
                            numeric_part_numbers.append(int(pn_str))
                    part_number = str((max(numeric_part_numbers) if numeric_part_numbers else 0) + 1)

            # Prepare data for ScheduleOpeningDoorFrameMaterials entry
            schedule_material_data = {
                'desc': project_material.desc,
                'material_type': component_type,
                'total_amount': project_material.total_amount,
                'total_sell_amount': project_material.total_sell_amount,
                'total_base_amount': project_material.total_base_amount,
                'total_extended_sell_amount': project_material.total_extended_sell_amount,
                'quantity': quantity,
                'final_amount': project_material.total_amount * quantity,
                'final_sell_amount': project_material.total_sell_amount * quantity,
                'final_base_amount': project_material.total_base_amount * quantity,
                'final_extended_sell_amount': project_material.total_extended_sell_amount * quantity,
                'opening_door_frame_material_id': opening_door_frame_material_id,
                'schedule_id': schedule_id,
                'part_number': part_number if is_door_material else None
            }

            schedule_action = 'updated' if schedule_door_frame_material_exists else 'created'

            if not schedule_door_frame_material_exists:
                # Insert into ScheduleOpeningDoorFrameMaterials mapping table
                new_schedule_material = ScheduleOpeningDoorFrameMaterials(**schedule_material_data)
                db.add(new_schedule_material)
                db.flush()
            else:
                # Update existing record with latest pricing data
                for key, value in schedule_material_data.items():
                    setattr(schedule_door_frame_material_exists, key, value)
                db.flush()
            
            responses.append({
                'short_code': short_code,
                'material_type': component_type,
                'opening_door_frame_material_id': opening_door_frame_material_id,
                'schedule_id': schedule_id,
                'action': schedule_action
            })

    return responses


async def format_material_schedule_data(db, material_obj, component_type):
    """Helper function to format material data into schedule format.
    
    Mirrors the logic of component_wise_clone_opening but works directly with
    a material object (dict or ORM model) instead of querying OpeningSchedules.
    
    Args:
        db (Session): SQLAlchemy database session.
        material_obj: Material object or dict with base_feature, adon_feature, pricing data
        component_type (str): Component type (DOOR or FRAME)
    
    Returns:
        dict: Formatted schedule data structure with component_type as key,
              containing 'fields' dict and 'price_details'.
    """
    def get_attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    
    base_feature = get_attr(material_obj, 'base_feature')
    adon_feature = get_attr(material_obj, 'adon_feature')
    base_price = get_attr(material_obj, 'base_price')
    adon_price = get_attr(material_obj, 'adon_price')
    
    manufacturer_id = get_attr(material_obj, 'manufacturer_id')
    brand_id = get_attr(material_obj, 'brand_id')
    
    # Get manufacturer and brand info
    manufacturer = db.query(Manufacturers).filter(Manufacturers.id == manufacturer_id).first()

    if brand_id:
        brand = db.query(Brands).filter(Brands.id == brand_id).first()
        catalog_name = brand.name
    else:
        catalog_name = manufacturer.name

    component = component_type.upper()
    catalog_key = 'door_catalog' if component == "DOOR" else 'frame_catalog'
    series_key = 'door_series' if component == "DOOR" else 'frame_series'

    # Extract pricing from base_price (mirrors component_wise_clone_opening logic)
    base_price_data = base_price.get('data', {}) if base_price else {}
    current_unit = base_price.get("currentUnit") if base_price else None
    price_list = base_price_data.get("pricePerQuantity", []) if base_price_data else []
    total_amount = next((item["price"] for item in price_list if item["unit"] == current_unit), 0) if current_unit else 0

    # Get discount/markup/surcharge values
    discount_type = get_attr(material_obj, 'discount_type')
    discount_type = discount_type.value if hasattr(discount_type, 'value') else discount_type

    discount = get_attr(material_obj, 'discount', 0) or 0
    markup = get_attr(material_obj, 'markup', 0) or 0
    margin = get_attr(material_obj, 'margin', 0) or 0

    surcharge_type = get_attr(material_obj, 'surcharge_type')
    surcharge_type = surcharge_type.value if hasattr(surcharge_type, 'value') else surcharge_type

    surcharge = get_attr(material_obj, 'surcharge', 0) or 0
    is_basic_discount = get_attr(material_obj, 'is_basic_discount', True)
    if is_basic_discount is None:
        is_basic_discount = True

    # Calculate pricing breakdown
    price_breakdown = await get_all_pricing_breakdown(discount, discount_type, markup, surcharge_type, surcharge, total_amount, quantity=1)
    total_base_amount = price_breakdown['total_base_amount']
    total_sell_amount = price_breakdown['total_sell_amount']
    total_extended_sell_amount = price_breakdown['total_extended_sell_amount']

    quantity = 1

    # Get all adon opening field definitions (used to map adon feature codes to readable names)
    opening_fields = db.query(AdonOpeningFields).all()
    opening_fields_dict = [
        {"id": field.id, "name": field.name, "desc": field.desc}
        for field in opening_fields
    ]

    component_data = {}
    fields_dict = {}

    # Append catalog and series as features with full pricing
    for name, value in [(catalog_key, catalog_name), (series_key, get_attr(material_obj, 'series'))]:
        fields_dict[name] = {
            "name": name,
            "feature_code": name,
            "value": value,
            "component": component,
            "is_adon_field": False,
            "has_price_dependancy": True,
            "total_amount": round((total_amount or 0), 3),
            "total_base_amount": round((total_base_amount or 0), 3),
            "total_sell_amount": round((total_sell_amount or 0), 3),
            "total_extended_sell_amount": round((total_extended_sell_amount or 0), 3),
            "quantity": quantity,
            "final_amount": round((total_amount or 0) * quantity, 3),
            "discount": round((discount or 0), 3),
            "final_base_amount": round((total_base_amount or 0) * quantity, 3),
            "markup": round((markup or 0), 3),
            "margin": round((margin or 0), 3),
            "final_sell_amount": round((total_sell_amount or 0) * quantity, 3),
            "surcharge": round((surcharge or 0), 3),
            "final_extended_sell_amount": round((total_extended_sell_amount or 0) * quantity, 3),
            "is_basic_discount": is_basic_discount,
            "discount_type": discount_type,
            "surcharge_type": surcharge_type,
            "price_data": price_list,
            "feature_data": base_price_data
        }

    # Append base features (selectedFeatures) as schedule features
    if base_feature and isinstance(base_feature, dict):
        selected_features = base_feature.get('selectedFeatures', base_feature)
        for feature_key, feature_value in selected_features.items():
            option_code = feature_value.get('optionCode', feature_value) if isinstance(feature_value, dict) else feature_value
            fields_dict[feature_key] = {
                "name": feature_key,
                "feature_code": feature_key,
                "value": option_code,
                "option_code": option_code,
                "component": component,
                "is_adon_field": False,
                "has_price_dependancy": True,
                "total_amount": round((total_amount or 0), 3),
                "total_base_amount": round((total_base_amount or 0), 3),
                "total_sell_amount": round((total_sell_amount or 0), 3),
                "total_extended_sell_amount": round((total_extended_sell_amount or 0), 3),
                "quantity": quantity,
                "final_amount": round((total_amount or 0) * quantity, 3),
                "discount": round((discount or 0), 3),
                "final_base_amount": round((total_base_amount or 0) * quantity, 3),
                "markup": round((markup or 0), 3),
                "margin": round((margin or 0), 3),
                "final_sell_amount": round((total_sell_amount or 0) * quantity, 3),
                "surcharge": round((surcharge or 0), 3),
                "final_extended_sell_amount": round((total_extended_sell_amount or 0) * quantity, 3),
                "is_basic_discount": is_basic_discount,
                "discount_type": discount_type,
                "surcharge_type": surcharge_type,
                "price_data": price_list,
                "feature_data": base_price_data
            }

    # Append adon features (custom fields) with full pricing (mirrors component_wise_clone_opening)
    if adon_feature and isinstance(adon_feature, dict):
        for adon_feature_key, adon_feature_value in adon_feature.items():
            addon_feature_code = adon_feature_key

            # Match adon feature key with a human-readable name and description
            addon_feature_best_match = await best_match(addon_feature_code, opening_fields_dict)
            name = addon_feature_best_match['name'] if addon_feature_best_match else adon_feature_key
            desc = addon_feature_best_match.get('desc', '') if addon_feature_best_match else ''

            pricing_section = adon_price.get(addon_feature_code, {}) if adon_price else {}

            results = []
            if isinstance(adon_feature_value, dict):
                for label, value in adon_feature_value.items():
                    option_code = value.get('option', {}).get('optionCode', '') if isinstance(value, dict) else value
                    feat_quantity = int(value.get('quantity', 1)) if isinstance(value, dict) else 1

                    # Fetch the price for the option from the pricing section
                    price = pricing_section.get(label, {}).get('data', {}).get('pricePerQuantity', [{}])[0].get('price', 0)
                    price_per_quantity = pricing_section.get(label, {}).get('data', {}).get('pricePerQuantity', [{}])
                    feat_feature_data = pricing_section.get(label, {}).get('data', {})
                    results.append({
                        'optionCode': option_code,
                        'quantity': feat_quantity,
                        'price': price,
                        'feature_data': feat_feature_data,
                        'price_data': price_per_quantity
                    })

            # Pick the first result to use for creating the feature entry
            if results:
                option_code = results[0]['optionCode']
                feature_data = results[0]['feature_data']
                price_data = results[0]['price_data']
                adon_quantity = results[0]['quantity']
                adon_total_amount = results[0]['price']
            else:
                option_code = adon_feature_value if isinstance(adon_feature_value, str) else ''
                feature_data = {}
                price_data = []
                adon_quantity = 1
                adon_total_amount = 0

            # Get addon field id and option id
            addon_field_data = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == name).first()
            addon_field_id = addon_option_id = None

            if addon_field_data:
                addon_field_id = addon_field_data.id
                addon_option_data = db.query(AdonOpeningFieldOptions).filter(
                    AdonOpeningFieldOptions.name == option_code
                ).first()
                if addon_option_data:
                    addon_option_id = addon_option_data.id

            adon_price_breakdown = await get_all_pricing_breakdown(discount, discount_type, markup, surcharge_type, surcharge, adon_total_amount, quantity=adon_quantity)
            adon_total_base_amount = adon_price_breakdown['total_base_amount']
            adon_total_sell_amount = adon_price_breakdown['total_sell_amount']
            adon_total_extended_sell_amount = adon_price_breakdown['total_extended_sell_amount']

            fields_dict[name] = {
                "name": name,
                "desc": desc,
                "feature_code": name,
                "value": option_code,
                "option_code": option_code,
                "component": component,
                "is_adon_field": True,
                "has_price_dependancy": True,
                "total_amount": round((adon_total_amount or 0), 3),
                "total_base_amount": round((adon_total_base_amount or 0), 3),
                "total_sell_amount": round((adon_total_sell_amount or 0), 3),
                "total_extended_sell_amount": round((adon_total_extended_sell_amount or 0), 3),
                "quantity": adon_quantity,
                "final_amount": round((adon_total_amount or 0) * adon_quantity, 3),
                "discount": round((discount or 0), 3),
                "final_base_amount": round((adon_total_base_amount or 0) * adon_quantity, 3),
                "markup": round((markup or 0), 3),
                "margin": round((margin or 0), 3),
                "final_sell_amount": round((adon_total_sell_amount or 0) * adon_quantity, 3),
                "surcharge": round((surcharge or 0), 3),
                "final_extended_sell_amount": round((adon_total_extended_sell_amount or 0) * adon_quantity, 3),
                "is_basic_discount": is_basic_discount,
                "discount_type": discount_type,
                "surcharge_type": surcharge_type,
                "adon_field_id": addon_field_id,
                "adon_field_option_id": addon_option_id,
                "feature_data": feature_data,
                "price_data": price_data
            }

    # Store with component type as key
    if fields_dict:
        component_data[component] = {
            "fields": fields_dict,
            "price_details": {
                "total_amount": round((total_amount or 0), 3),
                "total_base_amount": round((total_base_amount or 0), 3),
                "total_sell_amount": round((total_sell_amount or 0), 3),
                "total_extended_sell_amount": round((total_extended_sell_amount or 0), 3),
                "final_amount": round((total_amount or 0) * quantity, 3),
                "final_base_amount": round((total_base_amount or 0) * quantity, 3),
                "final_sell_amount": round((total_sell_amount or 0) * quantity, 3),
                "final_extended_sell_amount": round((total_extended_sell_amount or 0) * quantity, 3),
            }
        }
    
    return component_data


async def sync_material_schedule_data(db, opening_door_frame_material_id: str):
    """Helper function to format and store material's own data in schedule format.
    
    Args:
        db (Session): SQLAlchemy database session.
        opening_door_frame_material_id (str): ID of the door/frame material to format
    
    Returns:
        None
    """
    try:
        material = db.query(OpeningDoorFrameMaterials).filter(
            OpeningDoorFrameMaterials.id == opening_door_frame_material_id
        ).first()
        
        if not material or not material.material_type:
            return
        
        component_type = material.material_type 
        component_type= component_type if isinstance(component_type, str) else component_type.value
        component_data = await format_material_schedule_data(db, material, component_type)
        
        if component_data:
            material.schedule_master_data = component_data
            db.flush()
                
    except Exception as e:
        logger.exception(f"Error formatting material schedule data: {e}")
        # Don't raise - this is a helper function that shouldn't break the main flow


async def component_wise_clone_opening(db, schedule_id, take_off_area_item_id, component_type):
    """
    Clone opening schedule component-wise (DOOR or FRAME) along with all associated features 
    including base features and adon (custom) fields for a given take-off area item.

    This function performs the following:
    - Retrieves all `OpeningSchedules` entries matching the `component_type` (e.g., DOOR or FRAME)
      and associated with the given `take_off_area_item_id`.
    - Gathers related pricing data (base price, discount, surcharge, markup, margin) from the 
      linked `OpeningMaterial`.
    - Extracts both predefined catalog/series features and dynamic base features from material data.
    - Looks up and calculates prices for adon features, linking them with field and option IDs.
    - Computes pricing using `get_all_pricing` function and compiles a full feature breakdown for 
      the specified schedule and component.
    
    Parameters:
    ----------
    db : Session
        The SQLAlchemy session used for querying the database.
    schedule_id : int
        The ID of the schedule to which the features will be cloned.
    take_off_area_item_id : int
        The ID of the project area item under the take-off sheet.
    component_type : str
        The type of component to process, e.g., "DOOR" or "FRAME".
    
    Returns:
    -------
    List[dict]
        A list of feature dictionaries, each representing a feature with pricing, identifiers,
        and metadata for the component. These can be used to persist cloned features.
    """

    # Fetch all opening schedule data for the specified component (e.g., DOOR or FRAME)
    opening_schedule_data = db.query(OpeningSchedules)\
        .join(ProjectMaterials)\
        .filter(
            OpeningSchedules.project_take_off_sheet_section_area_item_id == take_off_area_item_id,
            OpeningSchedules.component == component_type).all()

    # Get all adon opening field definitions (used to map adon feature codes to readable names)
    opening_fields = db.query(AdonOpeningFields).all()
    opening_fields_dict = [
        {
            "id": field.id,
            "name": field.name,
            "desc": field.desc,
        }
        for field in opening_fields
    ]

    features = []
    part_number_checker = {}

    for schedule in opening_schedule_data:
        opening_material = schedule.opening_material

        # Get manufacturer and brand info
        manufacturer = db.query(Manufacturers).filter(Manufacturers.id == opening_material.manufacturer_id).first()

        if opening_material.brand_id:
            brand = db.query(Brands).filter(Brands.id == opening_material.brand_id).first()
            catalog_name = brand.name
        else:
            catalog_name = manufacturer.name

        # Determine component name and related catalog/series keys
        component = schedule.component.value
        catalog_key = 'door_catalog' if component == "DOOR" else 'frame_catalog'
        series_key = 'door_series' if component == "DOOR" else 'frame_series'
        # print(f"********************************{component}***********************************")
        # print(f"********************************{catalog_name}***********************************")
        # print(f"********************************{opening_material.series}***********************************")
        base_price = opening_material.base_price
        base_price_data = base_price['data'] if 'data' in base_price else {}
        # # Extract the current unit and price list
        current_unit = base_price["currentUnit"]
        price_list = base_price["data"]["pricePerQuantity"]

        total_amount = next((item["price"] for item in price_list if item["unit"] == current_unit), 0)
        
        discount_type = opening_material.discount_type
        discount_type = discount_type.value if hasattr(discount_type, 'value') else discount_type

        discount = opening_material.discount
        markup = opening_material.markup
        margin = opening_material.margin

        surcharge_type = opening_material.surcharge_type
        surcharge_type = surcharge_type.value if hasattr(surcharge_type, 'value') else surcharge_type

        surcharge = opening_material.surcharge
        price_breakdown = await get_all_pricing_breakdown(discount, discount_type, markup, surcharge_type, surcharge, total_amount, quantity=1)
        total_base_amount = price_breakdown['total_base_amount']
        total_sell_amount = price_breakdown['total_sell_amount']
        total_extended_sell_amount = price_breakdown['total_extended_sell_amount']
        
        # quantity
        quantity = 1

        # Append catalog and series as features
        for name, value in [
            (catalog_key, catalog_name),
            (series_key, opening_material.series)
        ]:
            # Generate unique part number per feature
            part_number_checker[name] = part_number_checker.get(name, 0) + 1
            part_number = part_number_checker[name]

            features.append({
                'schedule_id': schedule_id,
                'name': name,
                'value': value,
                'component': component,
                'is_adon_field': 0,
                'has_price_dependancy': 1,
                'total_amount': round((total_amount or 0), 3),
                'total_base_amount': round((total_base_amount or 0), 3),
                'total_sell_amount': round((total_sell_amount or 0), 3),
                'total_extended_sell_amount': round((total_extended_sell_amount or 0), 3),
                'quantity': quantity,
                'final_amount': round((total_amount or 0) * quantity, 3),
                'discount': round((discount or 0), 3),
                'final_base_amount': round((total_base_amount or 0) * quantity, 3),
                'markup': round((markup or 0), 3),
                'margin': round((margin or 0), 3),
                'final_sell_amount': round((total_sell_amount or 0) * quantity, 3),
                'surcharge': round((surcharge or 0)),
                'final_extended_sell_amount': round((total_extended_sell_amount or 0) * quantity, 3),
                'part_number': part_number if component_type == "DOOR" else None,
                'is_basic_discount': opening_material.discount_is_basic,
                'discount_type': discount_type,
                'surcharge_type': surcharge_type,
                'price_data': price_list,
                'feature_data': base_price_data
            })

        # Append base features as schedule features
        for feature_key, feature_value in opening_material.base_feature['selectedFeatures'].items():
            part_number_checker[feature_key] = part_number_checker.get(feature_key, 0) + 1
            part_number = part_number_checker[feature_key]
            _feature_data_content = {
                'schedule_id': schedule_id,
                'name': feature_key,
                'feature_code': feature_key,
                'value': feature_value['optionCode'],
                'option_code': feature_value['optionCode'],
                'component': component,
                'is_adon_field': 0,
                'has_price_dependancy': 1,
                'total_amount': round((total_amount or 0), 3),
                'total_base_amount': round((total_base_amount or 0), 3),
                'total_sell_amount': round((total_sell_amount or 0), 3),
                'total_extended_sell_amount': round((total_extended_sell_amount or 0), 3),
                'quantity': quantity,
                'final_amount': round((total_amount or 0) * quantity, 3),
                'discount': round((discount or 0), 3),
                'final_base_amount': round((total_base_amount or 0) * quantity, 3),
                'markup': round((markup or 0), 3),
                'margin': round((margin or 0), 3),
                'final_sell_amount': round((total_sell_amount or 0) * quantity, 3),
                'surcharge': round((surcharge or 0), 3),
                'final_extended_sell_amount': round((total_extended_sell_amount or 0) * quantity, 3),
                'feature_data': base_price_data,
                'part_number': part_number if component_type == "DOOR" else None,
                'is_basic_discount': opening_material.discount_is_basic,
                'discount_type': discount_type,
                'surcharge_type': surcharge_type,
                'price_data': price_list,
            }
            features.append(_feature_data_content)

        # Append adon features (custom fields) as schedule features
        if opening_material.adon_feature:
            for adon_feature_key, adon_feature_value in opening_material.adon_feature.items():
                
                addon_feature_code = adon_feature_key
                search_terms = []
                if isinstance(adon_feature_value, dict):
                    search_terms.extend(list(adon_feature_value.keys()))
                search_terms.append(adon_feature_key)
                print("search_terms----------------------------")
                print("search_terms:: ",search_terms)
                # Match adon feature key with a human-readable name and description
                addon_feature_best_match = await best_match(addon_feature_code, opening_fields_dict)
                # addon_feature_best_match = await find_best_match_dict(search_terms, opening_fields_dict, "name")
                print("addon_feature_best_match:: ",addon_feature_best_match)
                print("search_terms----------------------------")
                name = addon_feature_best_match['name']
                desc = addon_feature_best_match['desc']

                pricing_section = opening_material.adon_price.get(addon_feature_code, {})
   
                results = []
                price_per_quantity_data = []
                for label, value in adon_feature_value.items():
                    option_code = value['option']['optionCode']
                    quantity = int(value['quantity'])

                    # Fetch the price for the option from the pricing section
                    price = pricing_section.get(label, {}).get('data', {}).get('pricePerQuantity', [{}])[0].get('price', 0)
                    price_per_quantity = pricing_section.get(label, {}).get('data', {}).get('pricePerQuantity', [{}])
                    feature_data = pricing_section.get(label, {}).get('data', {})
                    results.append({
                        'optionCode': option_code,
                        'quantity': quantity,
                        'price': price,
                        'feature_data': feature_data,
                        'price_data': price_per_quantity
                    })  

                    price_per_quantity_data.append(price_per_quantity)

                # Pick the first result to use for creating the schedule entry
                if len(results) > 0:
                    option_code = results[0]['optionCode']
                    
                    feature_data = results[0]['feature_data']

                    price_data = results[0]['price_data']
                    quantity = results[0]['quantity']
                    total_amount = results[0]['price']

                # Get addon field id
                addon_field_data = db.query(AdonOpeningFields).filter(AdonOpeningFields.name == name).first()

                addon_field_id = addon_option_id = None

                if addon_field_data:
                    addon_field_id = addon_field_data.id
                    addon_option_data = db.query(AdonOpeningFieldOptions).filter(
                        AdonOpeningFieldOptions.name == option_code
                    ).first()
                    
                    if addon_option_data:
                        addon_option_id = addon_option_data.id

                
                price_breakdown = await get_all_pricing_breakdown(discount, discount_type, markup, surcharge_type, surcharge, total_amount, quantity=quantity)
                total_base_amount = price_breakdown['total_base_amount']
                total_sell_amount = price_breakdown['total_sell_amount']
                total_extended_sell_amount = price_breakdown['total_extended_sell_amount']

                _adon_feature_data_content = {
                    'schedule_id': schedule_id,
                    'name': name,
                    'desc': desc,
                    'feature_code': name,
                    'value': option_code,
                    'option_code': option_code,
                    'component': component,
                    'is_adon_field': 1,
                    'has_price_dependancy': 1,
                    'total_amount': round((total_amount or 0), 3),
                    'total_base_amount': round((total_base_amount or 0), 3),
                    'total_sell_amount': round((total_sell_amount or 0), 3),
                    'total_extended_sell_amount': round((total_extended_sell_amount or 0), 3),
                    'quantity': quantity,
                    'final_amount': round((total_amount or 0) * quantity, 3),
                    'discount': round((discount or 0), 3),
                    'final_base_amount': round((total_base_amount or 0) * quantity, 3),
                    'markup': round((markup or 0), 3),
                    'margin': round((margin or 0), 3),
                    'final_sell_amount': round((total_sell_amount or 0) * quantity, 3),
                    'surcharge': round((surcharge or 0), 3),
                    'final_extended_sell_amount': round((total_extended_sell_amount or 0) * quantity, 3),
                    'part_number': part_number if component_type == "DOOR" else None,
                    'is_basic_discount': opening_material.discount_is_basic,
                    'discount_type': discount_type,
                    'surcharge_type': surcharge_type,
                    'adon_field_id': addon_field_id,
                    'adon_field_option_id': addon_option_id,
                    'feature_data': feature_data,
                    'price_data': price_data
                }
                features.append(_adon_feature_data_content)

    return features


async def best_match(input_str: str, data: List[Dict]) -> Optional[Dict]:
    """
    Performs fuzzy matching between the input string and a list of dictionaries, 
    returning the dictionary with the closest match based on 'name' or 'desc'.

    This function is useful when trying to find the best human-readable match
    for a feature code or identifier by comparing it against multiple descriptive fields.

    Args:
        input_str (str): The string to match against the entries in the list.
        data (List[Dict]): A list of dictionaries where each dictionary contains
                           'name' and 'desc' keys to be compared with the input.

    Returns:
        Optional[Dict]: The dictionary with the highest fuzzy match score based on 
                        'name' or 'desc', or None if no matches are found.
    """
    best_score = 0
    best_row = None

    for row in data:
        # Compare input_str with both 'name' and 'desc' fields using fuzzy matching
        score_name = fuzz.ratio(input_str.lower(), row["name"].lower())
        score_desc = fuzz.ratio(input_str.lower(), row["desc"].lower())
        
        # Use the higher of the two scores
        total_score = max(score_name, score_desc)

        # Update best match if current row has a higher score
        if total_score > best_score:
            best_score = total_score
            best_row = row

    return best_row


async def prepare_take_off_data(db, schedule_id):
    """
    Retrieves and prepares take-off schedule data for a given schedule ID.

    This function queries the ScheduleData table for all entries associated with
    the provided schedule ID and returns a dictionary mapping each entry's name
    to its corresponding data in dictionary format.

    Args:
        db: SQLAlchemy database session used to perform the query.
        schedule_id (int): The ID of the schedule for which data is to be fetched.

    Returns:
        dict: A dictionary where each key is a feature name and the value is the corresponding data.
    """
    schedule_info = db.query(Schedules).get(schedule_id)
    schedule_data_records = db.query(ScheduleData).filter(ScheduleData.schedule_id == schedule_id, ScheduleData.latest_data == True).all()

    schedule_data_record, _ = await build_schedule_data_dict(schedule_data_records, schedule_info.quantity)
    return schedule_data_record


async def compare_take_off_data(db, current_member_id, schedule_id, component_type, part_number=None):
    """
    Compares the existing take-off data of a schedule with the latest opening data and identifies differences.

    This function:
    1. Retrieves the saved `take_off_data` from the `Schedules` table for a given schedule ID.
    2. Filters the data based on the specified `component_type` and (if applicable) `part_number`.
    3. Fetches the latest prepared take-off data (opening data) for the same schedule.
    4. Compares the two datasets and identifies any differences.
    5. Logs changes by inserting records into the `opening_change_stats` (via `insert_changes`) if differences are found.

    Args:
        db: SQLAlchemy database session used to perform queries and insertions.
        current_member_id (int): ID of the user/member performing the comparison.
        schedule_id (int): ID of the schedule to fetch and compare data for.
        component_type (str): Type of the component (e.g., "DOOR") to filter and compare.
        part_number (Optional[str]): Specific part number to filter (required when component_type is "DOOR").

    Returns:
        List[dict]: A list of differences between the saved take-off data and the current opening data.
                    Each item in the list contains detailed information about what has changed.

    Side Effects:
        - Calls `insert_changes()` to log any detected differences to the database.
    """
    # print(db, current_member_id, schedule_id, component_type, part_number)
    schedule = db.query(Schedules).get(schedule_id)
    # print(component_type)
    if schedule and schedule.take_off_data:
        take_off_data = schedule.take_off_data
        if take_off_data:
            opening_data = await prepare_take_off_data(db, schedule_id)
            if opening_data:
                differences = await compare_schedule_data(take_off_data, opening_data, schedule.project_id, schedule_id, schedule.opening_number)    
                if differences:
                    # Create record based to 'opening_change_stats' on diffarence 
                    insert_changes(db, current_member_id, schedule, differences, component_type, part_number)
            return differences


def insert_changes(db, current_member_id, schedule_data, differences, component, part_number = None):
    """
    Inserts records into the `OpeningChangeStats` table to track changes between take-off data 
    and opening data for a given schedule.

    This function:
    1. Deletes existing change stats for the specified project, schedule, and component.
    2. Processes the `differences` dictionary to extract relevant fields.
    3. Prepares and inserts change entries into the database, capturing both old (take-off) 
       and new (opening) values.
    4. Supports filtering by part number when the component is a DOOR.

    Args:
        db (Session): SQLAlchemy database session.
        current_member_id (User): The user making the change, used for the `updated_by` field.
        schedule_data (Schedules): The schedule object containing context like project ID and opening number.
        differences (dict): Dictionary containing differences between take-off and opening data, 
                            keyed by field name. Each value should have `take_off_data` and `opening_data`.
        component (str): The component type (e.g., "DOOR", "FRAME", etc.).
        part_number (str, optional): The part number to filter by, used only when component is "DOOR".

    Returns:
        None

    Side Effects:
        - Deletes existing change records for the same schedule/component.
        - Inserts new rows into the `OpeningChangeStats` table.
        - Commits the transaction.

    Raises:
        Exception: Any database or runtime error encountered during execution is printed to the console.
    """
    try:
        project_id = schedule_data.project_id
        schedule_id = schedule_data.id
        opening_number = schedule_data.opening_number

        entries = []
        for field_data in differences:
            entry = {
                "project_id": project_id,
                "schedule_id": schedule_id,
                "opening_number": opening_number,
                "field_name": field_data.get("field_name", None),

                "take_off_feature_code": field_data.get("initial_schedule_feature_code", None),
                "take_off_option_code": field_data.get("initial_schedule_option_code", None),
                "take_off_value": field_data.get("initial_schedule_value", None),
                "take_off_total_amount": field_data.get("initial_schedule_total_amount", 0),
                "take_off_total_base_amount": field_data.get("initial_schedule_total_base_amount", 0),
                "take_off_total_sell_amount": field_data.get("initial_schedule_total_sell_amount", 0),
                "take_off_total_extended_sell_amount": field_data.get("initial_schedule_total_extended_sell_amount", 0),
                "take_off_quantity": field_data.get("initial_schedule_quantity", 1),
                "take_off_final_amount": field_data.get("initial_schedule_final_amount", 0),
                "take_off_final_base_amount": field_data.get("initial_schedule_final_base_amount", 0),
                "take_off_final_sell_amount": field_data.get("initial_schedule_final_sell_amount", 0),
                "take_off_final_extended_sell_amount": field_data.get("initial_schedule_final_extended_sell_amount", 0),
                "take_off_discount": field_data.get("initial_schedule_discount", 0),
                "take_off_discount_type": field_data.get("initial_schedule_discount_type", None),
                "take_off_surcharge": field_data.get("initial_schedule_surcharge", 0),
                "take_off_surcharge_type": field_data.get("initial_schedule_surcharge_type", None),
                "take_off_markup": field_data.get("initial_schedule_markup", 0),
                "take_off_margin": field_data.get("initial_schedule_margin", 0),

                "schedule_feature_code": field_data.get("current_schedule_feature_code", None),
                "schedule_option_code": field_data.get("current_schedule_option_code", None),
                "schedule_value": field_data.get("current_schedule_value", None),
                "schedule_total_amount": field_data.get("current_schedule_total_amount", 0),
                "schedule_total_base_amount": field_data.get("current_schedule_total_base_amount", 0),
                "schedule_total_sell_amount": field_data.get("current_schedule_total_sell_amount", 0),
                "schedule_total_extended_sell_amount": field_data.get("current_schedule_total_extended_sell_amount", 0),
                "schedule_quantity": field_data.get("current_schedule_quantity", 1),
                "schedule_final_amount": field_data.get("current_schedule_final_amount", 0),
                "schedule_final_base_amount": field_data.get("current_schedule_final_base_amount", 0),
                "schedule_final_sell_amount": field_data.get("current_schedule_final_sell_amount", 0),
                "schedule_final_extended_sell_amount": field_data.get("current_schedule_final_extended_sell_amount", 0),
                "schedule_discount": field_data.get("current_schedule_discount", 0),
                "schedule_discount_type": field_data.get("current_schedule_discount_type", None),
                "schedule_surcharge": field_data.get("current_schedule_surcharge", 0),
                "schedule_surcharge_type": field_data.get("current_schedule_surcharge_type", None),
                "schedule_markup": field_data.get("current_schedule_markup", 0),
                "schedule_margin": field_data.get("current_schedule_margin", 0),

                "component": field_data.get("component", component),
                "is_manual": bool(field_data.get("is_manual", False)),
                "is_adon_field": bool(field_data.get("is_adon_field", False)),
                "has_price_dependancy": bool(field_data.get("has_price_dependancy", False)),
                "part_number": field_data.get("part_number", None),
                "updated_by": current_member_id.id,
                "updated_at": datetime.now()
            }

            entries.append(entry)
        if entries:
            query = db.query(OpeningChangeStats).filter(
                OpeningChangeStats.project_id == project_id,
                OpeningChangeStats.schedule_id == schedule_id,
                OpeningChangeStats.component.in_([COMPONENT_TYPE.DOOR.value, COMPONENT_TYPE.FRAME.value]),
            )
            query.delete(synchronize_session=False)
            db.flush()
            db.bulk_insert_mappings(OpeningChangeStats, entries)
            db.commit()

    except Exception as e:
        print(str(e))


async def compare_hardware_data(db, current_member_id, schedule_id):
    """
    Compares the take-off hardware data with the schedule hardware data for a given schedule,
    identifies differences, and delegates to `hardware_diff_lists` for further processing.

    This function:
    - Retrieves the schedule from the database.
    - Extracts and structures the take-off hardware data.
    - Calls `prepare_hardware_data` to get the current hardware configuration.
    - Normalizes both datasets for comparison.
    - Passes the structured data to `hardware_diff_lists` to find and record the differences.

    Args:
        db (Session): SQLAlchemy database session.
        current_member_id (User): The current user initiating the comparison, used for tracking changes.
        schedule_id (int): ID of the schedule to compare.

    Returns:
        Any: The result from the `hardware_diff_lists` function, which typically records the differences 
        and may return a summary or confirmation of the changes applied.

    Raises:
        None explicitly, but may propagate exceptions from the database or `prepare_hardware_data`/`hardware_diff_lists`.

    Notes:
        - This function assumes `take_off_hardware_data` exists in the schedule.
        - Both take-off and schedule hardware data are normalized to a consistent format before comparison.
    """
    schedule = db.query(Schedules).get(schedule_id)
    differences = None
    # print(component_type)
    if schedule and schedule.take_off_hardware_data:
        take_off_hardware_data = schedule.take_off_hardware_data
        project_id = schedule.project_id
        opening_number = schedule.opening_number
        if take_off_hardware_data:
            schedule_hardware_data = await prepare_hardware_data(db, schedule_id)
            if schedule_hardware_data:
                take_off_hardware_data = take_off_hardware_data.get("fields", {}) if take_off_hardware_data else {}
                schedule_hardware_data = schedule_hardware_data.get("fields", {}) if schedule_hardware_data else {}
                differences = await compare_schedule_hardware_data(take_off_hardware_data, schedule_hardware_data, project_id, schedule_id, opening_number)
                if differences:
                    response = insert_hardware_diff_to_db(db, differences, project_id, schedule_id, opening_number,  current_member_id)

    return differences


async def prepare_hardware_data(db, schedule_id):
    """
    Retrieves and prepares detailed hardware material data associated with a given schedule ID.

    This function queries the `ScheduleOpeningHardwareMaterials` table to get hardware materials for a
    specific schedule. It then extracts and formats related data from associated `OpeningHardwareMaterial`
    entries into a structured dictionary, including calculated final values based on quantity.

    Args:
        db (Session): SQLAlchemy database session.
        schedule_id (int): ID of the schedule for which hardware data needs to be retrieved.

    Returns:
        dict: A dictionary where each key is a hardware material's short code and the value is a nested
              dictionary containing comprehensive information about that hardware item, including pricing,
              discounts, surcharges, quantity, and calculated totals.

    Notes:
        - Values like `discount_type` and `surcharge_type` are safely extracted as string representations.
        - Multiplicative fields like `final_amount` are calculated using the quantity from the schedule.
        - All related IDs are converted to string for consistency.
        - Designed to be used as part of hardware comparison operations (e.g. in `compare_hardware_data`).
    """
    schedule_hardware_data = db.query(ScheduleOpeningHardwareMaterials).filter(ScheduleOpeningHardwareMaterials.schedule_id == schedule_id).all()
    hardware_record_dict = { hr.opening_hardware_material_id: hr.quantity for hr in schedule_hardware_data}
    hardware_record = await build_schedule_hardware_dict(db, hardware_record_dict, schedule_id)
    return hardware_record


def insert_hardware_diff_to_db(db, diff_result, project_id, schedule_id, opening_number,  current_member_id):
    """
    Inserts hardware difference data between take-off and schedule into the OpeningChangeStats table.

    This function compares hardware data from the take-off sheet and schedule, identifies discrepancies,
    and records them in the database. It removes any existing records for the same project, schedule, 
    and component ("HARDWARE") before inserting updated difference records.

    Args:
        db (Session): SQLAlchemy database session.
        diff_result (dict): Dictionary containing hardware data differences grouped by short_code.
        project_id (int): ID of the current project.
        schedule_id (int): ID of the schedule associated with the hardware.
        opening_number (str): The opening number this difference data belongs to.
        current_member_id (User): The user making the changes, used for tracking updates.

    Returns:
        list: A list of dictionaries representing the data inserted into OpeningChangeStats.

    Raises:
        None explicitly. Any exceptions during DB operations should be handled by the calling context.
    """
    response = []
    for field_data in diff_result:
        data = {
            'project_id':  project_id,
            'schedule_id': schedule_id,
            'opening_number': opening_number,
            "field_name": field_data.get("field_name", None),

            "take_off_feature_code": field_data.get("initial_schedule_feature_code", None),
            "take_off_option_code": field_data.get("initial_schedule_option_code", None),
            "take_off_value": field_data.get("initial_schedule_value", None),
            "take_off_total_amount": field_data.get("initial_schedule_total_amount", 0),
            "take_off_total_base_amount": field_data.get("initial_schedule_total_base_amount", 0),
            "take_off_total_sell_amount": field_data.get("initial_schedule_total_sell_amount", 0),
            "take_off_total_extended_sell_amount": field_data.get("initial_schedule_total_extended_sell_amount", 0),
            "take_off_quantity": field_data.get("initial_schedule_quantity", 1),
            "take_off_final_amount": field_data.get("initial_schedule_final_amount", 0),
            "take_off_final_base_amount": field_data.get("initial_schedule_final_base_amount", 0),
            "take_off_final_sell_amount": field_data.get("initial_schedule_final_sell_amount", 0),
            "take_off_final_extended_sell_amount": field_data.get("initial_schedule_final_extended_sell_amount", 0),
            "take_off_discount": field_data.get("initial_schedule_discount", 0),
            "take_off_discount_type": field_data.get("initial_schedule_discount_type", "PERCENTAGE"),
            "take_off_surcharge": field_data.get("initial_schedule_surcharge", 0),
            "take_off_surcharge_type": field_data.get("initial_schedule_surcharge_type", "PERCENTAGE"),
            "take_off_markup": field_data.get("initial_schedule_markup", 0),
            "take_off_margin": field_data.get("initial_schedule_margin", 0),

            "schedule_feature_code": field_data.get("current_schedule_feature_code", None),
            "schedule_option_code": field_data.get("current_schedule_option_code", None),
            "schedule_value": field_data.get("current_schedule_value", None),
            "schedule_total_amount": field_data.get("current_schedule_total_amount", 0),
            "schedule_total_base_amount": field_data.get("current_schedule_total_base_amount", 0),
            "schedule_total_sell_amount": field_data.get("current_schedule_total_sell_amount", 0),
            "schedule_total_extended_sell_amount": field_data.get("current_schedule_total_extended_sell_amount", 0),
            "schedule_quantity": field_data.get("current_schedule_quantity", 1),
            "schedule_final_amount": field_data.get("current_schedule_final_amount", 0),
            "schedule_final_base_amount": field_data.get("current_schedule_final_base_amount", 0),
            "schedule_final_sell_amount": field_data.get("current_schedule_final_sell_amount", 0),
            "schedule_final_extended_sell_amount": field_data.get("current_schedule_final_extended_sell_amount", 0),
            "schedule_discount": field_data.get("current_schedule_discount", 0),
            "schedule_discount_type": field_data.get("current_schedule_discount_type", "PERCENTAGE"),
            "schedule_surcharge": field_data.get("current_schedule_surcharge", 0),
            "schedule_surcharge_type": field_data.get("current_schedule_surcharge_type", "PERCENTAGE"),
            "schedule_markup": field_data.get("current_schedule_markup", 0),
            "schedule_margin": field_data.get("current_schedule_margin", 0),

            'component': "HARDWARE",
            "is_manual": bool(field_data.get("is_manual", False)),
            'is_adon_field': bool(field_data.get("is_adon_field", False)),
            'has_price_dependancy': bool(field_data.get("has_price_dependancy", False)),
            'short_code': field_data.get("field_name", None),
            'updated_by': current_member_id.id,
            'updated_at': datetime.now()
        }

        response.append(data)
    if response:
        query = db.query(OpeningChangeStats).filter(
                OpeningChangeStats.project_id == project_id,
                OpeningChangeStats.schedule_id == schedule_id,
                OpeningChangeStats.component == "HARDWARE",
            )
        query.delete(synchronize_session=False)
        db.flush()
        db.bulk_insert_mappings(OpeningChangeStats, response)
        db.commit()
    return response