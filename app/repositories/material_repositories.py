"""
This file contains all the database operations related to materials.
"""
from typing import List
from loguru import logger
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
from models.brands import Brands
from models.manufacturers import Manufacturers
from utils.description_generartor import get_door_description, get_frame_description,get_hardware_description
from sqlalchemy import or_, and_, update, func, text, case
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from utils.request_handler import call_get_api

async def get_material_type(db, raw_material_code):
    try:
        
        raw_material_data = (
            db.query(SectionRawMaterials)
            .join(RawMaterials, RawMaterials.id == SectionRawMaterials.raw_material_id)
            .join(Sections, Sections.id == SectionRawMaterials.section_id)
            .filter(RawMaterials.code == raw_material_code, Sections.code != "MXD")
            .first()
        )
        if not raw_material_data:
            category = None
        else:
            section_data = raw_material_data.section
            raw_material = raw_material_data.raw_material
            if section_data.is_hwd:
                category = "HARDWARE"
            elif section_data.is_door_frame:
                category = "DOOR" if "door" in raw_material.name.lower() else "FRAME"
            else:
                category = "OTHER"
        return category
    except Exception as error:
        print("error:: ",error)
        raise error
    
async def get_description(db, adon_fields, series, material_code, base_feature, adon_feature):
    try:
        print(">>>>>>>>>>>>>>>>>>hhh", adon_fields)
        for field, option in adon_fields.items():
            option_data = (
                db.query(AdonOpeningFieldOptions)
                .get(option)
            )
            adon_fields[field] = option_data.name
        
        desc = None
        print("material_code:: ",material_code)
        if material_code not in ["INST","HWD"]:
            raw_mat_data = (
                db.query(RawMaterials)
                .filter(
                    RawMaterials.code == material_code
                )
                .first()
            )

            if "door" in raw_mat_data.name.lower():
                desc = await get_door_description(adon_fields, raw_mat_data.name, series, base_feature, adon_feature)
            if "frame" in raw_mat_data.name.lower():
                desc = await get_frame_description(adon_fields, raw_mat_data.name, series, base_feature, adon_feature)
        elif material_code in ["HWD"]:
            desc = await get_hardware_description(series, base_feature, adon_feature)

        return desc
    except Exception as error:
        print("error:: ",error)
        raise error

async def update_material_charges(db, project_material_id, return_updated_values=False):
    """
    A function to update the material's `total_base_amount`, `total_sell_amount` based on different discount types.
    
    Parameters:
    - db: the database connection object
    - project_material_id: the unique identifier of the project material
    
    Returns:
    No explicit return value, but updates the material charges in the database.
    """
    try:
        
        query_text = f"""
            SELECT 
                id,
                total_amount,
                discount,
                discount_type,
                markup,
                surcharge,
                surcharge_type,

                -- Calculated discount amount
                ROUND(CASE 
                    WHEN discount_type = 'PERCENTAGE' THEN COALESCE(total_amount * discount, 0)
                    WHEN discount_type = 'MULTIPLIER' THEN COALESCE(total_amount * (1 - discount), 0)
                    ELSE 0
                END, 2) AS discount_amount,

                -- Calculated total_base_amount
                CASE 
                    WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                    WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                    ELSE total_amount
                END AS total_base_amount,

                -- total_sell_amount = total_base_amount * (1 + markup)
                ROUND(
                    (
                    CASE 
                        WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                        WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                        ELSE total_amount
                    END
                    ) * (1 + COALESCE(markup, 0)),
                2) AS total_sell_amount,

                -- total_extended_sell_amount = total_sell_amount + surcharge_amount
                ROUND(
                    (
                    (
                        CASE 
                        WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                        WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                        ELSE total_amount
                        END
                    ) * (1 + COALESCE(markup, 0))
                    ) + CASE 
                        WHEN surcharge_type = 'PERCENTAGE' THEN ROUND(COALESCE(
                            (
                            (
                                CASE 
                                WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                                WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                                ELSE total_amount
                                END
                            ) * (1 + COALESCE(markup, 0))
                            ) * surcharge, 0), 2)
                        WHEN surcharge_type = 'MULTIPLIER' THEN ROUND(COALESCE(
                            (
                            (
                                CASE 
                                WHEN discount_type = 'PERCENTAGE' THEN total_amount - ROUND(COALESCE(total_amount * discount, 0), 2)
                                WHEN discount_type = 'MULTIPLIER' THEN total_amount - ROUND(COALESCE(total_amount * (1 - discount), 0), 2)
                                ELSE total_amount
                                END
                            ) * (1 + COALESCE(markup, 0))
                            ) * surcharge, 0), 2)
                        ELSE 0
                        END,
                2) AS total_extended_sell_amount
            FROM 
                project_materials
            WHERE 
                id = '{project_material_id}' AND is_active = TRUE AND is_deleted = FALSE;
        """
        # print("project_material_id:: ",project_material_id)
        rows = db.execute(text(query_text))
        material_data = rows.mappings().first()
        # print("material_data:: ",material_data)
        if material_data:   
            update_query = f"""
                UPDATE project_materials
                SET 
                    total_base_amount = {material_data['total_base_amount']},
                    total_sell_amount = {material_data['total_sell_amount']},
                    total_extended_sell_amount = {material_data['total_extended_sell_amount']}
                WHERE id = '{project_material_id}';
            """
            rows = db.execute(text(update_query))
            db.flush()
            if not return_updated_values:
                return
            else:
                return {
                    "discount_amount": material_data['discount_amount'],
                    "total_amount": material_data['total_amount'],
                    "total_base_amount": material_data['total_base_amount'],
                    "total_sell_amount": material_data['total_sell_amount'],
                    "total_extended_sell_amount": material_data['total_extended_sell_amount'],
                }
        else:
            return None
    except Exception as error:
        # Handle the error appropriately
        print("update_material_charges:: An error occurred:", error)
        raise error
    



async def update_door_width_and_height(db, take_off_sheet_area_item_id):
    """
    Updates the door width and height for a given take-off sheet area item.

    This function retrieves the door width and height from the `ProjectTakeOffSheetSectionAreaItems` table
    and updates them based on the associated `ProjectMaterials` entries that are of type "DOOR". If there
    are fewer doors in the `ProjectMaterials` than the total door count, it fills the remaining slots with
    underscores ("_").

    Args:
        db: The database session object.
        take_off_sheet_area_item_id (str): The ID of the take-off sheet area item to update.

    Raises:
        Exception: If the input features for width or height are unavailable in any of the doors.

    Returns:
        None
    """
    try:
        item = (
            db.query(ProjectTakeOffSheetSectionAreaItems.door_width, ProjectTakeOffSheetSectionAreaItems.door_height)
            .filter(ProjectTakeOffSheetSectionAreaItems.id == take_off_sheet_area_item_id)
        ).first()

        total_doors_count = item.door_width.count(",") + 1

        doors = (
            db.query(ProjectMaterials)
            .select_from(ProjectMaterials)
            .join(OpeningSchedules, onclause=OpeningSchedules.project_material_id == ProjectMaterials.id)
            .filter(
                OpeningSchedules.is_active == True,
                OpeningSchedules.project_take_off_sheet_section_area_item_id == take_off_sheet_area_item_id,
                ProjectMaterials.is_active == True,
                ProjectMaterials.is_deleted == False,
                ProjectMaterials.material_type == "DOOR"
            ).order_by(ProjectMaterials.created_at.asc())
        ).all()

        door_width, door_height = [], []
        for door in doors:
            print('base_feature: ', door.base_feature)
            inputFeatures = door.base_feature['inputFeatures']
            featureNames = inputFeatures.keys()
            width_features = [x  for x in featureNames if "width" in x.lower()]
            height_features = [x  for x in featureNames if "height" in x.lower()]
            if len(width_features) == 0 or len(height_features) == 0:
                raise Exception("Unable to update door_width & door_height stats due to unavailability of input feature")
            width_feature, height_feature = width_features[0], height_features[0]
            door_width.append(str(inputFeatures[width_feature]['value']) + inputFeatures[width_feature]['unit'])
            door_height.append(str(inputFeatures[height_feature]['value']) + inputFeatures[height_feature]['unit'])
        
        new_doors_count = len(doors)
        required_to_fill = total_doors_count - new_doors_count
        for _ in range(required_to_fill):
            door_width.append("_"); door_height.append("_")
        
        result = db.execute(
            update(ProjectTakeOffSheetSectionAreaItems)
            .where(ProjectTakeOffSheetSectionAreaItems.id == take_off_sheet_area_item_id)
            .values(
                door_width = ",".join(door_width), door_height = ",".join(door_height)
            )
        )
    except Exception as e:
        print("update_door_width_and_height:: error - ",e)
        raise e


async def is_short_code_exists(project_id: str, short_code: str, db: Session, exclude_id=None):
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
            ProjectMaterials.short_code == short_code,
            ProjectMaterials.project_id == project_id,
            ProjectMaterials.is_deleted == False
        ]
        if exclude_id:
            filter_conditions.append(ProjectMaterials.id != exclude_id)

        # Execute the query
        project_short_code_exist = (
            db.query(ProjectMaterials)
            .filter(*filter_conditions)
            .all()
        )
        # Check if any matching records are found
        is_exists = len(project_short_code_exist) > 0
        
        return is_exists 
    except Exception as error:
        logger.exception(f"is_short_code_exists:: An unexpected error occurred: {error}")
        raise error


async def get_material_catalog(db: Session, keyword: List[str] = None):
    try:
        manufacturers_with_brands = []
        filter_condition = []  
        if keyword:
            raw_material_data = (
                db.query(RawMaterials)
                .filter(RawMaterials.code.in_(keyword))
                .all()
            )
            if not raw_material_data:
                return manufacturers_with_brands

            # Gather acceptable manufacturer IDs based on the keyword
            catalog_ids = []
            for item in raw_material_data:
                for cat in item.raw_material_catalogs:
                    if cat.has_data:
                        catalog_ids.append(cat.id)
            print("catalog_ids:: ",catalog_ids)
            if catalog_ids:
                filter_condition.append(
                    RawMaterialCatalogMapping.id.in_(list(catalog_ids))
                )
        
        # Query manufacturers and their brands with outer join
        catalog_data = (
            db.query(RawMaterialCatalogMapping)
        )
        # Apply filter based on keyword if needed
        if keyword and len(filter_condition) > 0:
            catalog_data = catalog_data.filter(*filter_condition)
        elif keyword:
            return manufacturers_with_brands
        
        # Apply ordering and pagination
        catalog_data = (
            catalog_data
            .order_by(RawMaterialCatalogMapping.created_at.asc())
            .all()
        )
        
        # Process results for the response structure
        for cat in catalog_data:
            temp_data = {}
            if cat.brand_id is not None:
                temp_data["brand"] = cat.catalog_brand.to_dict
                temp_data["manufacturer"] = cat.catalog_manufacturer.to_dict
            else:
                temp_data["brand"] = None
                temp_data["manufacturer"] = cat.catalog_manufacturer.to_dict
            manufacturers_with_brands.append(temp_data)
        return manufacturers_with_brands
    except Exception as error:
        logger.exception(f"get_material_catalog:: An unexpected error occurred: {error}")
        raise error
    

async def get_ctalog_details(db: Session, catalog: str):
    try:
        catalog_data = {}
        brand_data = db.query(Brands).filter(Brands.code == catalog).first()
        if brand_data:
            catalog_data["brand"] = brand_data.to_dict
            catalog_data["manufacturer"] = brand_data.manufacturer.to_dict
        else:
            manu_data = db.query(Manufacturers).filter(Manufacturers.code == catalog).first()
            catalog_data["manufacturer"] = manu_data.to_dict
        return catalog_data
    except Exception as error:
        logger.exception(f"get_ctalog_details:: An unexpected error occurred: {error}")
        raise error

async def get_brand_manufacture(db: Session, catalog: str):
    try:
        manufacture_code = None
        brand_code = None
        brand_data = db.query(Brands).filter(Brands.code == catalog).first()
        if brand_data:
            brand_code = brand_data.code
            manufacture_code = brand_data.manufacturer.code
        else:
            manufacture_data = db.query(Manufacturers).filter(Manufacturers.code == catalog).first()
            if manufacture_data:
                manufacture_code = manufacture_data.code
        return {"manufacture_code": manufacture_code, "brand_code": brand_code}
    except Exception as error:
        logger.exception(f"get_brand_manufacture:: An unexpected error occurred: {error}")
        raise error
   

async def get_material_series(manufacturer_code: str, brand_code: str, category: str):
    """**Summary:**
    fetch all series of a manufacturer and brand.

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - category (str): The code of the category(i.e. door/frame).

    **Returns:**
    - dict: A dictionary containing information about all series of a manufacturer and brand.
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        series_data = []

        if brand_code is not None:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "brandCode": brand_code,
                "category": category,
            }
        else:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "category": category,
            }
        response = await call_get_api("diamond/series/get_series", param_data)
        if int(response["status_code"]) == 200:
            series_data = response["response"]["data"]
            for indx, elm in enumerate(series_data):
                if "_id" in elm:
                    series_data[indx]["id"] = elm["_id"]
                    del series_data[indx]["_id"]
        return series_data
    except Exception as error:
        logger.exception(f"get_material_series:: An unexpected error occurred: {error}")
        raise error
    

