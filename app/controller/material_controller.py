"""
This module is responsible for all project material related operations
"""

from datetime import datetime
import json
import hashlib
from collections import defaultdict
from loguru import logger
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_section_area_items import (
    ProjectTakeOffSheetSectionAreaItems,
)
from models.project_take_off_sheet_sections import ProjectTakeOffSheetSections
from models.project_materials import ProjectMaterials, MATERIAL_TYPE
from models.hardware_groups import HardwareGroups
from models.sections import Sections
from models.hardware_group_materials import HardwareGroupMaterials
from models.raw_materials import RawMaterials
from models.section_raw_materials import SectionRawMaterials
from models.door_frame_raw_material_sections import DoorFrameRawMaterialSections
from models.material_description import MaterialDescription
from repositories.common_repositories import (
    get_take_off_sheet_section_price,
    add_estimation_breakups_to_project,
)
from repositories.material_repositories import (
    update_door_width_and_height,
    is_short_code_exists,
    get_description,
)
from models.manufacturers import Manufacturers
from models.brands import Brands
from models.raw_materials_catalog_mapping import RawMaterialCatalogMapping
from models.opening_schedules import OpeningSchedules, COMPONENTS
from repositories.material_repositories import (
    update_material_charges,
    get_material_type,
)
from repositories.update_stats_repositories import (
    update_opening_schedule_stats,
    update_area_item_stats,
    update_section_stats,
    update_take_off_sheet_stats,
    update_raw_material_stats,
)
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import math
import random
import string
from utils.request_handler import call_get_api
from utils.common import get_user_time, generate_uuid
from sqlalchemy.orm import Session
from schemas.materials_schema import (
    BatchProjectMaterialAssignRequest,
    CreateOpeningProjectMaterialRequest,
    ProjectMaterial,
    ProjectMaterialRequest,
    ProjectMaterialAssignRequest,
    RawMaterialMappingRequest,
    UpdateMaterialDescriptionRequest,
    UpdateDoorFrameMaterialSectionRequest,
)
from models.members import Members
from controller.opening_hardware_group_controller import add_category_info


async def generate_unique_short_code(
    project_id: str,
    db: Session,
    prefix: str = "MAT",
    code_length: int = 6,
    max_attempts: int = 20,
):
    """Generate a unique short code for a project material.

    The generated format is `<PREFIX>-<SUFFIX>`, where suffix is uppercase
    alphanumeric. The function retries until it finds a non-existing short code
    within the project or raises an error after exhausting attempts.
    """
    if not prefix:
        prefix = "MAT"
    prefix = str(prefix).strip().upper()

    if code_length <= 0:
        code_length = 6
    if max_attempts <= 0:
        max_attempts = 20

    alphabet = string.ascii_uppercase + string.digits

    for _ in range(max_attempts):
        suffix = "".join(random.choices(alphabet, k=code_length))
        candidate_code = f"{prefix}-{suffix}"
        short_code_exists = await is_short_code_exists(project_id, candidate_code, db)
        if not short_code_exists:
            return candidate_code

    raise ValueError("Unable to generate a unique short code after multiple attempts.")


def _get_material_description_combination_key(
    effective_material_type: str,
    raw_material_type: str,
    effective_series,
    effective_base_feature,
    effective_adon_feature,
    adon_fields,
):
    normalized_payload = {
        "material_type": effective_material_type,
        "raw_material_type": raw_material_type,
        "series": effective_series,
        "base_feature": effective_base_feature,
        "adon_feature": effective_adon_feature,
        "adon_fields": adon_fields,
    }
    payload_string = json.dumps(
        normalized_payload, sort_keys=True, default=str, separators=(",", ":")
    )
    return hashlib.sha256(payload_string.encode("utf-8")).hexdigest()


async def get_manufaturers(db: Session, page: int, page_size: int, keyword: str):
    """**Summary:**
    fetch all manufacturers.

    **Args:**
    - `db` (Session): The database session.
    - page (int): The page number to retrieve.
    - page_size (int): The number of items per page.
    - keyword (str): Keyword for filtering brands ('FRAME', 'DOOR', or any other value).

    **Returns:**
    - dict: A dictionary containing information about all manufacturer
        - `data` (dict): A dictionary containing all manufacturer data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        base_query = db.query(Manufacturers).filter(Manufacturers.is_deleted == False)
        # set the limit depending on the pagination info
        if page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = base_query.count()
            page = 1

        # Default filter value
        filter_condition = None
        if keyword:
            raw_material_data = (
                db.query(RawMaterials).filter(RawMaterials.code == keyword).all()
            )
            if len(raw_material_data) == 0:
                return JSONResponse(
                    status_code=400, content={"message": "Invalid keyword provided"}
                )
            acceptable_ids = []
            for item in raw_material_data:
                catalogs = item.raw_material_catalogs
                for cat in catalogs:
                    if cat.has_data:
                        acceptable_ids.append(cat.manufacturer_id)
            acceptable_ids = list(set(acceptable_ids))
            if len(acceptable_ids) > 0:
                # Set filter condition based on keyword
                filter_condition = Manufacturers.id.in_(acceptable_ids)
        # Query data with filters
        manufacturer_data = db.query(Manufacturers).filter(
            Manufacturers.is_deleted == False
        )
        if keyword:
            if filter_condition is not None:
                manufacturer_data = manufacturer_data.filter(filter_condition)
            else:
                return JSONResponse(
                    status_code=400,
                    content={"message": f"No Manufacturer found providing {keyword}"},
                )
        item_count = manufacturer_data.count()
        # Order data, apply pagination, and retrieve all matching records
        manufacturer_data = (
            manufacturer_data.order_by(Manufacturers.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        if page_size is None:
            page_size = len(manufacturer_data)
            item_count = len(manufacturer_data)
        # getting total number of items count
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0
        item_count = item_count if page_count > 0 else 0
        response = {
            "data": manufacturer_data,
            "page_count": page_count,
            "item_count": item_count,
            "message": "Data fetch successfull",
        }
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_catalogs(db: Session, page: int, page_size: int, keyword: str):
    """**Summary:**
    fetch all manufacturers.

    **Args:**
    - `db` (Session): The database session.
    - page (int): The page number to retrieve.
    - page_size (int): The number of items per page.
    - keyword (str): Keyword for filtering brands ('FRAME', 'DOOR', or any other value).

    **Returns:**
    - dict: A dictionary containing information about all manufacturer
        - `data` (dict): A dictionary containing all manufacturer data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        base_query = db.query(RawMaterialCatalogMapping)
        # set the limit depending on the pagination info
        if page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = base_query.count()
            page = 1

        filter_condition = []
        if keyword:
            raw_material_data = (
                db.query(RawMaterials).filter(RawMaterials.code == keyword).all()
            )
            if not raw_material_data:
                return JSONResponse(
                    status_code=400, content={"message": "Invalid keyword provided"}
                )

            # Gather acceptable manufacturer IDs based on the keyword
            catalog_ids = []
            for item in raw_material_data:
                print("item:: ", item.id)
                for cat in item.raw_material_catalogs:
                    print("cat:: ", cat.id)
                    if cat.has_data:
                        catalog_ids.append(cat.id)
            print("catalog_ids:: ", catalog_ids)
            if catalog_ids:
                filter_condition.append(
                    RawMaterialCatalogMapping.id.in_(list(catalog_ids))
                )

        # Query manufacturers and their brands with outer join
        catalog_data = db.query(RawMaterialCatalogMapping)
        # Apply filter based on keyword if needed
        if keyword and len(filter_condition) > 0:
            catalog_data = catalog_data.filter(*filter_condition)
        elif keyword:
            return JSONResponse(
                status_code=400,
                content={"message": f"No Catalog found providing {keyword}"},
            )

        item_count = catalog_data.count()
        # Apply ordering and pagination
        catalog_data = (
            catalog_data.order_by(RawMaterialCatalogMapping.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Process results for the response structure
        manufacturers_with_brands = []
        for cat in catalog_data:
            temp_data = {}
            if cat.brand_id is not None:
                temp_data["brand"] = cat.catalog_brand.to_dict
                temp_data["manufacturer"] = cat.catalog_manufacturer.to_dict
            else:
                temp_data["brand"] = None
                temp_data["manufacturer"] = cat.catalog_manufacturer.to_dict
            manufacturers_with_brands.append(temp_data)

        if page_size is None:
            page_size = len(manufacturers_with_brands)
            item_count = len(manufacturers_with_brands)
        # getting total number of items count
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0
        item_count = item_count if page_count > 0 else 0
        response = {
            "data": manufacturers_with_brands,
            "page_count": page_count,
            "item_count": item_count,
            "message": "Data fetch successfull",
        }
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_catalogs_v2(db: Session, page: int = None, page_size: int = None):
    try:
        base_query = (
            db.query(Manufacturers)
            .filter(Manufacturers.is_active == True, Manufacturers.is_deleted == False)
            .order_by(Manufacturers.created_at.asc())
        )

        total_count = base_query.count()

        if page is not None and page_size is not None:
            skip = (page - 1) * page_size
            manufacturers = base_query.offset(skip).limit(page_size).all()
        else:
            manufacturers = base_query.all()
            page = 1
            page_size = len(manufacturers)

        result = []
        for manufacturer in manufacturers:
            result.append(
                {
                    "manufacturer": manufacturer.to_dict,
                    "brands": [
                        brand.to_dict
                        for brand in manufacturer.brands
                        if brand.is_active and not brand.is_deleted
                    ],
                }
            )

        page_count = math.ceil(total_count / page_size) if page_size else 1

        converted = []

        for item in result:
            manufacturer = item["manufacturer"]
            brands = item.get("brands", {})
            if not brands:
                converted.append({"brand": None, "manufacturer": manufacturer})
            else:
                for brand in brands:
                    converted.append({"brand": brand, "manufacturer": manufacturer})

        return JSONResponse(
            status_code=200,
            content={
                "data": converted,
                "page_count": page_count,
                "item_count": total_count,
                "status": "success",
            },
        )

    except Exception as error:
        logger.exception(f"get_catalogs_v2:: Unexpected error - {error}")
        raise error


async def get_brands(
    db: Session, page: int, page_size: int, manufacturer_id: str, keyword: str
):
    """**Summary:**
    fetch all brands of a manufacturer.

    **Args:**
    - `db` (Session): The database session.
    - page (int): The page number to retrieve.
    - page_size (int): The number of items per page.
    - manufacturer_id (str): The ID of the manufacturer.
    - keyword (str): Keyword for filtering brands ('FRAME', 'DOOR', or any other value).

    **Returns:**
    - dict: A dictionary containing information about all brands of a manufacturer
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        base_query = db.query(Brands).filter(
            Brands.manufacturer_id == manufacturer_id, Brands.is_deleted == False
        )
        # set the limit depending on the pagination info
        if page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = base_query.count()
            page = 1
        item_count = base_query.count()

        # Default filter value
        filter_condition = None
        if keyword:
            raw_material_data = (
                db.query(RawMaterials).filter(RawMaterials.code == keyword).all()
            )
            if len(raw_material_data) == 0:
                return JSONResponse(
                    status_code=400, content={"message": "Invalid keyword provided"}
                )
            acceptable_ids = []
            for item in raw_material_data:
                catalogs = item.raw_material_catalogs
                for cat in catalogs:
                    if cat.has_data and cat.brand_id is not None:
                        acceptable_ids.append(cat.brand_id)
            acceptable_ids = list(set(acceptable_ids))
            if len(acceptable_ids) > 0:
                # Set filter condition based on keyword
                filter_condition = Brands.id.in_(acceptable_ids)
        # Query data with filters
        brand_data = db.query(Brands).filter(
            Brands.manufacturer_id == manufacturer_id, Brands.is_deleted == False
        )
        if keyword:
            if filter_condition is not None:
                brand_data = brand_data.filter(filter_condition)
            else:
                return JSONResponse(
                    status_code=400,
                    content={"message": f"No Brand found providing {keyword}"},
                )
        item_count = brand_data.count()
        # Order data, apply pagination, and retrieve all matching records
        brand_data = (
            brand_data.order_by(Brands.created_at.asc()).offset(skip).limit(limit).all()
        )

        if page_size is None:
            page_size = len(brand_data)
            item_count = len(brand_data)
        # getting total number of items count
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0
        item_count = item_count if page_count > 0 else 0
        response = {
            "data": brand_data,
            "page_count": page_count,
            "item_count": item_count,
            "message": "Data fetch successfull",
        }
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_series(
    db: Session, manufacturer_code: str, brand_code: str, category: str
):
    """**Summary:**
    fetch all series of a manufacturer and brand.

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - category (str): The code of the category.

    **Returns:**
    - dict: A dictionary containing information about all series of a manufacturer and brand.
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        category = await get_material_type(db, category)
        if category is None:
            return JSONResponse(
                content={"message": "Invalid Category"}, status_code=400
            )
        category = category.lower()
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
            return {
                "data": response["response"]["data"],
                "message": "Data fetch successfull",
            }
        else:
            return JSONResponse(
                content={"message": "Unable to fetch pricebook data"},
                status_code=int(response["status_code"]),
            )
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_features(manufacturer_code: str, brand_code: str, series_code: str):
    """**Summary:**
    fetch all features of a series.

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - series_code (str): The code of the series.

    **Returns:**
    - dict: A dictionary containing information about all features of a series
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        if brand_code is not None:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "brandCode": brand_code,
                "seriesCode": series_code,
            }
        else:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "seriesCode": series_code,
            }
        response = await call_get_api("diamond/features/get_features", param_data)
        if int(response["status_code"]) == 200:
            return {
                "data": response["response"]["data"],
                "message": "Data fetch successfull",
            }
        else:
            return JSONResponse(
                content={"message": "Unable to fetch pricebook data"},
                status_code=int(response["status_code"]),
            )
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_baseprice(
    request_params: dict, manufacturer_code: str, brand_code: str, series_code: str
):
    """**Summary:**
    fetch all features baseprice of a series.

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - series_code (str): The code of the series.
    - request_params (dict): extra dynamic param.
    - `db` (Session): The database session.

    **Returns:**
    - dict: A dictionary containing information about all features of a series
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        if brand_code is not None:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "brandCode": brand_code,
                "seriesCode": series_code,
                **request_params,
            }
        else:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "seriesCode": series_code,
                **request_params,
            }
        response = await call_get_api("diamond/baseprice/get_baseprice", param_data)
        if int(response["status_code"]) == 200:
            data = response["response"]["data"]
            if len(data) == 1:
                return {"data": data, "message": "Data fetch successfull"}
            else:
                return {"data": [], "message": "Data fetch successfull"}
        else:
            return JSONResponse(
                content={"message": "Unable to fetch pricebook data"},
                status_code=int(response["status_code"]),
            )
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_adon_features(manufacturer_code: str, brand_code: str, series_code: str):
    """**Summary:**
    fetch all adon-features of a series.

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - series_code (str): The code of the series.

    **Returns:**
    - dict: A dictionary containing information about all adon-features of a series
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        if brand_code is not None:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "brandCode": brand_code,
                "seriesCode": series_code,
            }
        else:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "seriesCode": series_code,
            }
        response = await call_get_api(
            "diamond/adonFeatures/get_adonFeatures", param_data
        )
        if int(response["status_code"]) == 200:
            return {
                "data": response["response"]["data"],
                "message": "Data fetch successfull",
            }
        else:
            return JSONResponse(
                content={"message": "Unable to fetch pricebook data"},
                status_code=int(response["status_code"]),
            )
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_adonprice(
    request_params: dict, manufacturer_code: str, brand_code: str, series_code: str
):
    """**Summary:**
    fetch all adon-features price of a series.

    **Args:**
    - manufacturer_code (str): The code of the manufacturer.
    - brand_code (str): The code of the brand.
    - series_code (str): The code of the series.
    - request_params (dict): extra dynamic param.
    - `db` (Session): The database session.

    **Returns:**
    - dict: A dictionary containing information about all features of a series
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        if brand_code is not None:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "brandCode": brand_code,
                "seriesCode": series_code,
                **request_params,
            }
        else:
            param_data = {
                "manufacturerCode": manufacturer_code,
                "seriesCode": series_code,
                **request_params,
            }
        response = await call_get_api("diamond/adonprice/get_adonprice", param_data)
        if int(response["status_code"]) == 200:
            data = response["response"]["data"]
            if len(data) == 1:
                return {"data": data, "message": "Data fetch successfull"}
            else:
                return {"data": [], "message": "Data fetch successfull"}
        else:
            return JSONResponse(
                content={"message": "Unable to fetch pricebook data"},
                status_code=int(response["status_code"]),
            )
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def sync_project_material_price(project_material_id: str, db: Session):
    """**Summary:**
    sync all prices from the pricebook server.

    **Args:**
    - project_material_id (str): The ID of the project_material to be updated.
    - `db` (Session): The database session.

    **Returns:**
    - dict: A dictionary containing information about all features of a series
        - `data` (dict): A dictionary containing all brand data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        item = (
            db.query(ProjectMaterials)
            .filter(ProjectMaterials.id == project_material_id)
            .first()
        )
        if item:
            price_data = {"base_price": {}, "adon_price": {}}
            series = item.series
            base_feature = item.base_feature
            adon_feature = item.adon_feature
            manufacturer_id = item.manufacturer_id
            brand_id = item.brand_id
            if len(base_feature.keys()) > 0:
                manufacturer_data = (
                    db.query(Manufacturers)
                    .filter(Manufacturers.id == manufacturer_id)
                    .first()
                )
                brand_data = db.query(Brands).filter(Brands.id == brand_id).first()
                # syncing the base price
                param_data = {
                    "seriesCode": series,
                    "manufacturerCode": manufacturer_data.code,
                    "brandCode": brand_data.code,
                }
                for key, value in base_feature.items():
                    param_data[key] = value["optionCode"]
                response = await call_get_api(
                    "diamond/baseprice/get_baseprice", param_data
                )
                if int(response["status_code"]) == 200:
                    data = response["response"]["data"]
                    if len(data) == 1:
                        price_data["base_price"] = data[0]
                    if len(adon_feature.keys()) > 0:
                        # syncing the adon price
                        param_data = {
                            "seriesCode": series,
                            "manufacturerCode": manufacturer_data.code,
                            "brandCode": brand_data.code,
                        }
                        for key, value in adon_feature.items():
                            param_data[key] = value["optionCode"]
                            response = await call_get_api(
                                "diamond/adonprice/get_adonprice", param_data
                            )
                            if int(response["status_code"]) == 200:
                                data = response["response"]["data"]
                                if len(data) == 1:
                                    price_data["adon_price"][key] = data[0]
                            # else:
                            #     return JSONResponse(content={"message": "Unable to fetch adon price data"}, status_code=int(response["status_code"]))
                    return {
                        "data": price_data,
                        "message": "Price synced successfully.",
                        "status": "success",
                    }
                else:
                    return JSONResponse(
                        content={"message": "Unable to fetch base price data"},
                        status_code=int(response["status_code"]),
                    )
            else:
                return JSONResponse(
                    content={"message": "No base feature is there"}, status_code=400
                )
        else:
            return JSONResponse(content={"message": "Item not found"}, status_code=400)
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def add_hardware_material(
    material_req_data: ProjectMaterialRequest,
    hardware_group_id: str,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    This module is responsible for creating a hardware material for a project hardware group.

    **Args:**
    - material_req_data (dict): project material create data.
    - `hardware_group_id` (str): hardware_group id for which we are going to add the project material.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): created project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Ensure that only set fields are considered
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            # Set created_by field to the current member's ID
            material_req_data["created_by"] = current_member.id

            # Set default material type to "HARDWARE" if not provided
            if "material_type" not in material_req_data:
                material_req_data["material_type"] = "HARDWARE"

            # Calculate final amount based on total amount and quantity
            total_amount = material_req_data["total_amount"]
            quantity = material_req_data["quantity"]
            final_amount = total_amount * quantity
            if "quantity" in material_req_data:
                del material_req_data["quantity"]

            # Check if the provided shortcode is unique within the project
            short_code = material_req_data["short_code"]
            hw_group_data = db.query(HardwareGroups).get(hardware_group_id)

            # fetch raw_material with code 'HWD' which stands for Hardware
            raw_material_hwd = (
                db.query(RawMaterials.id).filter(RawMaterials.code == "HWD")
            ).first()
            # we need the id to associate the hardware_material with the raw_material
            material_req_data["raw_material_id"] = (
                None if raw_material_hwd is None else raw_material_hwd.id
            )

            project_short_code_exist = await is_short_code_exists(
                hw_group_data.project_id, short_code, db
            )
            if not project_short_code_exist:
                # Manage product category of the hardware
                product_category = material_req_data["product_category"]
                material_req_data["hardware_product_category_id"] = (
                    await add_category_info(db, product_category)
                )
                del material_req_data["product_category"]

                # We need to apply the markup, margin, discount, surcharge automatically based on an exisiting project_material
                add_estimation_breakups_to_project(db, material_req_data)

                desc = await get_description(
                    db,
                    {},
                    material_req_data["series"],
                    "HWD",
                    material_req_data["base_feature"],
                    material_req_data["adon_feature"],
                )
                material_req_data["desc"] = desc

                # Create the project material
                material_data = ProjectMaterials(**material_req_data)
                db.add(material_data)
                db.flush()
                project_material_id = material_data.id

                material_costs = await update_material_charges(
                    db, project_material_id, return_updated_values=True
                )

                # calculate the total base cost and sell cost and final base cost and final base cost sell cost
                if material_costs is not None:
                    total_sell_amount = material_costs["total_sell_amount"]
                    total_base_amount = material_costs["total_base_amount"]
                    total_extended_sell_amount = material_costs[
                        "total_extended_sell_amount"
                    ]
                    final_sell_amount = quantity * total_sell_amount
                    final_base_amount = quantity * total_base_amount
                    final_extended_sell_amount = quantity * total_extended_sell_amount
                else:
                    total_sell_amount = total_amount
                    total_base_amount = total_amount
                    total_extended_sell_amount = total_amount
                    final_sell_amount = quantity * total_sell_amount
                    final_base_amount = quantity * total_base_amount
                    final_extended_sell_amount = quantity * total_extended_sell_amount

                # Create the relation between project material and hardware group
                hw_group_material_data = HardwareGroupMaterials(
                    total_amount=total_amount,
                    quantity=quantity,
                    final_amount=final_amount,
                    project_material_id=project_material_id,
                    hardware_group_id=hardware_group_id,
                    total_sell_amount=total_sell_amount,
                    total_base_amount=total_base_amount,
                    total_extended_sell_amount=total_extended_sell_amount,
                    final_base_amount=final_base_amount,
                    final_sell_amount=final_sell_amount,
                    final_extended_sell_amount=final_extended_sell_amount,
                    created_by=current_member.id,
                )
                db.add(hw_group_material_data)
                db.flush()

                # Update statistics for the associated hardware group
                take_off_sheet_section_area_item_ids = (
                    await update_opening_schedule_stats(
                        db, hardware_group_id=hardware_group_id
                    )
                )
                for (
                    take_off_sheet_section_area_item_id
                ) in take_off_sheet_section_area_item_ids:
                    # Update area item statistics related to the hardware group
                    take_off_sheet_section_id = await update_area_item_stats(
                        db,
                        project_take_off_sheet_section_area_item_id=take_off_sheet_section_area_item_id,
                    )

                    # Update section statistics related to the hardware group
                    await update_section_stats(
                        db, project_take_off_sheet_section_id=take_off_sheet_section_id
                    )

                project_take_off_data = (
                    db.query(ProjectTakeOffSheets)
                    .filter(
                        ProjectTakeOffSheets.project_id
                        == material_req_data["project_id"]
                    )
                    .first()
                )

                if project_take_off_data is not None:
                    # update the sheet stats after deleting the section area and its associated openings
                    await update_take_off_sheet_stats(
                        db, project_take_off_sheet_id=project_take_off_data.id
                    )

                    # update the raw material stats after deleting the section area and its associated openings
                    await update_raw_material_stats(
                        db, project_id=project_take_off_data.project_id
                    )

                # Return success message and created material ID
                return {
                    "id": project_material_id,
                    "message": "Hardware group material added.",
                    "status": "success",
                }
            else:
                return JSONResponse(
                    content={
                        "message": "Short Code already exits in the current project"
                    },
                    status_code=400,
                )
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def update_hardware_material(
    material_req_data: ProjectMaterialRequest, current_member: Members, db: Session
):
    """**Summary:**
    This module is responsible for creating a hardware material for a project hardware group.

    **Args:**
    - material_req_data (dict): project material create data.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): created project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Extract relevant data from the request payload
            material_req_data = material_req_data.model_dump(exclude_unset=True)

            # Check if 'id' field is present in the payload
            if not "id" in material_req_data:
                return JSONResponse(
                    content={"message": "Invalid request payload."}, status_code=400
                )

            project_material_data = db.query(ProjectMaterials).get(
                material_req_data["id"]
            )

            # Set default material type to 'HARDWARE' if not provided
            if "material_type" not in material_req_data:
                material_req_data["material_type"] = "HARDWARE"

            # Calculate final amount based on total amount and quantity
            final_amount = None
            if "total_amount" in material_req_data:
                total_amount = material_req_data["total_amount"]
            else:
                total_amount = project_material_data.total_amount

            if "quantity" in material_req_data:
                quantity = material_req_data["quantity"]
                del material_req_data["quantity"]
            else:
                quantity = project_material_data.quantity

            final_amount = total_amount * quantity

            hardware_group_material_datas = (
                db.query(HardwareGroupMaterials)
                .filter(
                    HardwareGroupMaterials.project_material_id
                    == material_req_data["id"]
                )
                .all()
            )

            # Return error if material data or associated hardware group materials are not found
            if not (project_material_data or hardware_group_material_datas):
                return JSONResponse(
                    content={"message": "Invalid request payload."}, status_code=400
                )

            # Check and update shortcode if provided
            if "short_code" in material_req_data:
                short_code = material_req_data["short_code"]
                project_short_code_exist = await is_short_code_exists(
                    project_material_data.project_id,
                    short_code,
                    db,
                    material_req_data["id"],
                )
                if project_short_code_exist:
                    return JSONResponse(
                        content={"message": "Shortcode Already in used"},
                        status_code=400,
                    )

            if "product_category" in material_req_data:
                # Manage product category of the hardware
                product_category = material_req_data["product_category"]
                material_req_data["hardware_product_category_id"] = (
                    await add_category_info(db, product_category)
                )
                del material_req_data["product_category"]

            desc = await get_description(
                db,
                {},
                material_req_data["series"],
                "HWD",
                material_req_data["base_feature"],
                material_req_data["adon_feature"],
            )
            material_req_data["desc"] = desc
            # Update material data with current member's ID
            material_req_data["updated_by"] = current_member.id
            for key, value in material_req_data.items():
                setattr(project_material_data, key, value)

            db.flush()

            material_costs = await update_material_charges(
                db, project_material_data.id, return_updated_values=True
            )
            # calculate the total base cost and sell cost and final base cost and final base cost sell cost
            if material_costs is not None:
                total_sell_amount = material_costs["total_sell_amount"]
                total_base_amount = material_costs["total_base_amount"]
                total_extended_sell_amount = material_costs[
                    "total_extended_sell_amount"
                ]
                final_sell_amount = quantity * total_sell_amount
                final_base_amount = quantity * total_base_amount
                final_extended_sell_amount = quantity * total_extended_sell_amount
            else:
                total_sell_amount = total_amount
                total_base_amount = total_amount
                total_extended_sell_amount = total_amount
                final_sell_amount = quantity * total_sell_amount
                final_base_amount = quantity * total_base_amount
                final_extended_sell_amount = quantity * total_extended_sell_amount
            # Update hardware group material data if final amount is not none
            hardware_group_ids = []
            if final_amount:
                for hardware_group_material_data in hardware_group_material_datas:
                    hardware_group_material_data.total_amount = total_amount
                    hardware_group_material_data.quantity = quantity
                    hardware_group_material_data.final_amount = final_amount
                    hardware_group_material_data.total_sell_amount = total_sell_amount
                    hardware_group_material_data.total_base_amount = total_base_amount
                    hardware_group_material_data.total_extended_sell_amount = (
                        total_extended_sell_amount
                    )
                    hardware_group_material_data.final_sell_amount = final_sell_amount
                    hardware_group_material_data.final_base_amount = final_base_amount
                    hardware_group_material_data.final_extended_sell_amount = (
                        final_extended_sell_amount
                    )

                    hardware_group_ids.append(
                        hardware_group_material_data.hardware_group_id
                    )

            # Update stats for associated hardware groups
            if hardware_group_ids:
                for hardware_group_id in hardware_group_ids:

                    # Update statistics for the associated hardware group
                    take_off_sheet_section_area_item_ids = (
                        await update_opening_schedule_stats(
                            db, hardware_group_id=hardware_group_id
                        )
                    )

                    for (
                        take_off_sheet_section_area_item_id
                    ) in take_off_sheet_section_area_item_ids:
                        # Update area item statistics related to the hardware group
                        take_off_sheet_section_id = await update_area_item_stats(
                            db,
                            project_take_off_sheet_section_area_item_id=take_off_sheet_section_area_item_id,
                        )

                        # Update section statistics related to the hardware group
                        await update_section_stats(
                            db,
                            project_take_off_sheet_section_id=take_off_sheet_section_id,
                        )

                project_take_off_data = (
                    db.query(ProjectTakeOffSheets)
                    .filter(
                        ProjectTakeOffSheets.project_id
                        == project_material_data.project_id
                    )
                    .first()
                )

                if project_take_off_data is not None:
                    # update the sheet stats after deleting the section area and its associated openings
                    await update_take_off_sheet_stats(
                        db, project_take_off_sheet_id=project_take_off_data.id
                    )

                    # update the raw material stats after deleting the section area and its associated openings
                    await update_raw_material_stats(
                        db, project_id=project_take_off_data.project_id
                    )

            # Return success message and updated material ID
            return {
                "id": material_req_data["id"],
                "message": "Hardware group material updated.",
                "status": "success",
            }

    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def delete_hardware_material(
    hardware_group_material_id: str, current_member: Members, db: Session
):
    """**Summary:**
    Delete hardware material from the database and updates related statistics.

    Args:
        - hardware_group_material_id: The ID of the hardware group material to be removed.
        - current_member (Members): The current member (user) making the request.
        - db: The database session.

    Returns:
        dict: A dictionary containing a message and status indicating the success of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Retrieve hardware group material data based on the provided ID
            hardware_group_material_data = db.query(HardwareGroupMaterials).get(
                hardware_group_material_id
            )

            # Check if hardware group material data exists
            if hardware_group_material_data:

                # # Retrieve all hardware group materials associated with the same project material
                # hardware_group_material_list = (
                #     db.query(HardwareGroupMaterials)
                #     .filter(
                #         HardwareGroupMaterials.project_material_id
                #         == hardware_group_material_data.project_material_id
                #     )
                #     .all()
                # )

                # Delete the hardware group material with the provided ID
                db.query(HardwareGroupMaterials).filter(
                    HardwareGroupMaterials.id == hardware_group_material_id
                ).delete()

                # # If there's only one hardware group associated with this project material, delete the project material as well
                # if len(hardware_group_material_list) == 1:
                #     update_data = {
                #         "is_deleted": True,
                #         "deleted_at": datetime.now(),
                #         "deleted_by": current_member.id,
                #     }
                #     db.query(ProjectMaterials).filter(
                #         ProjectMaterials.id
                #         == hardware_group_material_data.project_material_id
                #     ).update(update_data)

                # Update statistics for the associated hardware group
                take_off_sheet_section_area_item_ids = await update_opening_schedule_stats(
                    db, hardware_group_id=hardware_group_material_data.hardware_group_id
                )

                for (
                    take_off_sheet_section_area_item_id
                ) in take_off_sheet_section_area_item_ids:
                    # Update area item statistics related to the hardware group
                    take_off_sheet_section_id = await update_area_item_stats(
                        db,
                        project_take_off_sheet_section_area_item_id=take_off_sheet_section_area_item_id,
                    )

                    # Update section statistics related to the hardware group
                    await update_section_stats(
                        db, project_take_off_sheet_section_id=take_off_sheet_section_id
                    )

                project_material_data = (
                    db.query(ProjectMaterials)
                    .filter(
                        ProjectMaterials.id
                        == hardware_group_material_data.project_material_id
                    )
                    .first()
                )

                project_take_off_data = (
                    db.query(ProjectTakeOffSheets)
                    .filter(
                        ProjectTakeOffSheets.project_id
                        == project_material_data.project_id
                    )
                    .first()
                )

                # update the sheet stats after deleting the section area and its associated openings
                await update_take_off_sheet_stats(
                    db, project_take_off_sheet_id=project_take_off_data.id
                )

                # update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(
                    db, project_id=project_take_off_data.project_id
                )

                return {"message": "Material Deleted.", "status": "success"}

            else:
                return JSONResponse(content={"message": "Invalid ID"}, status_code=400)

    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def assign_hardware_material(
    material_req_data: ProjectMaterialAssignRequest,
    hardware_group_id: str,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    This module is responsible for assigning an existing hardware material to a project hardware group.

    **Args:**
    - material_req_data (dict): project material data that will be assign to the hw group.
    - `hardware_group_id` (str): hardware_group id for which we are going to add the project material.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): created project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # print("material_req_data:: ",material_req_data)
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            project_material_id = material_req_data["project_material_id"]
            quantity = material_req_data["quantity"]
            material_data = db.query(ProjectMaterials).get(project_material_id)
            # print("material_data:: ",material_data.to_dict)
            total_amount = material_data.total_amount
            total_sell_amount = material_data.total_sell_amount
            total_base_amount = material_data.total_base_amount
            total_extended_sell_amount = material_data.total_extended_sell_amount
            hardware_exists = (
                db.query(HardwareGroupMaterials)
                .filter(
                    HardwareGroupMaterials.hardware_group_id == hardware_group_id,
                    HardwareGroupMaterials.project_material_id == project_material_id,
                )
                .all()
            )
            if len(hardware_exists) == 0:
                final_amount = total_amount * quantity
                final_sell_amount = quantity * total_sell_amount
                final_base_amount = quantity * total_base_amount
                final_extended_sell_amount = quantity * total_extended_sell_amount
                # This section is going to add the relation between project material and hw group
                hw_group_material_data = HardwareGroupMaterials(
                    total_amount=total_amount,
                    quantity=quantity,
                    final_amount=final_amount,
                    total_sell_amount=total_sell_amount,
                    total_base_amount=total_base_amount,
                    total_extended_sell_amount=total_extended_sell_amount,
                    final_sell_amount=final_sell_amount,
                    final_base_amount=final_base_amount,
                    final_extended_sell_amount=final_extended_sell_amount,
                    project_material_id=project_material_id,
                    hardware_group_id=hardware_group_id,
                    created_by=current_member.id,
                )
                db.add(hw_group_material_data)
                db.flush()

                # Update statistics for the associated hardware group
                take_off_sheet_section_area_item_ids = (
                    await update_opening_schedule_stats(
                        db, hardware_group_id=hardware_group_id
                    )
                )

                for (
                    take_off_sheet_section_area_item_id
                ) in take_off_sheet_section_area_item_ids:
                    # Update area item statistics related to the hardware group
                    take_off_sheet_section_id = await update_area_item_stats(
                        db,
                        project_take_off_sheet_section_area_item_id=take_off_sheet_section_area_item_id,
                    )

                    # Update section statistics related to the hardware group
                    await update_section_stats(
                        db, project_take_off_sheet_section_id=take_off_sheet_section_id
                    )

                project_take_off_data = (
                    db.query(ProjectTakeOffSheets)
                    .filter(ProjectTakeOffSheets.project_id == material_data.project_id)
                    .first()
                )

                # update the sheet stats after deleting the section area and its associated openings
                await update_take_off_sheet_stats(
                    db, project_take_off_sheet_id=project_take_off_data.id
                )

                # update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(
                    db, project_id=project_take_off_data.project_id
                )

                return {
                    "id": project_material_id,
                    "message": "project material Added.",
                    "status": "success",
                }
            else:
                return JSONResponse(
                    content={
                        "message": "Current Hardware material already exists in the group"
                    },
                    status_code=400,
                )
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def assign_material_to_opening(
    material_req_data: ProjectMaterialAssignRequest,
    project_take_off_sheet_section_area_item_id: str,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    This module is responsible for assigning an existing project material to a project opening.

    **Args:**
    - material_req_data (ProjectMaterialAssignRequest): project material data with project_material_id and quantity.
    - `project_take_off_sheet_section_area_item_id` (str): project_take_off_sheet_section_area_item id for which we are going to assign the project material.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            project_material_id = material_req_data["project_material_id"]
            quantity = material_req_data["quantity"]

            # Get the existing material
            material_data = db.query(ProjectMaterials).get(project_material_id)
            if not material_data:
                return JSONResponse(
                    content={"message": "Project material not found"}, status_code=404
                )

            # Get opening information
            project_take_off_sheet_section_area_item_data = db.query(
                ProjectTakeOffSheetSectionAreaItems
            ).get(project_take_off_sheet_section_area_item_id)
            if not project_take_off_sheet_section_area_item_data:
                return JSONResponse(
                    content={"message": "Opening not found"}, status_code=404
                )

            project_take_off_sheet_data = db.query(ProjectTakeOffSheets).get(
                project_take_off_sheet_section_area_item_data.project_take_off_sheet_id
            )

            # Get material costs
            total_amount = material_data.total_amount
            total_sell_amount = material_data.total_sell_amount
            total_base_amount = material_data.total_base_amount
            total_extended_sell_amount = material_data.total_extended_sell_amount

            # Calculate final amounts
            final_amount = total_amount * quantity
            final_sell_amount = quantity * total_sell_amount
            final_base_amount = quantity * total_base_amount
            final_extended_sell_amount = quantity * total_extended_sell_amount

            # Check if material already assigned to this opening with the same component type
            material_type = material_data.material_type.value
            material_type_enum = COMPONENTS(material_type)

            existing_schedule = (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.project_take_off_sheet_section_area_item_id
                    == project_take_off_sheet_section_area_item_id,
                    OpeningSchedules.project_material_id == project_material_id,
                    OpeningSchedules.component == material_type_enum,
                )
                .first()
            )

            if existing_schedule:
                return JSONResponse(
                    content={
                        "message": "This material is already assigned to this opening"
                    },
                    status_code=400,
                )

            # Determine raw_material_id based on material type
            if material_type == "DOOR":
                possible_raw_material_type = (
                    project_take_off_sheet_section_area_item_data.door_raw_material_type
                )
            elif material_type == "FRAME":
                possible_raw_material_type = (
                    project_take_off_sheet_section_area_item_data.frame_raw_material_type
                )
            else:
                # For HARDWARE or OTHER types, use the material's raw_material_id
                possible_raw_material_type_id = material_data.raw_material_id

            if material_type in ["DOOR", "FRAME"]:
                possible_raw_material_type_id_result = (
                    db.query(RawMaterials.id)
                    .filter(RawMaterials.code == possible_raw_material_type)
                    .first()
                )
                if possible_raw_material_type_id_result:
                    possible_raw_material_type_id = (
                        possible_raw_material_type_id_result.id
                    )
                else:
                    return JSONResponse(
                        content={
                            "message": f"Raw material type {possible_raw_material_type} not found"
                        },
                        status_code=400,
                    )

            # Get description for the opening schedule
            desc = material_data.desc
            if material_type in ["DOOR", "FRAME"]:
                desc = await get_description(
                    db,
                    project_take_off_sheet_section_area_item_data.adon_fields,
                    material_data.series,
                    possible_raw_material_type,
                    material_data.base_feature,
                    material_data.adon_feature,
                )

            # Create the opening schedule entry
            opening_schedule_data = OpeningSchedules(
                component=material_type_enum,
                desc=desc,
                total_amount=total_amount,
                total_sell_amount=total_sell_amount,
                total_base_amount=total_base_amount,
                total_extended_sell_amount=total_extended_sell_amount,
                quantity=quantity,
                final_amount=final_amount,
                final_sell_amount=final_sell_amount,
                final_base_amount=final_base_amount,
                final_extended_sell_amount=final_extended_sell_amount,
                project_material_id=project_material_id,
                raw_material_id=possible_raw_material_type_id,
                project_id=project_take_off_sheet_data.project_id,
                project_take_off_sheet_section_area_item_id=project_take_off_sheet_section_area_item_id,
                created_by=current_member.id,
            )
            db.add(opening_schedule_data)
            db.flush()

            # Update area item statistics
            take_off_sheet_section_id = await update_area_item_stats(
                db,
                project_take_off_sheet_section_area_item_id=project_take_off_sheet_section_area_item_id,
            )

            # Update section statistics
            await update_section_stats(
                db, project_take_off_sheet_section_id=take_off_sheet_section_id
            )

            # Update the sheet stats
            await update_take_off_sheet_stats(
                db, project_take_off_sheet_id=project_take_off_sheet_data.id
            )

            # Update the raw material stats
            await update_raw_material_stats(
                db, project_id=project_take_off_sheet_data.project_id
            )

            # Update the Opening's door width & height
            await update_door_width_and_height(
                db, project_take_off_sheet_section_area_item_id
            )

            return {
                "id": project_material_id,
                "message": "Project material assigned to opening.",
                "status": "success",
            }

    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def remove_material_from_opening(
    opening_schedule_id: str, current_member: Members, db: Session
):
    """**Summary:**
    Remove a material assignment from an opening.

    **Args:**
    - opening_schedule_id (str): The ID of the opening schedule entry to remove.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with success message.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Find the opening schedule entry
            opening_schedule = (
                db.query(OpeningSchedules)
                .filter(OpeningSchedules.id == opening_schedule_id)
                .first()
            )

            if not opening_schedule:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "Opening schedule not found",
                        "status": "error",
                    },
                )

            # Store the opening ID for statistics updates
            project_take_off_sheet_section_area_item_id = (
                opening_schedule.project_take_off_sheet_section_area_item_id
            )
            project_id = opening_schedule.project_id

            # Delete the opening schedule entry
            db.query(OpeningSchedules).filter(
                OpeningSchedules.id == opening_schedule_id
            ).delete()
            db.flush()

            # Update area item statistics
            take_off_sheet_section_id = await update_area_item_stats(
                db,
                project_take_off_sheet_section_area_item_id=project_take_off_sheet_section_area_item_id,
            )

            # Update section statistics
            await update_section_stats(
                db, project_take_off_sheet_section_id=take_off_sheet_section_id
            )

            # Get the take off sheet
            project_take_off_sheet_section_area_item = db.query(
                ProjectTakeOffSheetSectionAreaItems
            ).get(project_take_off_sheet_section_area_item_id)
            if project_take_off_sheet_section_area_item:
                project_take_off_sheet_data = db.query(ProjectTakeOffSheets).get(
                    project_take_off_sheet_section_area_item.project_take_off_sheet_id
                )

                if project_take_off_sheet_data:
                    # Update the sheet stats
                    await update_take_off_sheet_stats(
                        db, project_take_off_sheet_id=project_take_off_sheet_data.id
                    )

                    # Update the raw material stats
                    await update_raw_material_stats(
                        db, project_id=project_take_off_sheet_data.project_id
                    )

            # Update the Opening's door width & height
            await update_door_width_and_height(
                db, project_take_off_sheet_section_area_item_id
            )

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Material removed from opening successfully",
                    "status": "success",
                },
            )

    except Exception as error:
        logger.exception(f"remove_material_from_opening error: {error}")
        db.rollback()
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def add_material(
    material_req_data: ProjectMaterialRequest,
    project_take_off_sheet_section_area_item_id: str,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    This module is responsible for creating a project material for a project opening.

    **Args:**
    - material_req_data (dict): project material create data.
    - `project_take_off_sheet_section_area_item_id` (str): project_take_off_sheet_section_area_item id for which we are going to add the project material.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): created project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            material_type = None
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            print(">>>>>>>>>>>>>>>>>>", material_req_data)
            if "material_type" in material_req_data:
                material_req_data["created_by"] = current_member.id
                total_amount = material_req_data["total_amount"]
                quantity = material_req_data["quantity"]
                final_amount = total_amount * quantity
                if "quantity" in material_req_data:
                    del material_req_data["quantity"]
                project_take_off_sheet_section_area_item_data = db.query(
                    ProjectTakeOffSheetSectionAreaItems
                ).get(project_take_off_sheet_section_area_item_id)
                project_take_off_sheet_data = db.query(ProjectTakeOffSheets).get(
                    project_take_off_sheet_section_area_item_data.project_take_off_sheet_id
                )
                if material_req_data["material_type"] == "HARDWARE":
                    short_code = material_req_data["short_code"]
                    project_short_code_exist = await is_short_code_exists(
                        project_take_off_sheet_data.project_id, short_code, db
                    )
                else:
                    project_short_code_exist = False
                if not project_short_code_exist:
                    # We need the opening's raw_material type based on DOOR/FRAME
                    if material_req_data["material_type"] == "DOOR":
                        material_type = "DOOR"
                        possible_raw_material_type = (
                            project_take_off_sheet_section_area_item_data.door_raw_material_type
                        )
                    elif material_req_data["material_type"] == "FRAME":
                        material_type = "FRAME"
                        possible_raw_material_type = (
                            project_take_off_sheet_section_area_item_data.frame_raw_material_type
                        )
                    possible_raw_material_type_id = (
                        db.query(RawMaterials.id)
                        .filter(RawMaterials.code == possible_raw_material_type)
                        .first()
                    )
                    material_req_data["raw_material_id"] = (
                        possible_raw_material_type_id.id
                    )
                    # We need to apply the markup, margin, discount, surcharge automatically based on an exisiting project_material
                    add_estimation_breakups_to_project(db, material_req_data)
                    desc = None
                    if material_req_data["material_type"] in ["DOOR", "FRAME"]:
                        desc = await get_description(
                            db,
                            project_take_off_sheet_section_area_item_data.adon_fields,
                            material_req_data["series"],
                            possible_raw_material_type,
                            material_req_data["base_feature"],
                            material_req_data["adon_feature"],
                        )
                        material_req_data["desc"] = desc
                    # This section is going to add the project material
                    material_data = ProjectMaterials(**material_req_data)
                    db.add(material_data)
                    db.flush()
                    project_material_id = material_data.id
                    material_costs = await update_material_charges(
                        db, project_material_id, return_updated_values=True
                    )
                    # calculate the total base cost and sell cost and final base cost and final base cost sell cost
                    if material_costs is not None:
                        total_sell_amount = material_costs["total_sell_amount"]
                        total_base_amount = material_costs["total_base_amount"]
                        total_extended_sell_amount = material_costs[
                            "total_extended_sell_amount"
                        ]
                        final_sell_amount = quantity * total_sell_amount
                        final_base_amount = quantity * total_base_amount
                        final_extended_sell_amount = (
                            quantity * total_extended_sell_amount
                        )
                    else:
                        total_sell_amount = total_amount
                        total_base_amount = total_amount
                        total_extended_sell_amount = total_amount
                        final_sell_amount = quantity * total_sell_amount
                        final_base_amount = quantity * total_base_amount
                        final_extended_sell_amount = (
                            quantity * total_extended_sell_amount
                        )
                    # This section is going to add the relation between project material and openning
                    openning_schedule_data = OpeningSchedules(
                        component=material_req_data["material_type"],
                        desc=desc,
                        total_amount=total_amount,
                        total_sell_amount=total_sell_amount,
                        total_base_amount=total_base_amount,
                        total_extended_sell_amount=total_extended_sell_amount,
                        quantity=quantity,
                        final_amount=final_amount,
                        final_sell_amount=final_sell_amount,
                        final_base_amount=final_base_amount,
                        final_extended_sell_amount=final_extended_sell_amount,
                        project_material_id=project_material_id,
                        raw_material_id=possible_raw_material_type_id.id,
                        project_id=project_take_off_sheet_data.project_id,
                        project_take_off_sheet_section_area_item_id=project_take_off_sheet_section_area_item_id,
                        created_by=current_member.id,
                    )
                    db.add(openning_schedule_data)
                    db.flush()

                    # Update area item statistics related to the hardware group
                    take_off_sheet_section_id = await update_area_item_stats(
                        db,
                        project_take_off_sheet_section_area_item_id=project_take_off_sheet_section_area_item_id,
                    )

                    # Update section statistics related to the hardware group
                    await update_section_stats(
                        db, project_take_off_sheet_section_id=take_off_sheet_section_id
                    )

                    # update the sheet stats after deleting the section area and its associated openings
                    await update_take_off_sheet_stats(
                        db, project_take_off_sheet_id=project_take_off_sheet_data.id
                    )

                    # update the raw material stats after deleting the section area and its associated openings
                    await update_raw_material_stats(
                        db, project_id=project_take_off_sheet_data.project_id
                    )

                    # update the Opening's door width & height
                    await update_door_width_and_height(
                        db, project_take_off_sheet_section_area_item_id
                    )

                    return {
                        "id": project_material_id,
                        "message": "project material Added.",
                        "status": "success",
                    }
                else:
                    return JSONResponse(
                        content={
                            "message": "Short Code already exits in the current project"
                        },
                        status_code=400,
                    )
            else:
                return JSONResponse(
                    content={"message": "Material type is not selected"},
                    status_code=500,
                )
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


# TODO insed of ID we are sending project_material_id in the paramiter
async def update_material(
    material_req_data: ProjectMaterialRequest, current_member: Members, db: Session
):
    """**Summary:**
    This module is responsible for updating a project material.

    **Args:**
    - material_req_data (dict): project material update data.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): updated project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Extract relevant data from the request payload
            material_req_data = material_req_data.model_dump(exclude_unset=True)

            # Check if 'id' field is present in the payload
            if not "id" in material_req_data:
                return JSONResponse(
                    content={"message": "Invalid request payload."}, status_code=400
                )

            # Fetch project material data and associated opening data
            project_material_data = db.query(ProjectMaterials).get(
                material_req_data["id"]
            )
            mat_type = project_material_data.material_type.value
            material_type_enum = COMPONENTS(mat_type)
            project_material_opening_schedule = (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.project_material_id == project_material_data.id,
                    OpeningSchedules.component == material_type_enum,
                )
                .first()
            )

            if not project_material_opening_schedule:
                return JSONResponse(
                    content={"message": "Not a Valid Project Material"}, status_code=400
                )

            # Calculate final amount based on total amount and quantity
            final_amount = None
            if "total_amount" in material_req_data:
                total_amount = material_req_data["total_amount"]
            else:
                total_amount = project_material_data.total_amount
            if "quantity" in material_req_data:
                quantity = material_req_data["quantity"]
                del material_req_data["quantity"]
            else:
                quantity = project_material_opening_schedule.quantity
            final_amount = total_amount * quantity

            # Check and update shortcode if provided
            # if project_material_data.material_type == "HARDWARE" and "short_code" in material_req_data:
            #     short_code = material_req_data["short_code"]
            #     project_short_code_exist = await is_short_code_exists(project_material_opening_schedule.project_id, short_code, db)
            #     if project_short_code_exist:
            #         return JSONResponse(content={"message": "Shortcode Already in used"}, status_code=400)

            # Update material data with current member's ID
            project_take_off_sheet_section_area_item_data = db.query(
                ProjectTakeOffSheetSectionAreaItems
            ).get(
                project_material_opening_schedule.project_take_off_sheet_section_area_item_id
            )
            desc = None
            if mat_type in ["DOOR", "FRAME"]:
                desc = await get_description(
                    db,
                    project_take_off_sheet_section_area_item_data.adon_fields,
                    material_req_data["series"],
                    (
                        project_take_off_sheet_section_area_item_data.door_raw_material_type
                        if mat_type == "DOOR"
                        else project_take_off_sheet_section_area_item_data.frame_raw_material_type
                    ),
                    material_req_data["base_feature"],
                    material_req_data["adon_feature"],
                )
                material_req_data["desc"] = desc
            material_req_data["updated_by"] = current_member.id
            for key, value in material_req_data.items():
                setattr(project_material_data, key, value)
            project_material_opening_schedule.desc = desc
            db.flush()

            material_costs = await update_material_charges(
                db, project_material_data.id, return_updated_values=True
            )
            # calculate the total base cost and sell cost and final base cost and final base cost sell cost
            if material_costs is not None:
                total_sell_amount = material_costs["total_sell_amount"]
                total_base_amount = material_costs["total_base_amount"]
                total_extended_sell_amount = material_costs[
                    "total_extended_sell_amount"
                ]
                final_sell_amount = quantity * total_sell_amount
                final_base_amount = quantity * total_base_amount
                final_extended_sell_amount = quantity * total_extended_sell_amount
            else:
                total_sell_amount = total_amount
                total_base_amount = total_amount
                total_extended_sell_amount = total_amount
                final_sell_amount = quantity * total_sell_amount
                final_base_amount = quantity * total_base_amount
                final_extended_sell_amount = quantity * total_extended_sell_amount

            # Update project material data if final amount is not none
            if final_amount:
                project_material_opening_schedule.total_amount = total_amount
                project_material_opening_schedule.total_sell_amount = total_sell_amount
                project_material_opening_schedule.total_base_amount = total_base_amount
                project_material_opening_schedule.total_extended_sell_amount = (
                    total_extended_sell_amount
                )
                project_material_opening_schedule.quantity = quantity
                project_material_opening_schedule.final_amount = final_amount
                project_material_opening_schedule.final_sell_amount = final_sell_amount
                project_material_opening_schedule.final_base_amount = final_base_amount
                project_material_opening_schedule.final_extended_sell_amount = (
                    final_extended_sell_amount
                )

            # Update area item statistics related to the hardware group
            take_off_sheet_section_id = await update_area_item_stats(
                db,
                project_take_off_sheet_section_area_item_id=project_material_opening_schedule.project_take_off_sheet_section_area_item_id,
            )

            # Update section statistics related to the hardware group
            await update_section_stats(
                db, project_take_off_sheet_section_id=take_off_sheet_section_id
            )

            project_take_off_data = (
                db.query(ProjectTakeOffSheets)
                .filter(
                    ProjectTakeOffSheets.project_id == project_material_data.project_id
                )
                .first()
            )

            # update the sheet stats after deleting the section area and its associated openings
            await update_take_off_sheet_stats(
                db, project_take_off_sheet_id=project_take_off_data.id
            )

            # update the raw material stats after deleting the section area and its associated openings
            await update_raw_material_stats(
                db, project_id=project_take_off_data.project_id
            )

            # update the Opening's door width & height
            await update_door_width_and_height(
                db,
                project_material_opening_schedule.project_take_off_sheet_section_area_item_id,
            )

            # Return success message and updated material ID
            return {
                "id": material_req_data["id"],
                "message": "Project material updated.",
                "status": "success",
            }

    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def clone_opening_material(
    opening_schedule_id: str, current_member: Members, db: Session
):
    """**Summary:**
    This module is responsible for clonning  a opening schedule material for a project opening.

    **Args:**
    - opening_schedule_id (str): opening_schedule_id which we want to clone.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): created opening schedule id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            opening_schedule_data = db.query(OpeningSchedules).get(opening_schedule_id)
            if opening_schedule_data.component.value == "DOOR":
                # add new project material
                project_material_id = opening_schedule_data.project_material_id
                project_material_data = db.query(ProjectMaterials).get(
                    project_material_id
                )
                project_material_data_dict = project_material_data.to_dict
                project_material_data_dict["created_by"] = current_member.id
                # Remove unnecessary fields
                if "id" in project_material_data_dict:
                    del project_material_data_dict["id"]
                if "created_at" in project_material_data_dict:
                    del project_material_data_dict["created_at"]
                if "updated_at" in project_material_data_dict:
                    del project_material_data_dict["updated_at"]
                if "updated_by" in project_material_data_dict:
                    del project_material_data_dict["updated_by"]
                # Create a new entry in the project paterial table
                new_project_material_data = ProjectMaterials(
                    **project_material_data_dict
                )
                db.add(new_project_material_data)
                db.flush()

                opening_schedule_data_dict = opening_schedule_data.to_dict
                opening_schedule_data_dict["project_material_id"] = (
                    new_project_material_data.id
                )
                opening_schedule_data_dict["created_by"] = current_member.id
                # Remove unnecessary fields
                if "id" in opening_schedule_data_dict:
                    del opening_schedule_data_dict["id"]
                if "created_at" in opening_schedule_data_dict:
                    del opening_schedule_data_dict["created_at"]
                if "updated_at" in opening_schedule_data_dict:
                    del opening_schedule_data_dict["updated_at"]
                if "updated_by" in opening_schedule_data_dict:
                    del opening_schedule_data_dict["updated_by"]

                # Create a new entry in the OpeningSchedules table
                new_opening_opening_schedule_data = OpeningSchedules(
                    **opening_schedule_data_dict
                )
                db.add(new_opening_opening_schedule_data)
                db.flush()

                # Update area item statistics related to the hardware group
                take_off_sheet_section_id = await update_area_item_stats(
                    db,
                    project_take_off_sheet_section_area_item_id=opening_schedule_data.project_take_off_sheet_section_area_item_id,
                )

                # Update section statistics related to the hardware group
                project_take_off_sheet_id = await update_section_stats(
                    db, project_take_off_sheet_section_id=take_off_sheet_section_id
                )

                # update the sheet stats after deleting the section area and its associated openings
                project_id = await update_take_off_sheet_stats(
                    db, project_take_off_sheet_id=project_take_off_sheet_id
                )

                # update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(db, project_id=project_id)

                # update the Opening's door width & height
                await update_door_width_and_height(
                    db,
                    opening_schedule_data.project_take_off_sheet_section_area_item_id,
                )

                return {
                    "id": new_opening_opening_schedule_data.id,
                    "message": "project material clonned",
                    "status": "success",
                }
            else:
                return JSONResponse(
                    content={"message": "Cloning not allowed"}, status_code=400
                )
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def delete_material(material_id: str, current_member: Members, db: Session):
    """**Summary:**
    This module is responsible for deleting a project material.

    **Args:**
    - material_id (str): project material id which we need to delete.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Fetch project material data and associated opening data
            project_material_data = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.id == material_id,
                    ProjectMaterials.is_deleted == False,
                )
                .first()
            )
            if not project_material_data:
                return JSONResponse(
                    content={"message": "Invalid delete request."}, status_code=400
                )

            if project_material_data.material_type.value == "HARDWARE":
                return JSONResponse(
                    content={"message": "Can't Delete HW item from here."},
                    status_code=400,
                )

            # collect all openings to which this material is associated with
            project_material_opening_schedule = (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.project_material_id == material_id,
                )
                .all()
            )

            deleted_opening_ids = []
            for opening in project_material_opening_schedule:
                deleted_opening_ids.append(
                    opening.project_take_off_sheet_section_area_item_id
                )
            # delte the opening sechedule
            db.query(OpeningSchedules).filter(
                OpeningSchedules.project_material_id == material_id
            ).delete()
            # get unique opening ids
            deleted_opening_ids = list(set(deleted_opening_ids))

            # delete the project material
            project_material_data.is_deleted = True
            project_material_data.deleted_at = datetime.now()
            project_material_data.deleted_by = current_member.id

            # Update stats for associated opening
            for deleted_opening_id in deleted_opening_ids:
                take_off_sheet_section_id = await update_area_item_stats(
                    db, project_take_off_sheet_section_area_item_id=deleted_opening_id
                )
                # Update section statistics related to the hardware group
                await update_section_stats(
                    db, project_take_off_sheet_section_id=take_off_sheet_section_id
                )

            project_take_off_data = (
                db.query(ProjectTakeOffSheets)
                .filter(
                    ProjectTakeOffSheets.project_id == project_material_data.project_id
                )
                .first()
            )

            # update the sheet stats after deleting the section area and its associated openings
            await update_take_off_sheet_stats(
                db, project_take_off_sheet_id=project_take_off_data.id
            )

            # update the raw material stats after deleting the section area and its associated openings
            await update_raw_material_stats(
                db, project_id=project_material_data.project_id
            )

            # update the Opening's door width & height
            for project_take_off_sheet_section_area_item_id in deleted_opening_ids:
                await update_door_width_and_height(
                    db, project_take_off_sheet_section_area_item_id
                )

            return {
                "message": "Project material delted successfully.",
                "status": "success",
            }

    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def get_materials(db: Session, project_id: str, material_type: str, keyword: str, raw_material_id: str):
    """**Summary:**
    This method is responsible for retreaving materials list depending on the input keyword and type

    This method fetches a subset of materials from the database based on the specified type and short code.

    **Args:**
    - db: The database session object.
    - material_type (str): material type we need.
    - keyword (str): this will be usefull for keyword search on short code.
    - raw_material_id (str, optional): when set, restrict to this raw material id.
    """
    try:
        filters = [
            ProjectMaterials.is_deleted == False,
            ProjectMaterials.material_type == material_type,
            ProjectMaterials.project_id == project_id,
        ]
        if raw_material_id:
            filters.append(ProjectMaterials.raw_material_id == raw_material_id)
        if keyword is not None:
            filters.append(or_(ProjectMaterials.short_code.ilike(f"%{keyword}%")))

        items = (
            db.query(ProjectMaterials)
            .filter(*filters)
            .order_by(ProjectMaterials.created_at.asc())
            .all()
        )

        material_opening_numbers_map = await get_associated_opening_numbers_by_materials(
            db=db,
            project_material_ids=[item.id for item in items],
        )

        data = []
        for item in items:
            item_dict = item.to_dict
            item_dict["raw_material_code"] = (
                item.raw_material.code
                if item.raw_material
                else None
            )
            item_dict["material_manufacturer"] = (
                item.material_manufacturer.to_dict
                if item.material_manufacturer
                else None
            )
            item_dict["material_brand"] = (
                item.material_brand.to_dict
                if item.material_brand
                else None
            )
            

            item_dict["product_category"] = (
                {
                    "category": {
                        "id": item.take_off_hardware_product_category.id,
                        "name": item.take_off_hardware_product_category.name,
                    }
                }
                if item.take_off_hardware_product_category
                else None
            )
            item_dict["opening_numbers"] = material_opening_numbers_map.get(str(item.id), [])
            data.append(item_dict)

        response = {"data": data, "status": "success"}
        return response
    except Exception as e:
        logger.exception("get_materials:: error - " + str(e))
        raise e


async def get_associated_opening_numbers_by_materials(
    db: Session, project_material_ids: list
):
    """Return opening_number list grouped by project material id."""
    try:
        if not project_material_ids:
            return {}

        rows = (
            db.query(
                OpeningSchedules.project_material_id,
                ProjectTakeOffSheetSectionAreaItems.opening_number,
            )
            .join(
                ProjectTakeOffSheetSectionAreaItems,
                OpeningSchedules.project_take_off_sheet_section_area_item_id
                == ProjectTakeOffSheetSectionAreaItems.id,
            )
            .filter(
                OpeningSchedules.project_material_id.in_(project_material_ids),
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False,
            )
            .all()
        )

        opening_numbers_by_material = defaultdict(list)
        for material_id, opening_number in rows:
            material_id = str(material_id) if material_id else None
            if not material_id or not opening_number:
                continue
            if opening_number not in opening_numbers_by_material[material_id]:
                opening_numbers_by_material[material_id].append(opening_number)

        return dict(opening_numbers_by_material)
    except Exception as e:
        logger.exception(
            "get_associated_opening_numbers_by_materials:: error - " + str(e)
        )
        raise e


async def add_manufacturer_material_mapping(
    manu_material_req_data: RawMaterialMappingRequest,
    manufacturer_code: str,
    brand_code: str,
    db: Session,
):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Resolve brand and manufacturer IDs
            brand_id = None
            if brand_code:
                brand_data = db.query(Brands).filter(Brands.code == brand_code).first()
                if not brand_data:
                    return JSONResponse(
                        content={"message": f"No brand found with code: {brand_code}"},
                        status_code=400,
                    )
                manufacturer_id = brand_data.manufacturer_id
                brand_id = brand_data.id
            else:
                manufacturer_data = (
                    db.query(Manufacturers)
                    .filter(Manufacturers.code == manufacturer_code)
                    .first()
                )
                if not manufacturer_data:
                    return JSONResponse(
                        content={
                            "message": f"No manufacturer found with code: {manufacturer_code}"
                        },
                        status_code=400,
                    )
                manufacturer_id = manufacturer_data.id

            # Insert or update raw material mappings
            for item in manu_material_req_data.mapping_data:
                existing = (
                    db.query(RawMaterialCatalogMapping)
                    .filter_by(
                        raw_material_id=item.raw_material_id,
                        manufacturer_id=manufacturer_id,
                        brand_id=brand_id,
                    )
                    .first()
                )
                if existing:
                    # Update existing record
                    existing.discount_percentage = item.default_discount
                    existing.has_data = item.has_data
                else:
                    # Create new mapping
                    new_mapping = RawMaterialCatalogMapping(
                        manufacturer_id=manufacturer_id,
                        brand_id=brand_id,
                        raw_material_id=item.raw_material_id,
                        discount_percentage=item.default_discount,
                        has_data=item.has_data,
                    )
                    db.add(new_mapping)

            return JSONResponse(
                status_code=201,
                content={
                    "message": "Manufacturer material mappings added successfully.",
                    "status": "success",
                },
            )

    except SQLAlchemyError as db_err:
        logger.exception(f"Database error occurred: {db_err}")
        db.rollback()
        raise db_err

    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def get_manufacturer_material_mappings(
    manufacturer_code: str, brand_code: str, db: Session
):
    try:
        # Get manufacturer
        manufacturer = db.query(Manufacturers).filter_by(code=manufacturer_code).first()
        if not manufacturer:
            return JSONResponse(
                content={"message": f"Manufacturer '{manufacturer_code}' not found"},
                status_code=400,
            )

        manufacturer_id = manufacturer.id
        brand_id = None

        if brand_code:
            brand = db.query(Brands).filter_by(code=brand_code).first()
            if not brand:
                return JSONResponse(
                    content={"message": f"Brand '{brand_code}' not found"},
                    status_code=400,
                )
            brand_id = brand.id

        query = (
            db.query(RawMaterialCatalogMapping, RawMaterials)
            .outerjoin(
                RawMaterials,
                RawMaterialCatalogMapping.raw_material_id == RawMaterials.id,
            )
            .filter(RawMaterialCatalogMapping.manufacturer_id == manufacturer_id)
        )

        if brand_id:
            query = query.filter(RawMaterialCatalogMapping.brand_id == brand_id)
        else:
            query = query.filter(RawMaterialCatalogMapping.brand_id == None)

        results = query.all()

        # Format response
        response_data = []
        for mapping, material in results:
            material_data = {
                "id": material.id if material else None,
                "item_number": material.item_number if material else None,
                "code": material.code if material else None,
                "name": material.name if material else None,
                "desc": material.desc if material else None,
                "sort_order": material.sort_order if material else None,
            }

            response_data.append(
                {
                    "id": mapping.id,
                    "manufacturer_id": mapping.manufacturer_id,
                    "brand_id": mapping.brand_id,
                    "raw_material_id": mapping.raw_material_id,
                    "discount_percentage": mapping.discount_percentage,
                    "has_data": mapping.has_data,
                    "accepted_types": mapping.accepted_types,
                    "sort_order": mapping.sort_order,
                    "raw_material": material_data,
                }
            )

        return JSONResponse(
            status_code=200, content={"data": response_data, "status": "success"}
        )

    except Exception as error:
        logger.exception(
            f"Unexpected error in get_manufacturer_material_mappings: {error}"
        )
        return JSONResponse(
            content={"message": "Internal server error"}, status_code=500
        )


async def set_pricebook_available(
    manufacturer_code: str, brand_code: str = None, db: Session = None
):
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            manufacturer = (
                db.query(Manufacturers).filter_by(code=manufacturer_code).first()
            )
            if not manufacturer:
                return JSONResponse(
                    content={
                        "message": f"Manufacturer '{manufacturer_code}' not found"
                    },
                    status_code=400,
                )

            manufacturer_id = manufacturer.id
            brand_id = None

            if brand_code:
                brand = db.query(Brands).filter_by(code=brand_code).first()
                if not brand:
                    return JSONResponse(
                        content={"message": f"Brand '{brand_code}' not found"},
                        status_code=400,
                    )
                brand_id = brand.id

            # Build base query
            query = db.query(RawMaterialCatalogMapping).filter(
                RawMaterialCatalogMapping.manufacturer_id == manufacturer_id
            )

            if brand_id:
                query = query.filter(RawMaterialCatalogMapping.brand_id == brand_id)
            else:
                query = query.filter(RawMaterialCatalogMapping.brand_id == None)

            query.update(
                {RawMaterialCatalogMapping.has_data: True}, synchronize_session=False
            )

            return JSONResponse(
                status_code=200,
                content={
                    "message": "manufacturer material mapping updated successfully.",
                    "status": "success",
                },
            )

    except SQLAlchemyError as db_err:
        logger.exception(f"Database error occurred: {db_err}")
        db.rollback()
        return JSONResponse(content={"message": "Database error"}, status_code=500)

    except Exception as error:
        logger.exception(f"Unexpected error in set_pricebook_available: {error}")
        db.rollback()
        return JSONResponse(
            content={"message": "Internal server error"}, status_code=500
        )


async def list_raw_materials(db: Session):
    try:
        raw_materials = (
            db.query(RawMaterials).order_by(RawMaterials.sort_order.asc()).all()
        )

        data = [
            material.to_dict for material in raw_materials if material.code != "INST"
        ]

        return JSONResponse(
            status_code=200, content={"status": "success", "data": data}
        )

    except Exception as error:
        logger.exception(f"Unexpected error in list_raw_materials: {error}")
        return JSONResponse(
            content={"message": "Internal server error"}, status_code=500
        )


async def create_project_material(
    material_req_data: ProjectMaterialRequest, current_member: Members, db: Session,
    return_project_material_id: bool = False
):
    """**Summary:**
    Create a simple project material entry without complex business logic.

    **Args:**
    - material_req_data (ProjectMaterialRequest): project material create data.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with project_material_id and success message.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Convert request data to dict, excluding unset fields
            material_data = material_req_data.model_dump(exclude_unset=True)
            print(">>>>>>>>>>>>>>>>>> material_data", material_data)
            if not "raw_material_id" in material_data:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "raw_material_id is required",
                        "status": "error",
                    },
                )
            # Validate shortcode uniqueness if provided
            if "short_code" in material_data and "project_id" in material_data:
                short_code = material_data["short_code"]
                project_id = material_data["project_id"]
                project_short_code_exist = await is_short_code_exists(
                    project_id, short_code, db
                )
                if project_short_code_exist:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "message": "Short code already exists in the current project",
                            "status": "error",
                        },
                    )

            # Set created_by field
            material_data["created_by"] = current_member.id

            # Remove quantity if present (not a column in ProjectMaterials)
            if "quantity" in material_data:
                del material_data["quantity"]

            # Handle product_category for hardware materials
            if "product_category" in material_data:
                # Check if this is a hardware material
                material_type = material_data.get("material_type")
                if material_type == "HARDWARE":
                    # Manage product category of the hardware
                    product_category = material_data["product_category"]
                    material_data["hardware_product_category_id"] = (
                        await add_category_info(db, product_category)
                    )
                del material_data["product_category"]

            # Apply estimation breakups (markup, margin, discount, surcharge) from existing project materials
            if "project_id" in material_data and "raw_material_id" in material_data:
                add_estimation_breakups_to_project(db, material_data)

            if material_data.get("material_type") in ["DOOR", "FRAME"]:
                raw_material_type_data = (
                    db.query(RawMaterials.code)
                    .filter(RawMaterials.id == material_data["raw_material_id"])
                    .first()
                )
                if raw_material_type_data and raw_material_type_data.code:
                    adon_fields = material_data.get("adon_fields")
                    combination_key = _get_material_description_combination_key(
                        effective_material_type=material_data["material_type"],
                        raw_material_type=raw_material_type_data.code,
                        effective_series=material_data.get("series"),
                        effective_base_feature=material_data.get("base_feature"),
                        effective_adon_feature=material_data.get("adon_feature"),
                        adon_fields=adon_fields if isinstance(adon_fields, dict) else None,
                    )
                    print(">>>>>>>>>>>>>>>>>> combination_key", combination_key)
                    material_desc_row = (
                        db.query(MaterialDescription)
                        .filter(
                            MaterialDescription.combination_key == combination_key
                        )
                        .first()
                    )
                    if material_desc_row and material_desc_row.desc:
                        material_data["desc"] = material_desc_row.desc
                        print(">>>>>>>>>>>>>>>>>> material_desc_row present", material_data["desc"])
                    else:
                        desc = await get_description(
                            db=db,
                            adon_fields=adon_fields if isinstance(adon_fields, dict) else {},
                            series=material_data.get("series"),
                            material_code=raw_material_type_data.code,
                            base_feature=material_data.get("base_feature"),
                            adon_feature=material_data.get("adon_feature"),
                        )
                        material_data["desc"] = desc
                        print(">>>>>>>>>>>>>>>>>> new desc", material_data["desc"])
                        db.add(
                            MaterialDescription(
                                material_type=material_data["material_type"],
                                raw_material_type=raw_material_type_data.code,
                                series=material_data.get("series"),
                                base_feature=material_data.get("base_feature"),
                                adon_feature=material_data.get("adon_feature"),
                                adon_fields=adon_fields if isinstance(adon_fields, dict) else None,
                                combination_key=combination_key,
                                desc=desc,
                            )
                        )


            # Create the project material
            new_material = ProjectMaterials(**material_data)
            db.add(new_material)
            db.flush()

            project_material_id = new_material.id
            await update_material_charges(
                db, project_material_id, return_updated_values=False
            )

            if return_project_material_id:
                return project_material_id
            else:
                return JSONResponse(
                    status_code=201,
                    content={
                        "message": "Project material created successfully",
                        "status": "success",
                        "project_material_id": str(new_material.id),
                    },
                )

    except Exception as error:
        logger.exception(f"create_project_material error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def update_project_material(
    material_id: str,
    material_req_data: ProjectMaterialRequest,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    Update an existing project material entry.

    **Args:**
    - material_id (str): The ID of the project material to update.
    - material_req_data (ProjectMaterialRequest): Updated project material data.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with success message and project_material_id.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Find the existing project material
            existing_material = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.id == material_id,
                    ProjectMaterials.is_deleted == False,
                )
                .first()
            )

            if not existing_material:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "Project material not found",
                        "status": "error",
                    },
                )

            # Convert request data to dict, excluding unset fields
            update_data = material_req_data.model_dump(exclude_unset=True)

            # Validate shortcode uniqueness if being updated
            if "short_code" in update_data:
                short_code = update_data["short_code"]
                project_id = existing_material.project_id
                project_short_code_exist = await is_short_code_exists(
                    project_id, short_code, db, exclude_id=material_id
                )
                if project_short_code_exist:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "message": "Short code already exists in the current project",
                            "status": "error",
                        },
                    )

            # Set updated_by field
            update_data["updated_by"] = current_member.id
            update_data["updated_at"] = datetime.now()

            # Remove fields that shouldn't be updated directly
            if "quantity" in update_data:
                del update_data["quantity"]

            # Handle product_category for hardware materials
            if "product_category" in update_data:
                # Check if this is a hardware material
                material_type = (
                    existing_material.material_type.value
                    if hasattr(existing_material.material_type, "value")
                    else existing_material.material_type
                )
                if material_type == "HARDWARE":
                    # Manage product category of the hardware
                    product_category = update_data["product_category"]
                    update_data["hardware_product_category_id"] = (
                        await add_category_info(db, product_category)
                    )
                del update_data["product_category"]

            if "id" in update_data:
                del update_data["id"]

            # Reapply estimation breakups if manufacturer, brand, or raw_material is being changed
            if (
                "manufacturer_id" in update_data
                or "brand_id" in update_data
                or "raw_material_id" in update_data
            ):
                # Prepare data for breakup calculation
                breakup_data = {
                    "project_id": existing_material.project_id,
                    "raw_material_id": update_data.get(
                        "raw_material_id", existing_material.raw_material_id
                    ),
                    "manufacturer_id": update_data.get(
                        "manufacturer_id", existing_material.manufacturer_id
                    ),
                    "brand_id": update_data.get("brand_id", existing_material.brand_id),
                }
                add_estimation_breakups_to_project(db, breakup_data)
                # Apply the calculated breakups to update_data
                for key in [
                    "margin",
                    "markup",
                    "surcharge_type",
                    "surcharge",
                    "discount_type",
                    "discount_is_basic",
                    "discount",
                ]:
                    if key in breakup_data:
                        update_data[key] = breakup_data[key]

            existing_material_type = (
                existing_material.material_type.value
                if hasattr(existing_material.material_type, "value")
                else existing_material.material_type
            )
            effective_material_type = update_data.get(
                "material_type", existing_material_type
            )
            if hasattr(effective_material_type, "value"):
                effective_material_type = effective_material_type.value

            # For DOOR/FRAME updates, reuse description from cache by combination.
            # Generate and cache only when no cached description exists and desc isn't explicitly provided.
            if effective_material_type in ["DOOR", "FRAME"]:
                effective_raw_material_id = update_data.get(
                    "raw_material_id", existing_material.raw_material_id
                )
                raw_material_row = (
                    db.query(RawMaterials.code)
                    .filter(RawMaterials.id == effective_raw_material_id)
                    .first()
                )
                if raw_material_row and raw_material_row.code:
                    adon_fields = update_data.get("adon_fields", None)
                    if adon_fields is not None and not isinstance(adon_fields, dict):
                        adon_fields = {}

                    effective_series = update_data.get("series", existing_material.series)
                    effective_base_feature = update_data.get(
                        "base_feature", existing_material.base_feature
                    )
                    effective_adon_feature = update_data.get(
                        "adon_feature", existing_material.adon_feature
                    )
                    combination_key = _get_material_description_combination_key(
                        effective_material_type=effective_material_type.value if hasattr(effective_material_type, "value") else effective_material_type,
                        raw_material_type=raw_material_row.code,
                        effective_series=effective_series,
                        effective_base_feature=effective_base_feature,
                        effective_adon_feature=effective_adon_feature,
                        adon_fields=adon_fields if isinstance(adon_fields, dict) else None,
                    )
                    print(">>>>>>>>>>>>>>>>>> combination_key", combination_key)
                    material_desc_row = (
                        db.query(MaterialDescription)
                        .filter(MaterialDescription.combination_key == combination_key)
                        .first()
                    )
                    if material_desc_row and material_desc_row.desc:
                        update_data["desc"] = material_desc_row.desc
                    elif not material_desc_row:
                        generated_desc = await get_description(
                            db,
                            adon_fields if isinstance(adon_fields, dict) else {},
                            effective_series,
                            raw_material_row.code,
                            effective_base_feature,
                            effective_adon_feature,
                        )
                        update_data["desc"] = generated_desc
                        print(">>>>>>>>>>>>>>>>>> new desc", update_data["desc"])
                        db.add(
                            MaterialDescription(
                                material_type=effective_material_type,
                                raw_material_type=raw_material_row.code,
                                series=effective_series,
                                base_feature=effective_base_feature,
                                adon_feature=effective_adon_feature,
                                adon_fields=adon_fields if isinstance(adon_fields, dict) else None,
                                combination_key=combination_key,
                                desc=generated_desc,
                            )
                        )

            # Update the project material
            db.query(ProjectMaterials).filter(
                ProjectMaterials.id == material_id
            ).update(update_data)

            db.flush()

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Project material updated successfully",
                    "status": "success",
                    "project_material_id": material_id,
                },
            )

    except Exception as error:
        logger.exception(f"update_project_material error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def delete_project_material(
    material_id: str, current_member: Members, db: Session
):
    """**Summary:**
    Soft delete a project material entry.

    **Args:**
    - material_id (str): The ID of the project material to delete.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with success message.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Find the existing project material
            existing_material = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.id == material_id,
                    ProjectMaterials.is_deleted == False,
                )
                .first()
            )

            if not existing_material:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "Project material not found",
                        "status": "error",
                    },
                )

            # Check if material is assigned based on material type
            material_type = existing_material.material_type.value

            if material_type == "HARDWARE":
                # For hardware materials, check only in hardware groups
                assigned_to_hardware_group = (
                    db.query(HardwareGroupMaterials)
                    .filter(HardwareGroupMaterials.project_material_id == material_id)
                    .first()
                )

                if assigned_to_hardware_group:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "message": "Cannot delete material. It is currently assigned to one or more hardware groups. Please remove the material from all hardware groups before deleting.",
                            "status": "error",
                        },
                    )
            else:
                # For door/frame materials, check only in opening schedules
                assigned_to_opening = (
                    db.query(OpeningSchedules)
                    .filter(OpeningSchedules.project_material_id == material_id)
                    .first()
                )

                if assigned_to_opening:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "message": "Cannot delete material. It is currently assigned to one or more openings. Please remove the material from all openings before deleting.",
                            "status": "error",
                        },
                    )

            # Soft delete the material
            update_data = {
                "is_deleted": True,
                "deleted_at": datetime.now(),
                "deleted_by": current_member.id,
            }

            db.query(ProjectMaterials).filter(
                ProjectMaterials.id == material_id
            ).update(update_data)
            db.flush()

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Project material deleted successfully",
                    "status": "success",
                    "project_material_id": material_id,
                },
            )

    except Exception as error:
        logger.exception(f"delete_project_material error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def clone_project_material(
    material_id: str, short_code: str, current_member: Members, db: Session
):
    """**Summary:**
    Clone an existing project material to create a new copy.

    **Args:**
    - material_id (str): The ID of the project material to clone.
    - short_code (str): The short code for the cloned material.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with new project_material_id.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Find the existing project material
            existing_material = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.id == material_id,
                    ProjectMaterials.is_deleted == False,
                )
                .first()
            )

            if not existing_material:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "Project material not found",
                        "status": "error",
                    },
                )

            # Validate the provided short_code for uniqueness
            project_id = existing_material.project_id
            short_code_exists = await is_short_code_exists(project_id, short_code, db)
            if short_code_exists:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "Short code already exists in the current project",
                        "status": "error",
                    },
                )

            # Create a new material based on the existing one
            material_dict = existing_material.to_dict

            # Remove fields that should be unique or auto-generated
            fields_to_remove = [
                "id",
                "created_at",
                "updated_at",
                "deleted_at",
                "created_by",
                "updated_by",
                "deleted_by",
            ]
            for field in fields_to_remove:
                if field in material_dict:
                    del material_dict[field]

            # Use the provided short_code for the cloned material
            material_dict["short_code"] = short_code

            # Apply fresh estimation breakups to get current project pricing standards
            if "project_id" in material_dict and "raw_material_id" in material_dict:
                add_estimation_breakups_to_project(db, material_dict)

            # Set created_by for the new material
            material_dict["created_by"] = current_member.id
            material_dict["is_deleted"] = False

            # Create the new material
            new_material = ProjectMaterials(**material_dict)
            db.add(new_material)
            db.flush()

            return JSONResponse(
                status_code=201,
                content={
                    "message": "Project material cloned successfully",
                    "status": "success",
                    "project_material_id": str(new_material.id),
                    "original_material_id": material_id,
                },
            )

    except Exception as error:
        logger.exception(f"clone_project_material error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def get_unassigned_door_and_other_materials(
    db: Session,
    project_id: str,
    material_type: str,
    project_take_off_sheet_section_area_item_id: str,
):
    """**Summary:**

    This method fetches a subset of materials from the database based on the specified type and project take off sheet section area item id.

    **Args:**
    - db: The database session object.
    - material_type (str): material type we need.
    - project_take_off_sheet_section_area_item_id (str): project take off sheet section area item id.
    """
    try:
        opening_schedule_subquery = (
            db.query(OpeningSchedules.project_material_id)
            .filter(
                OpeningSchedules.project_take_off_sheet_section_area_item_id
                == project_take_off_sheet_section_area_item_id,
                OpeningSchedules.project_material_id != None,
            )
            .subquery()
        )

        material_items = (
            db.query(ProjectMaterials)
            .filter(
                ProjectMaterials.is_deleted == False,
                ProjectMaterials.material_type == material_type,
                ProjectMaterials.project_id == project_id,
                ~ProjectMaterials.id.in_(opening_schedule_subquery),
            )
            .order_by(ProjectMaterials.created_at.asc())
            .all()
        )

        response = {
            "data": material_items,
            "status": "success",
            "message": "Unassigned door and other materials fetched successfully",
        }
        return response
    except Exception as e:
        logger.exception("get_unassigned_door_and_other_materials:: error - " + str(e))
        raise e



async def get_unassigned_door_and_other_materials_v2(
    db: Session,
    project_id: str,
    material_type: str,
    project_take_off_sheet_section_area_item_id: str,
    section_id: str,
    project_take_off_sheet_section_id: str,
    project_take_off_sheet_id: str,
):
    """**Summary:**

    This method fetches a subset of materials from the database based on the specified type and project take off sheet section area item id.
    Project materials are limited to raw materials linked to the section in section_raw_materials for the validated section_id.

    **Args:**
    - db: The database session object.
    - material_type (str): material type we need.
    - project_take_off_sheet_section_area_item_id (str): project take off sheet section area item id.
    - section_id (str): section id (must match the take-off sheet section row).
    - project_take_off_sheet_section_id (str): project take off sheet section id.
    - project_take_off_sheet_id (str): project take off sheet id.
    """
    try:
        take_off_sheet = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.id == project_take_off_sheet_id,
                ProjectTakeOffSheets.project_id == project_id,
                ProjectTakeOffSheets.is_deleted == False,
            )
            .first()
        )
        if not take_off_sheet:
            return {
                "data": [],
                "status": "error",
                "message": "Take-off sheet not found or does not belong to this project.",
            }

        take_off_section = (
            db.query(ProjectTakeOffSheetSections)
            .filter(
                ProjectTakeOffSheetSections.id == project_take_off_sheet_section_id,
                ProjectTakeOffSheetSections.section_id == section_id,
                ProjectTakeOffSheetSections.project_take_off_sheet_id
                == project_take_off_sheet_id,
                ProjectTakeOffSheetSections.is_deleted == False,
            )
            .first()
        )
        if not take_off_section:
            return {
                "data": [],
                "status": "error",
                "message": "Take-off section does not match the provided section or sheet.",
            }
        area_item = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.id
                == project_take_off_sheet_section_area_item_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False,
            )
            .first()
        )
        if not area_item:
            return {
                "data": [],
                "status": "error",
                "message": "Opening not found or does not belong to the specified take-off section.",
            }

        opening_schedule_subquery = (
            db.query(OpeningSchedules.project_material_id)
            .join(
                ProjectTakeOffSheetSectionAreaItems,
                OpeningSchedules.project_take_off_sheet_section_area_item_id
                == ProjectTakeOffSheetSectionAreaItems.id,
            )
            .join(
                ProjectTakeOffSheetSections,
                ProjectTakeOffSheetSections.id
                == ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_id,
            )
            .filter(
                ProjectTakeOffSheetSectionAreaItems.id
                == project_take_off_sheet_section_area_item_id,
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_section_id
                == project_take_off_sheet_section_id,
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id
                == project_take_off_sheet_id,
                ProjectTakeOffSheetSections.section_id == section_id,
                ProjectTakeOffSheetSections.project_take_off_sheet_id
                == project_take_off_sheet_id,
                OpeningSchedules.project_material_id != None,
            )
            .subquery()
        )

        allowed_raw_material_ids = (
            db.query(SectionRawMaterials.raw_material_id)
            .filter(SectionRawMaterials.section_id == section_id)
            .subquery()
        )

        material_items = (
            db.query(ProjectMaterials)
            .filter(
                ProjectMaterials.is_deleted == False,
                ProjectMaterials.material_type == material_type,
                ProjectMaterials.project_id == project_id,
                ProjectMaterials.raw_material_id.in_(allowed_raw_material_ids),
                ~ProjectMaterials.id.in_(opening_schedule_subquery),
            )
            .order_by(ProjectMaterials.created_at.asc())
            .all()
        )

        response = {
            "data": material_items,
            "status": "success",
            "message": "Unassigned door and other materials fetched successfully",
        }
        return response
    except Exception as e:
        logger.exception("get_unassigned_door_and_other_materials:: error - " + str(e))
        raise e


async def get_unassigned_hardware_materials(
    db: Session,
    project_id: str,
    material_type: str,
    hardware_group_id: str,
):
    """**Summary:**

    This method fetches a subset of materials from the database based on the specified type and project take off sheet section area item id.

    **Args:**
    - db: The database session object.
    - material_type (str): material type we need.
    - hardware_group_id (str): hardware group id.
    """
    try:
        hardware_group_subquery = (
            db.query(HardwareGroupMaterials.project_material_id)
            .filter(
                HardwareGroupMaterials.hardware_group_id == hardware_group_id,
                HardwareGroupMaterials.project_material_id != None,
            )
            .subquery()
        )

        material_items = (
            db.query(ProjectMaterials)
            .filter(
                ProjectMaterials.is_deleted == False,
                ProjectMaterials.material_type == material_type,
                ProjectMaterials.project_id == project_id,
                ~ProjectMaterials.id.in_(hardware_group_subquery),
            )
            .order_by(ProjectMaterials.created_at.asc())
            .all()
        )

        response = {
            "data": material_items,
            "status": "success",
            "message": "Unassigned hardware materials fetched successfully",
        }
        return response
    except Exception as e:
        logger.exception("get_unassigned_hardware_materials:: error - " + str(e))
        raise e


async def get_materials_details(
    db: Session,
    project_id: str,
    opening_schedule_id: str,
):
    """**Summary:**

    This method fetches materials details for a specific opening schedule.

    **Args:**
    - db: The database session object.
    - project_id: The project ID.
    - opening_schedule_id: The opening schedule ID.
    """
    try:
        opening_schedule = db.query(OpeningSchedules).filter(OpeningSchedules.id == opening_schedule_id).first()
        if not opening_schedule:
            return JSONResponse(
                status_code=404,
                content={"message": "Opening schedule not found", "status": "error"},
            )

        material_item = db.query(ProjectMaterials).filter(ProjectMaterials.project_id == project_id,ProjectMaterials.id == opening_schedule.project_material_id,ProjectMaterials.is_deleted == False,).first()
        if not material_item:
            return JSONResponse(
                status_code=404,
                content={"message": "Material not found", "status": "error"},
            )

        material_type = material_item.material_type.value if isinstance(material_item.material_type, str) else material_item.material_type.value

        short_code = await generate_unique_short_code(project_id=project_id, db=db, prefix=material_type)

        item_dict = material_item.to_dict
        item_dict["short_code"] = short_code
        item_dict["raw_material_code"] = (
            material_item.raw_material.code
            if material_item.raw_material
            else None
        )
        item_dict["material_manufacturer"] = (
            material_item.material_manufacturer.to_dict
            if material_item.material_manufacturer
            else None
        )
        item_dict["material_brand"] = (
            material_item.material_brand.to_dict
            if material_item.material_brand
            else None
        )
        

        item_dict["product_category"] = (
            {
                "category": {
                    "id": material_item.take_off_hardware_product_category.id,
                    "name": material_item.take_off_hardware_product_category.name,
                }
            }
            if material_item.take_off_hardware_product_category
            else None
        )

        item_dict["opening_schedule"] = (
            {
                "id": str(opening_schedule.id),
                "desc": opening_schedule.desc,
                "component": opening_schedule.component if isinstance(opening_schedule.component, str) else opening_schedule.component.value,
            }
            if opening_schedule
            else None
        )
        item_dict["catelog_code"]=  item_dict["material_manufacturer"].get("code",item_dict["material_brand"])

        response = {
            "data": item_dict,
            "status": "success",
            "message": "Materials details fetched successfully",
        }
        return response
    except Exception as e:
        logger.exception("get_materials_details:: error - " + str(e))
        raise e

async def create_opening_project_material(
    request_data: CreateOpeningProjectMaterialRequest,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    Create a new opening project material.

    **Args:**
    - `request_data` (CreateOpeningProjectMaterialRequest): The request payload
      containing opening schedule and project material details.
    - `current_member` (Members): The authenticated member performing the action.
    - `db` (Session): The active database session.

    **Returns:**
    - dict: A success response containing created data details.
    - JSONResponse: An error response when opening schedule is not found.
    """
    try:
        if db.in_transaction():
           db.commit()

        #Get the opening schedule and check if it exists
        opening_schedule = db.query(OpeningSchedules).filter(OpeningSchedules.id == request_data.opening_schedule_id).first()
        if not opening_schedule:
            return JSONResponse(
                status_code=404,
                content={"message": "Opening schedule not found", "status": "error"},
            )

        #Create the project material
        material_payload = request_data.model_dump(exclude_unset=True, exclude={"opening_schedule_id"})
        create_material_request = ProjectMaterialRequest(**material_payload)
        project_material_id = await create_project_material(
            material_req_data=create_material_request,
            current_member=current_member,
            db=db,
            return_project_material_id=True
        )
        if isinstance(project_material_id, JSONResponse):
            response_payload = {}
            if project_material_id.body:
                try:
                    response_payload = json.loads(project_material_id.body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    response_payload = {}

            extracted_project_material_id = response_payload.get("project_material_id")
            if not extracted_project_material_id:
                raise ValueError(
                    response_payload.get(
                        "message",
                        "Unable to extract project_material_id from create_project_material response",
                    )
                )
            project_material_id = extracted_project_material_id
        print("project_material_id:: ",project_material_id)
        #Get the project take off sheet section area item id
        project_take_off_sheet_section_area_item_id=opening_schedule.project_take_off_sheet_section_area_item_id

        #Remove the material from the opening schedule
        await remove_material_from_opening(opening_schedule_id=request_data.opening_schedule_id, current_member=current_member, db=db)

        #Assign the material to the opening schedule
        assign_req_payload = ProjectMaterialAssignRequest(
            project_material_id=project_material_id,
            quantity=request_data.quantity
        )
        await assign_material_to_opening(material_req_data=assign_req_payload, project_take_off_sheet_section_area_item_id=project_take_off_sheet_section_area_item_id, current_member=current_member, db=db)
        #Return the success response
        return JSONResponse(content={"message": "Material added to opening successfully", "status": "success"}, status_code=200)
    except Exception as e:
        logger.exception("create_opening_project_material:: error - " + str(e))
        return JSONResponse(content={"message": str(e)}, status_code=500)



async def update_material_desc(
    material_id: str,
    material_desc: UpdateMaterialDescriptionRequest,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    Update an project material description.

    **Args:**
    - material_id (str): The ID of the project material to update.
    - description (UpdateMaterialDescriptionRequest): Updated project material description.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with success message and project_material_id.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            # Find the existing project material
            existing_material = (
                db.query(ProjectMaterials)
                .filter(
                    ProjectMaterials.id == material_id,
                    ProjectMaterials.is_deleted == False,
                )
                .first()
            )

            if not existing_material:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "Project material not found",
                        "status": "error",
                    },
                )

            # Build the update data
            update_data = {
                "desc": material_desc.description,
                "updated_by": current_member.id,
                "updated_at": datetime.now()
            }

            # Update the project material
            db.query(ProjectMaterials).filter(
                ProjectMaterials.id == material_id
            ).update(update_data)

            existing_material_type = (
                existing_material.material_type.value
                if hasattr(existing_material.material_type, "value")
                else existing_material.material_type
            )
            if existing_material_type in ["DOOR", "FRAME"] and existing_material.raw_material_id:
                raw_material_row = (
                    db.query(RawMaterials.code)
                    .filter(RawMaterials.id == existing_material.raw_material_id)
                    .first()
                )
                if raw_material_row and raw_material_row.code:
                    # adon_fields are not stored on ProjectMaterials, so try both common key variants.
                    possible_key =_get_material_description_combination_key(
                            effective_material_type=existing_material_type.value if hasattr(existing_material_type, "value") else existing_material_type,
                            raw_material_type=raw_material_row.code,
                            effective_series=existing_material.series,
                            effective_base_feature=existing_material.base_feature,
                            effective_adon_feature=existing_material.adon_feature,
                            adon_fields=None,
                        )
                    print(">>>>>>>>>>>>>>>>>> possible_keys", possible_key)
                    updated_rows = db.query(MaterialDescription).filter(
                        MaterialDescription.combination_key==possible_key
                    ).update({"desc": material_desc.description})
                    if updated_rows == 0:
                        db.add(
                            MaterialDescription(
                                material_type=existing_material_type,
                                raw_material_type=raw_material_row.code,
                                series=existing_material.series,
                                base_feature=existing_material.base_feature,
                                adon_feature=existing_material.adon_feature,
                                adon_fields=None,
                                combination_key=_get_material_description_combination_key(
                                    existing_material_type,
                                    raw_material_row.code,
                                    existing_material.series,
                                    existing_material.base_feature,
                                    existing_material.adon_feature,
                                    None,
                                ),
                                desc=material_desc.description,
                            )
                        )
            db.flush()

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Project material updated successfully",
                    "status": "success",
                    "project_material_id": material_id,
                },
            )

    except Exception as error:
        logger.exception(f"update_material_desc error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def get_door_frame_material_sections(db: Session, project_id: str, material_type: str):
    """Return all door frame raw material section rows for a project."""
    try:
        sections = (
            db.query(DoorFrameRawMaterialSections)
            .filter(DoorFrameRawMaterialSections.project_id == project_id, DoorFrameRawMaterialSections.material_type == material_type)
            .all()
        )
        data =[]
        for section in sections:
            data_temp = section.to_dict
            data_temp["id"] = section.id
            data_temp["project_id"] = section.project_id
            data_temp["raw_material_id"] = section.raw_material_id
            data_temp["material_type"] = section.material_type
            data_temp["raw_material"] = section.raw_material.to_dict
            data.append(data_temp)
        return {
            "data": data,
            "status": "success",
        }
    except Exception as error:
        logger.exception(f"get_door_frame_material_sections error: {error}")
        raise error


async def update_door_frame_material_section(
    project_id: str,
    door_frame_raw_material_section_request: UpdateDoorFrameMaterialSectionRequest,
    db: Session,
):
    """Create or update rows keyed by (project_id, raw_material_id) with a single material_type."""
    try:

        if db.in_transaction():
            db.commit()

        with db.begin():
            raw_ids = door_frame_raw_material_section_request.raw_material_ids
            mt_str = door_frame_raw_material_section_request.material_type
            mt_str = mt_str.value if hasattr(mt_str, "value") else str(mt_str)
            try:
                material_type_enum = MATERIAL_TYPE(mt_str)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": f"Invalid material_type: {mt_str}",
                        "status": "error",
                    },
                )

            found_rows = (
                db.query(RawMaterials.id)
                .filter(RawMaterials.id.in_(raw_ids))
                .all()
            )
            found_set = {str(r[0]) for r in found_rows}
            missing = [rid for rid in raw_ids if str(rid) not in found_set]
            if missing:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "One or more raw materials not found",
                        "status": "error",
                        "missing_raw_material_ids": missing,
                    },
                )

            def _mt_val(mt) -> str:
                if mt is None:
                    return ""
                return mt.value if hasattr(mt, "value") else str(mt)

            mt_val = _mt_val(material_type_enum)
            pair_set = {(str(rid), mt_val) for rid in raw_ids}

            project_rows = (
                db.query(DoorFrameRawMaterialSections)
                .filter(DoorFrameRawMaterialSections.project_id == project_id)
                .all()
            )
            # First row per raw_material_id matches prior .first() semantics per id
            by_raw_id = {}
            for r in project_rows:
                k = str(r.raw_material_id)
                if k not in by_raw_id:
                    by_raw_id[k] = r

            saved = []
            for raw_material_id in raw_ids:
                rid = str(raw_material_id)
                row = by_raw_id.get(rid)
                if row is None:
                    row = DoorFrameRawMaterialSections(
                        id=generate_uuid(),
                        project_id=project_id,
                        raw_material_id=raw_material_id,
                        material_type=mt_str,
                    )
                    db.add(row)
                    by_raw_id[rid] = row
                else:
                    row.material_type = mt_str
                saved.append(row.to_dict)

            ids_to_remove = [
                r.id
                for r in project_rows
                if (str(r.raw_material_id), _mt_val(r.material_type)) not in pair_set
            ]
            if ids_to_remove:
                (
                    db.query(DoorFrameRawMaterialSections)
                    .filter(DoorFrameRawMaterialSections.id.in_(ids_to_remove))
                    .delete(synchronize_session=False)
                )

            db.flush()

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Door frame raw material sections saved successfully",
                    "status": "success",
                },
            )

    except Exception as error:
        logger.exception(f"update_door_frame_material_section error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)


async def get_openings(db: Session, project_id: str, material_type: str):
    """Get opening id and opening number list by project id and material type."""
    try:

        area_item_data = (
            db.query(
                ProjectTakeOffSheetSectionAreaItems.id,
                ProjectTakeOffSheetSectionAreaItems.opening_number,
                ProjectTakeOffSheetSectionAreaItems.adon_fields,
            )
            .join(
                ProjectTakeOffSheets,
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id
                == ProjectTakeOffSheets.id,
            )
            .filter(
                ProjectTakeOffSheets.project_id == project_id,
                ProjectTakeOffSheets.is_active == True,
                ProjectTakeOffSheets.is_deleted == False,
                ProjectTakeOffSheetSectionAreaItems.is_active == True,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False,
            )
            .all()
        )

        data = []
        if not area_item_data:
            return {
                "status": "success",
                "data": data,
            }

        area_item_ids = [area_item.id for area_item in area_item_data]

        opening_schedule_rows = (
            db.query(OpeningSchedules.project_take_off_sheet_section_area_item_id)
            .filter(
                OpeningSchedules.project_take_off_sheet_section_area_item_id.in_(area_item_ids),
                OpeningSchedules.component == material_type,
            )
            .all()
        )
        opening_schedule_count_map = defaultdict(int)
        for row in opening_schedule_rows:
            opening_schedule_count_map[row.project_take_off_sheet_section_area_item_id] += 1

        if material_type == "DOOR":
            door_type_ids = set()
            for area_item in area_item_data:
                adon_fields = area_item.adon_fields or {}
                if isinstance(adon_fields, dict):
                    door_type_id = adon_fields.get("door_type")
                    if door_type_id:
                        door_type_ids.add(door_type_id)

            door_type_name_map = {}
            if door_type_ids:
                door_type_rows = (
                    db.query(AdonOpeningFieldOptions.id, AdonOpeningFieldOptions.name)
                    .filter(AdonOpeningFieldOptions.id.in_(list(door_type_ids)))
                    .all()
                )
                door_type_name_map = {row.id: row.name for row in door_type_rows}

            for area_item in area_item_data:
                adon_fields = area_item.adon_fields or {}
                if not isinstance(adon_fields, dict):
                    continue

                door_type_id = adon_fields.get("door_type")
                if not door_type_id:
                    continue

                door_type = door_type_name_map.get(door_type_id)
                if not door_type:
                    continue

                opening_schedule_count = opening_schedule_count_map.get(area_item.id, 0)
                if door_type == "single" and opening_schedule_count == 1:
                    continue
                elif door_type == "double" and opening_schedule_count == 2:
                    continue
                elif door_type == "multi" and opening_schedule_count > 2:
                    continue

                data.append(
                    {
                        "id": area_item.id,
                        "opening_number": area_item.opening_number,
                    }
                )

        elif material_type == "FRAME":
            for area_item in area_item_data:
                if opening_schedule_count_map.get(area_item.id, 0) > 0:
                    continue
                data.append(
                    {
                        "id": area_item.id,
                        "opening_number": area_item.opening_number,
                    }
                )

        return {
            "status": "success",
            "data": data,
        }
    except Exception as error:
        logger.exception(f"get_openings error: {error}")
        raise error



async def batch_assign_material_to_opening(
    material_req_data: BatchProjectMaterialAssignRequest,
    project_material_id: str,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    This module is responsible for batch assigning an existing project material to a project opening.

    **Args:**
    - material_req_data (BatchProjectMaterialAssignRequest): project material data with opening_schedule_ids and quantity.
    - `project_material_id` (str): project_material_id to assign the project material.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

    **Return:**
    - `id` (str): project material id:
    - `message` (str): A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            project_take_off_sheet_section_area_items_ids = material_req_data.get(
                "project_take_off_sheet_section_area_items_ids", []
            )
            quantity = material_req_data["quantity"]

            # Get the existing material
            material_data = db.query(ProjectMaterials).get(project_material_id)
            if not material_data:
                return JSONResponse(
                    content={"message": "Project material not found","errors": [],
}, status_code=404
                )

            material_type = material_data.material_type.value
            material_type_enum = COMPONENTS(material_type)

            # Get material costs
            total_amount = material_data.total_amount
            total_sell_amount = material_data.total_sell_amount
            total_base_amount = material_data.total_base_amount
            total_extended_sell_amount = material_data.total_extended_sell_amount

            affected_section_ids = set()
            affected_take_off_sheet_ids = set()
            affected_project_ids = set()

            # All-or-nothing: validate every opening first, then insert.
            prepared = []
            errors = []

            for project_take_off_sheet_section_area_item_id in (
                project_take_off_sheet_section_area_items_ids or []
            ):
                # Get opening information
                project_take_off_sheet_section_area_item_data = db.query(
                    ProjectTakeOffSheetSectionAreaItems
                ).get(project_take_off_sheet_section_area_item_id)
                if not project_take_off_sheet_section_area_item_data:
                    errors.append(
                        {
                            "project_take_off_sheet_section_area_item_id": project_take_off_sheet_section_area_item_id,
                            "message": "Opening not found",
                            "status_code": 404,
                        }
                    )
                    continue

                project_take_off_sheet_data = db.query(ProjectTakeOffSheets).get(
                    project_take_off_sheet_section_area_item_data.project_take_off_sheet_id
                )
                if not project_take_off_sheet_data:
                    errors.append(
                        {
                            "project_take_off_sheet_section_area_item_id": project_take_off_sheet_section_area_item_id,
                            "opening_number": project_take_off_sheet_section_area_item_data.opening_number,
                            "message": "Take off sheet not found",
                            "status_code": 404,
                        }
                    )
                    continue

                # Check if material already assigned to this opening with the same component type
                existing_schedule = (
                    db.query(OpeningSchedules)
                    .filter(
                        OpeningSchedules.project_take_off_sheet_section_area_item_id
                        == project_take_off_sheet_section_area_item_id,
                        OpeningSchedules.project_material_id == project_material_id,
                        OpeningSchedules.component == material_type_enum,
                    )
                    .first()
                )
                if existing_schedule:
                    errors.append(
                        {
                            "project_take_off_sheet_section_area_item_id": project_take_off_sheet_section_area_item_id,
                            "opening_number": project_take_off_sheet_section_area_item_data.opening_number,
                            "message": "This material is already assigned to this opening",
                            "status_code": 400,
                        }
                    )
                    continue

                # Calculate final amounts
                final_amount = total_amount * quantity
                final_sell_amount = quantity * total_sell_amount
                final_base_amount = quantity * total_base_amount
                final_extended_sell_amount = quantity * total_extended_sell_amount

                # Determine raw_material_id based on material type
                if material_type == "DOOR":
                    possible_raw_material_type = (
                        project_take_off_sheet_section_area_item_data.door_raw_material_type
                    )
                elif material_type == "FRAME":
                    possible_raw_material_type = (
                        project_take_off_sheet_section_area_item_data.frame_raw_material_type
                    )
                else:
                    # For HARDWARE or OTHER types, use the material's raw_material_id
                    possible_raw_material_type = None
                    possible_raw_material_type_id = material_data.raw_material_id

                if material_type in ["DOOR", "FRAME"]:
                    possible_raw_material_type_id_result = (
                        db.query(RawMaterials.id)
                        .filter(RawMaterials.code == possible_raw_material_type)
                        .first()
                    )
                    if possible_raw_material_type_id_result:
                        possible_raw_material_type_id = (
                            possible_raw_material_type_id_result.id
                        )
                    else:
                        errors.append(
                            {
                                "project_take_off_sheet_section_area_item_id": project_take_off_sheet_section_area_item_id,
                                "opening_number": project_take_off_sheet_section_area_item_data.opening_number,
                                "message": f"Raw material type {possible_raw_material_type} not found",
                                "status_code": 400,
                            }
                        )
                        continue

                # Get description for the opening schedule
                desc = material_data.desc
                if material_type in ["DOOR", "FRAME"]:
                    desc = await get_description(
                        db,
                        project_take_off_sheet_section_area_item_data.adon_fields,
                        material_data.series,
                        possible_raw_material_type,
                        material_data.base_feature,
                        material_data.adon_feature,
                    )

                prepared.append(
                    {
                        "project_take_off_sheet_section_area_item_id": project_take_off_sheet_section_area_item_id,
                        "desc": desc,
                        "raw_material_id": possible_raw_material_type_id,
                        "final_amount": final_amount,
                        "final_sell_amount": final_sell_amount,
                        "final_base_amount": final_base_amount,
                        "final_extended_sell_amount": final_extended_sell_amount,
                        "project_id": project_take_off_sheet_data.project_id,
                        "project_take_off_sheet_id": project_take_off_sheet_data.id,
                    }
                )

            if errors:
                status_code = max((e.get("status_code", 400) for e in errors), default=400)
                return JSONResponse(
                    content={
                        "message": "Batch assign failed. No materials were assigned.",
                        "errors": errors,
                    },
                    status_code=status_code,
                )

            assigned_to = []

            for item in prepared:
                opening_schedule_data = OpeningSchedules(
                    component=material_type_enum,
                    desc=item["desc"],
                    total_amount=total_amount,
                    total_sell_amount=total_sell_amount,
                    total_base_amount=total_base_amount,
                    total_extended_sell_amount=total_extended_sell_amount,
                    quantity=quantity,
                    final_amount=item["final_amount"],
                    final_sell_amount=item["final_sell_amount"],
                    final_base_amount=item["final_base_amount"],
                    final_extended_sell_amount=item["final_extended_sell_amount"],
                    project_material_id=project_material_id,
                    raw_material_id=item["raw_material_id"],
                    project_id=item["project_id"],
                    project_take_off_sheet_section_area_item_id=item[
                        "project_take_off_sheet_section_area_item_id"
                    ],
                    created_by=current_member.id,
                )
                db.add(opening_schedule_data)
                db.flush()

                take_off_sheet_section_id = await update_area_item_stats(
                    db,
                    project_take_off_sheet_section_area_item_id=item[
                        "project_take_off_sheet_section_area_item_id"
                    ],
                )
                affected_section_ids.add(take_off_sheet_section_id)
                affected_take_off_sheet_ids.add(item["project_take_off_sheet_id"])
                affected_project_ids.add(item["project_id"])

                await update_door_width_and_height(
                    db, item["project_take_off_sheet_section_area_item_id"]
                )

                assigned_to.append(
                    {
                        "project_take_off_sheet_section_area_item_id": item[
                            "project_take_off_sheet_section_area_item_id"
                        ],
                        "opening_schedule_id": opening_schedule_data.id,
                    }
                )

            # Update section statistics
            for take_off_sheet_section_id in affected_section_ids:
                await update_section_stats(
                    db, project_take_off_sheet_section_id=take_off_sheet_section_id
                )

            # Update the sheet stats
            for take_off_sheet_id in affected_take_off_sheet_ids:
                await update_take_off_sheet_stats(db, project_take_off_sheet_id=take_off_sheet_id)

            # Update the raw material stats
            for project_id in affected_project_ids:
                await update_raw_material_stats(db, project_id=project_id)

            return {
                "id": project_material_id,
                "message": "Batch assign completed.",
                "status": "success",
                "data": {
                    "assigned_to": assigned_to,
                },
            }

    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error

