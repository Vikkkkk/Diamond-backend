"""
This file contains all commonly used repositories.
"""
from loguru import logger
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_charges import ProjectTakeOffSheetCharges
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.project_materials import ProjectMaterials
from models.opening_hardware_materials import OpeningHardwareMaterials
from models.raw_materials import RawMaterials
from sqlalchemy import or_, and_, update, func, text, case

async def get_take_off_sheet_section_price(take_off_sheet_section_id, db):
    """**Summary:**
    This module is responsible for getting all of the items for an take off sheet area.

    **Args:**
    - take_off_sheet_section_id (str): project take off sheet section id.
    - `db` (Session): The database session.

    **Return:**
    - `total_amount` (float): total calculated charge of a project take off sheet section.
    """
    try:
        item_data = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_id == take_off_sheet_section_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .order_by(ProjectTakeOffSheetSectionAreaItems.created_at.asc())
            .all()
        )
        total_amount = 0.0
        for data in item_data:
            total_amount += data.gross_amount
        return total_amount
    except Exception as error:
        logger.exception(f"get_take_off_sheet_section_price:: An unexpected error occurred: {error}")
        raise error
    

async def get_raw_materialwise_total(db, project_id):
    """
    Asynchronous function to retrieve the total raw material amounts for a specific project.
    
    Args:
        db: The database session.
        project_id: The ID of the project for which to retrieve raw material totals.
        
    Returns:
        A dictionary containing the raw material data and a status message.
    """
    try:
        # Query all RawMaterials along with their summed total amount from ProjectMaterials
        # Perform a left outer join to include all RawMaterials even if there are no corresponding ProjectMaterials
        # Filter to include ProjectMaterials that belong to a specific project and are not deleted
        # Group the results by RawMaterials.id to sum up the total amount for each RawMaterial
        raw_material_items = (
            db.query(RawMaterials, func.ifnull(func.sum(ProjectMaterials.total_amount), 0))
            .join(ProjectMaterials, isouter=True)
            .filter(
                or_(
                    ProjectMaterials.id == None,  # if ProjectMaterials.id is NULL (i.e., no corresponding ProjectMaterial found)
                    and_(  # if there is a corresponding ProjectMaterial
                        ProjectMaterials.is_deleted == False,  # then filter by project_id and is_active
                        ProjectMaterials.project_id == project_id,
                        ProjectMaterials.is_active == True
                    )
                )
            )
            .group_by(RawMaterials.id)
            .all()
        )
        data = []
        # loop through all raw materials & add the 'total_amount' property to each one of them
        for row in raw_material_items:
            raw_material_item, total_amount = row
            resp = raw_material_item.to_dict
            resp["total_amount"] = total_amount
            data.append(resp)
        return data
    except Exception as error:
        # Handle the error appropriately
        print("An error occurred:", error)
        raise error



def add_estimation_breakups_to_project(db, project_material_data):
    """
    Add estimation breakups to the project based on the provided project material data.
    Sets the markup, margin, discount, surcharge from existing project material in same project.

    Args:
        db: The database connection.
        project_material_data: The data related to the project material.

    Returns:
        No return value. However, it updates the `project_material_data`
    """
    project_id = project_material_data['project_id']
    raw_material_id = project_material_data['raw_material_id']
    manufacturer_id = project_material_data['manufacturer_id'] if "manufacturer_id" in project_material_data else None
    brand_id = project_material_data['brand_id'] if "brand_id" in project_material_data else None
    try:
        query_text = """
            SELECT 
                COALESCE(pm_with_manufacturer.margin, pm.margin) AS margin,
                COALESCE(pm_with_manufacturer.markup, pm.markup) AS markup,
                COALESCE(pm_with_manufacturer.surcharge_type, pm.surcharge_type) AS surcharge_type,
                COALESCE(pm_with_manufacturer.surcharge, pm.surcharge) AS surcharge,
                pm_with_manufacturer.discount_type,
                pm_with_manufacturer.discount_is_basic,
                pm_with_manufacturer.discount,
                rcm.discount_percentage AS default_discount,
                CASE 
                    WHEN pm_with_manufacturer.id IS NOT NULL THEN 1
                    ELSE 0
                END AS found_with_manufacturer
            FROM raw_materials rm
            LEFT JOIN project_materials pm_with_manufacturer ON 
                pm_with_manufacturer.project_id = :project_id
                AND pm_with_manufacturer.raw_material_id = :raw_material_id
                AND pm_with_manufacturer.manufacturer_id = :manufacturer_id
                AND pm_with_manufacturer.is_active = TRUE
                AND pm_with_manufacturer.is_deleted = FALSE
            LEFT JOIN project_materials pm ON 
                pm.project_id = :project_id
                AND pm.raw_material_id = :raw_material_id
                AND pm.is_active = TRUE
                AND pm.is_deleted = FALSE
            LEFT JOIN raw_material_catalog_mapping rcm ON 
                rcm.raw_material_id = :raw_material_id
                AND rcm.manufacturer_id = :manufacturer_id
                AND (
                    (:brand_id IS NULL AND rcm.brand_id IS NULL) OR rcm.brand_id = :brand_id
                )
            LIMIT 1
        """
        result = db.execute(
            text(query_text), 
            {
                "project_id": project_id,
                "raw_material_id": raw_material_id,
                "manufacturer_id": manufacturer_id,
                "brand_id": brand_id
            }
        ).fetchone()
        if not project_material_data.get('manufacturer_id'):
            project_material_data.update({
                'discount_is_basic': 1,
                'discount_type': 'PERCENTAGE',
                'discount': 0.0
            })
        else:
            if result:
                project_material_data['margin'] = result.margin
                project_material_data['markup'] = result.markup
                project_material_data['surcharge_type'] = result.surcharge_type
                project_material_data['surcharge'] = result.surcharge

                if result.found_with_manufacturer:
                    project_material_data['discount_type'] = result.discount_type
                    project_material_data['discount_is_basic'] = result.discount_is_basic
                    project_material_data['discount'] = result.discount
                elif result.default_discount is not None:
                    project_material_data['discount_is_basic'] = 1
                    project_material_data['discount_type'] = 'PERCENTAGE'
                    project_material_data['discount'] = result.default_discount
        return
    except Exception as e:
        print("add_estimation_breakups_to_project:: ",e)
        raise e




async def get_total_adon_price(db, take_off_sheet_id):
    try:
        sheet_data = (
            db.query(ProjectTakeOffSheets)
            .filter(ProjectTakeOffSheets.id == take_off_sheet_id)
        ).first()
        total_extended_sell_amount = sheet_data.total_extended_sell_amount
        operations = {
            'FLAT': lambda x, y: y,
            'MULTIPLIER': lambda x, y: (x * y),
            'PERCENTAGE': lambda x, y: (x * (y / 100))
        }
        adon_price_data = (
            db.query(ProjectTakeOffSheetCharges)
            .filter(
                ProjectTakeOffSheetCharges.project_take_off_sheet_id == take_off_sheet_id,
                ProjectTakeOffSheetCharges.is_active == True
            )
            .all()
        )
        total_misc_price = 0.0
        for adon_price in adon_price_data:
            total_misc_price += operations[adon_price.multiplier_type.value](total_extended_sell_amount or 0, adon_price.amount or 0)
        return total_misc_price
    except Exception as e:
        print("get_total_adon_price:: error - ",e)
        raise e

