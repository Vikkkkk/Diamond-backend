"""
This file contains all the database operations related to materials.
"""
from typing import List
from loguru import logger
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.project_take_off_sheet_sections import ProjectTakeOffSheetSections
from models.opening_schedules import OpeningSchedules
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.sections import Sections
from models.section_raw_materials import SectionRawMaterials
from models.raw_materials import RawMaterials
from models.project_materials import ProjectMaterials
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.opening_hardware_materials import OpeningHardwareMaterials
from utils.description_generartor import get_door_description, get_frame_description
from sqlalchemy import or_, and_, update, func, text, case
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from utils.request_handler import call_get_api



async def is_opening_hw_short_code_exists(project_id: str, short_code: str, db: Session, exclude_id=None):
    """**Summary:**
    This module is responsible for checking if the input short code already exists or not in the input project.

    **Args:**
    - project_id (str): project id for which we need to check the existence.
    - short_code (str): short code for which we need to check the existence.
    - db (Session): The database session.
    - exclude_id (str, optional): ID of the record to exclude from the check. Defaults to None.

    **Return:**
    - is_exists (bool): return True if already exists otherwise False.
    """
    try:
        # Define the filter conditions
        filter_conditions = [
            OpeningHardwareMaterials.short_code == short_code,
            OpeningHardwareMaterials.project_id == project_id,
            OpeningHardwareMaterials.is_deleted == False
        ]
        if exclude_id:
            filter_conditions.append(OpeningHardwareMaterials.id != exclude_id)

        # Execute the query
        project_short_code_exist = (
            db.query(OpeningHardwareMaterials)
            .filter(*filter_conditions)
            .all()
        )
        # Check if any matching records are found
        is_exists = len(project_short_code_exist) > 0
        
        return is_exists 
    except Exception as error:
        logger.exception(f"is_opening_hw_short_code_exists:: An unexpected error occurred: {error}")
        raise error

def add_estimation_breakups_to_opening_hardware(db, opening_hardware_material_data):
    """
    Add estimation breakups to the project based on the provided project material data.
    Sets the markup, margin, discount, surcharge from existing project material in same project.

    Args:
        db: The database connection.
        project_material_data: The data related to the project material.

    Returns:
        No return value. However, it updates the `project_material_data`
    """
    project_id = opening_hardware_material_data['project_id']
    manufacturer_id = opening_hardware_material_data['manufacturer_id'] if "manufacturer_id" in opening_hardware_material_data else None
    brand_id = opening_hardware_material_data['brand_id'] if "brand_id" in opening_hardware_material_data else None
    # fetch raw_material with code 'HWD' which stands for Hardware
    raw_material_hwd = (
        db.query(RawMaterials.id)
        .filter(RawMaterials.code == 'HWD')
    ).first()
    try:
        if manufacturer_id is None:
            opening_hardware_material_data['discount_type'] = 'PERCENTAGE'
            opening_hardware_material_data['discount'] = 0.0
        else:
            # We first try to fetch the project_material with the same brand_id & manufacturer_id
            another_opening_hw_material = (
                db.query(OpeningHardwareMaterials)
                .filter(
                    OpeningHardwareMaterials.is_deleted == False,
                    OpeningHardwareMaterials.project_id == project_id,
                    OpeningHardwareMaterials.manufacturer_id == manufacturer_id,
                    OpeningHardwareMaterials.brand_id == brand_id
                ).first()
            )
            
            if another_opening_hw_material is not None:
                # Let's update the breakdown charges
                opening_hardware_material_data['discount_type'] = another_opening_hw_material.discount_type.value if another_opening_hw_material.discount_type else another_opening_hw_material.discount_type
                opening_hardware_material_data['discount'] = another_opening_hw_material.discount
                opening_hardware_material_data['margin'] = another_opening_hw_material.margin
                opening_hardware_material_data['markup'] = another_opening_hw_material.markup
                opening_hardware_material_data['surcharge_type'] = another_opening_hw_material.surcharge_type.value if another_opening_hw_material.surcharge_type else another_opening_hw_material.surcharge_type
                opening_hardware_material_data['surcharge'] = another_opening_hw_material.surcharge
            else:
                opening_hardware_material_data['margin'] = 0.0
                opening_hardware_material_data['markup'] = 0.0
                opening_hardware_material_data['surcharge_type'] = 'PERCENTAGE'
                opening_hardware_material_data['surcharge'] = 0.0
                # We need to set the default manufacturer discount, if no estimation discount was applied
                [default_discount] = (
                    db.query(RawMaterialCatalogMapping.discount_percentage)
                    .filter(
                        RawMaterialCatalogMapping.raw_material_id == raw_material_hwd.id,
                        RawMaterialCatalogMapping.manufacturer_id == manufacturer_id,
                        RawMaterialCatalogMapping.brand_id == brand_id,
                    )
                    .first()
                )
                if default_discount is not None:
                    opening_hardware_material_data['discount_type'] = 'PERCENTAGE'
                    opening_hardware_material_data['discount'] = default_discount
        print("opening_hardware_material_data:: ",opening_hardware_material_data)
        return
    except Exception as e:
        print("add_estimation_breakups_to_opening_hardware:: ",e)
        raise e




async def update_opening_hw_material_charges(db, opening_hw_material_id, return_updated_values=False):
    """
    A function to update the material's `total_base_amount`, `total_sell_amount` based on different discount types.
    
    Parameters:
    - db: the database connection object
    - opening_hw_material_id: the unique identifier of the opening hardware material
    
    Returns:
    No explicit return value, but updates the material charges in the database.
    """
    try:
        # When Discount is Percentage, then DiscountAmount =
        # IFNULL(total_amount * discount, 0))
        percentage_discount = func.round(
            func.ifnull(OpeningHardwareMaterials.total_amount * OpeningHardwareMaterials.discount, 0)    
        , 2)
 
        # When Discount is Multiplier, then DiscountAmount =
        # IFNULL(total_amount * (1 - discount), 0))
        multiplier_discount = func.round(
            func.ifnull(OpeningHardwareMaterials.total_amount * (1 - OpeningHardwareMaterials.discount), 0)
        , 2)
 
        result = db.execute(
        update(OpeningHardwareMaterials).where(
            OpeningHardwareMaterials.id == opening_hw_material_id,
            OpeningHardwareMaterials.is_deleted == False
        ).values(
            # we will calculate the corresponding total_base_amount
            total_base_amount = case(
                    (OpeningHardwareMaterials.discount_type == "PERCENTAGE", OpeningHardwareMaterials.total_amount - percentage_discount),
                    (OpeningHardwareMaterials.discount_type == "MULTIPLIER", OpeningHardwareMaterials.total_amount - multiplier_discount),
                    (OpeningHardwareMaterials.discount_type == None, OpeningHardwareMaterials.total_amount),
                )
            )
        )
        
        # Now update total_sell_amount based on the updated total_base_amount
        result = db.execute(
            update(OpeningHardwareMaterials).where(
                OpeningHardwareMaterials.id == opening_hw_material_id,
                OpeningHardwareMaterials.is_deleted == False
            ).values(
                # We Know that:
                # SellPrice = (TotalAmount - DiscountAmount) + MarkUpAmount
                #
                # Note: markup is stored as percentage in float format. eg: 25% is stored as 0.25
                # Therefore we can use the formula `BaseAmount * (1 + markup)` which is equivalent to `BaseAmount + (BaseAmount * markup)`
                total_sell_amount = func.round(OpeningHardwareMaterials.total_base_amount * (1 + func.ifnull(OpeningHardwareMaterials.markup, 0)), 2)
            )
        )
        # When surcharge is Percentage, then SurchargeAmount =
        # IFNULL(total_sell_amount * surcharge, 0))
        percentage_surcharge = func.round(
            func.ifnull(OpeningHardwareMaterials.total_sell_amount * OpeningHardwareMaterials.surcharge, 0)    
        , 2)

        # When surcharge is Multiplier, then SurchargeAmount =
        # IFNULL(total_sell_amount * surcharge, 0))
        multiplier_surcharge = func.round(
            func.ifnull(OpeningHardwareMaterials.total_sell_amount * OpeningHardwareMaterials.surcharge, 0)
        , 2)

        # Now update total_extended_sell_amount based on the updated total_sell_amount
        result = db.execute(
            update(OpeningHardwareMaterials).where(
                OpeningHardwareMaterials.id == opening_hw_material_id,
                OpeningHardwareMaterials.is_deleted == False
            ).values(
                # we will calculate the corresponding total_extended_sell_amount
                total_extended_sell_amount = case(
                    (OpeningHardwareMaterials.surcharge_type == "PERCENTAGE", OpeningHardwareMaterials.total_sell_amount + percentage_surcharge),
                    (OpeningHardwareMaterials.surcharge_type == "MULTIPLIER", OpeningHardwareMaterials.total_sell_amount + multiplier_surcharge),
                    (OpeningHardwareMaterials.surcharge_type == None, OpeningHardwareMaterials.total_sell_amount),
                )
            )
        )

        if not return_updated_values:
            return
        else:
            if result.rowcount == 0:
                return None
            else:
                new_values = (
                    db.query(OpeningHardwareMaterials.total_base_amount, OpeningHardwareMaterials.total_sell_amount, OpeningHardwareMaterials.total_extended_sell_amount)
                    .filter(OpeningHardwareMaterials.id == opening_hw_material_id)
                    .first()
                )
                
                return {
                    "total_base_amount": new_values[0],
                    "total_sell_amount": new_values[1],
                    "total_extended_sell_amount": new_values[2],
                }
    except Exception as error:
        # Handle the error appropriately
        print("update_opening_hw_material_charges:: An error occurred:", error)
        raise error
    