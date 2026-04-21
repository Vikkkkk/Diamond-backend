"""
This file contains all the database operations related to opening door/frame materials.
"""
from loguru import logger
from models.opening_door_frame_materials import OpeningDoorFrameMaterials
from models.raw_materials import RawMaterials
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from sqlalchemy import func,case
from sqlalchemy.orm import Session


async def is_opening_door_frame_short_code_exists(project_id: str, short_code: str, db: Session, exclude_id=None):
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
            OpeningDoorFrameMaterials.short_code == short_code,
            OpeningDoorFrameMaterials.project_id == project_id,
            OpeningDoorFrameMaterials.is_deleted == False
        ]
        if exclude_id:
            filter_conditions.append(OpeningDoorFrameMaterials.id != exclude_id)

        # Execute the query
        project_short_code_exist = (
            db.query(OpeningDoorFrameMaterials)
            .filter(*filter_conditions)
            .all()
        )
        # Check if any matching records are found
        is_exists = len(project_short_code_exist) > 0
        
        return is_exists 
    except Exception as error:
        logger.exception(f"is_opening_door_frame_short_code_exists:: An unexpected error occurred: {error}")
        raise error


def add_estimation_breakups_to_opening_door_frame(db, opening_door_frame_material_data):
    """
    Add estimation breakups to the opening door/frame material based on existing materials in the same project.
    Sets the markup, margin, discount, surcharge from existing project material in same project.

    Args:
        db: The database connection.
        opening_door_frame_material_data: The data related to the opening door/frame material.

    Returns:
        No return value. However, it updates the `opening_door_frame_material_data`
    """
    project_id = opening_door_frame_material_data['project_id']
    manufacturer_id = opening_door_frame_material_data.get('manufacturer_id')
    brand_id = opening_door_frame_material_data.get('brand_id')
    material_type = opening_door_frame_material_data.get('material_type', 'DOOR')
    raw_material_code = opening_door_frame_material_data.get('raw_material_code', None)
    
    raw_material = None
    if raw_material_code:
        raw_material = (
            db.query(RawMaterials.id)
            .filter(RawMaterials.code == raw_material_code)
        ).first()
    
    try:
        if manufacturer_id is None:
            opening_door_frame_material_data['discount_type'] = 'PERCENTAGE'
            opening_door_frame_material_data['discount'] = 0.0
        else:
            # Try to fetch another door/frame material with the same brand_id & manufacturer_id
            another_door_frame_material = (
                db.query(OpeningDoorFrameMaterials)
                .filter(
                    OpeningDoorFrameMaterials.is_deleted == False,
                    OpeningDoorFrameMaterials.project_id == project_id,
                    OpeningDoorFrameMaterials.manufacturer_id == manufacturer_id,
                    OpeningDoorFrameMaterials.brand_id == brand_id,
                    OpeningDoorFrameMaterials.material_type == material_type
                ).first()
            )
            
            if another_door_frame_material is not None:
                # Update the breakdown charges from existing material
                opening_door_frame_material_data['discount_type'] = another_door_frame_material.discount_type.value if another_door_frame_material.discount_type else another_door_frame_material.discount_type
                opening_door_frame_material_data['discount'] = another_door_frame_material.discount
                opening_door_frame_material_data['margin'] = another_door_frame_material.margin
                opening_door_frame_material_data['markup'] = another_door_frame_material.markup
                opening_door_frame_material_data['surcharge_type'] = another_door_frame_material.surcharge_type.value if another_door_frame_material.surcharge_type else another_door_frame_material.surcharge_type
                opening_door_frame_material_data['surcharge'] = another_door_frame_material.surcharge
            else:
                opening_door_frame_material_data['margin'] = 0.0
                opening_door_frame_material_data['markup'] = 0.0
                opening_door_frame_material_data['surcharge_type'] = 'PERCENTAGE'
                opening_door_frame_material_data['surcharge'] = 0.0
                
                # Set the default manufacturer discount if available
                if raw_material:
                    default_discount_result = (
                        db.query(RawMaterialCatalogMapping.discount_percentage)
                        .filter(
                            RawMaterialCatalogMapping.raw_material_id == raw_material.id,
                            RawMaterialCatalogMapping.manufacturer_id == manufacturer_id,
                            RawMaterialCatalogMapping.brand_id == brand_id,
                        )
                        .first()
                    )
                    if default_discount_result:
                        [default_discount] = default_discount_result
                        opening_door_frame_material_data['discount_type'] = 'PERCENTAGE'
                        opening_door_frame_material_data['discount'] = default_discount
                    else:
                        opening_door_frame_material_data['discount_type'] = 'PERCENTAGE'
                        opening_door_frame_material_data['discount'] = 0.0
                else:
                    opening_door_frame_material_data['discount_type'] = 'PERCENTAGE'
                    opening_door_frame_material_data['discount'] = 0.0
                    
        logger.info(f"opening_door_frame_material_data:: {opening_door_frame_material_data}")
        return
    except Exception as e:
        logger.exception(f"add_estimation_breakups_to_opening_door_frame:: {e}")
        raise e


async def update_opening_door_frame_material_charges(db, opening_door_frame_material_id, return_updated_values=False):
    """
    A function to update the door/frame material's `total_base_amount`, `total_sell_amount` based on different discount types.
    
    Parameters:
    - db: the database connection object
    - opening_door_frame_material_id: the unique identifier of the opening door/frame material
    - return_updated_values: if True, returns the updated values
    
    Returns:
    Dictionary with updated values if return_updated_values is True, otherwise None.
    """
    try:
        # When Discount is Percentage, discount amount = total_amount * discount
        percentage_discount = func.round(
            func.ifnull(OpeningDoorFrameMaterials.total_amount * OpeningDoorFrameMaterials.discount, 0), 2
        )
        
        # When Discount is Multiplier, discount amount = total_amount * discount / 100
        multiplier_discount = func.round(
            func.ifnull(OpeningDoorFrameMaterials.total_amount * OpeningDoorFrameMaterials.discount / 100, 0), 2
        )
        
        # Case statement to determine discount amount based on discount type
        discount_amount = func.coalesce(
            case(
                (OpeningDoorFrameMaterials.discount_type == 'PERCENTAGE', percentage_discount),
                (OpeningDoorFrameMaterials.discount_type == 'MULTIPLIER', multiplier_discount),
                else_=0
            ),
            0
        )
        
        # Calculate base amount: total_amount - discount_amount
        base_amount = OpeningDoorFrameMaterials.total_amount - discount_amount
        
        # Calculate markup amount
        markup_amount = func.round(
            func.ifnull(base_amount * OpeningDoorFrameMaterials.markup, 0), 2
        )
        
        # Calculate margin amount
        margin_amount = func.round(
            func.ifnull(base_amount * OpeningDoorFrameMaterials.margin, 0), 2
        )
        
        # Calculate sell amount: base_amount + markup_amount + margin_amount
        sell_amount = base_amount + markup_amount + margin_amount
        
        # Calculate surcharge
        percentage_surcharge = func.round(
            func.ifnull(sell_amount * OpeningDoorFrameMaterials.surcharge, 0), 2
        )
        
        multiplier_surcharge = func.round(
            func.ifnull(sell_amount * OpeningDoorFrameMaterials.surcharge / 100, 0), 2
        )
        
        surcharge_amount = func.coalesce(
            case(
                (OpeningDoorFrameMaterials.surcharge_type == 'PERCENTAGE', percentage_surcharge),
                (OpeningDoorFrameMaterials.surcharge_type == 'MULTIPLIER', multiplier_surcharge),
                else_=0
            ),
            0
        )
        
        # Final extended sell amount
        extended_sell_amount = sell_amount + surcharge_amount
        
        # Update the material with calculated values
        update_query = (
            db.query(OpeningDoorFrameMaterials)
            .filter(OpeningDoorFrameMaterials.id == opening_door_frame_material_id)
            .update(
                {
                    'total_base_amount': base_amount,
                    'total_sell_amount': sell_amount,
                    'total_extended_sell_amount': extended_sell_amount
                },
                synchronize_session=False
            )
        )
        
        db.flush()
        
        if return_updated_values:
            # Fetch updated values
            updated_material = db.query(OpeningDoorFrameMaterials).filter(
                OpeningDoorFrameMaterials.id == opening_door_frame_material_id
            ).first()
            
            if updated_material:
                return {
                    'total_base_amount': updated_material.total_base_amount,
                    'total_sell_amount': updated_material.total_sell_amount,
                    'total_extended_sell_amount': updated_material.total_extended_sell_amount
                }
        
        return None
        
    except Exception as error:
        logger.exception(f"update_opening_door_frame_material_charges:: An unexpected error occurred: {error}")
        raise error
