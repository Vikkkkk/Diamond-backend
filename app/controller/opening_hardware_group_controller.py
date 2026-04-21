"""
This file contains all the controller operations related to opening hardware groups.
"""
from collections import defaultdict
from datetime import datetime
import json
from typing import Literal
from loguru import logger
from repositories.schedule_repositories import update_schedule_stats
from models.opening_hardware_materials import OpeningHardwareMaterials
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from models.schedules import Schedules
from models.schedule_data import ScheduleData
from models.raw_materials import RawMaterials
from repositories.material_repositories import get_brand_manufacture
from repositories.opening_hw_material_repositories import is_opening_hw_short_code_exists
from repositories.opening_hw_material_repositories import add_estimation_breakups_to_opening_hardware, update_opening_hw_material_charges
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, func
from fastapi.responses import JSONResponse
from utils.common import get_user_time, extract_keywords
from sqlalchemy.orm import Session
from schemas.hardware_group_schemas import HardwareGroup
from schemas.materials_schema import OpeningHardwareMaterialCloneRequest, OpeningHardwareMaterial
from schemas.hardware_group_material_schema import ScheduleHardwarMaterialRequest
from models.members import Members
from models.hardware_product_category import HardwareProductCategory
from models.schedule_opening_hardware_material import ScheduleOpeningHardwareMaterials
from utils.request_handler import call_get_api
from repositories.material_repositories import get_description
from controller.transfer_opening_controller import compare_hardware_data
from sqlalchemy import or_, exists, and_
from models.schedules import Schedules
from models.co_schedules import CoSchedules
from models.change_order import ChangeOrder,ChangeOrderStatusEnum

    
async def add_category_info(
    db: Session,
    product_category: dict
):
    try:
        hardware_product_category_id = None
        category = product_category["category"]

        if category is not None:
            if category["id"] is None:
                # Handle the case where this is a new category
                existing_hw_product_cat = db.query(HardwareProductCategory).filter(
                    HardwareProductCategory.name == category["name"]
                ).first()

                if existing_hw_product_cat:
                    # Use the existing category if it already exists
                    category["id"] = existing_hw_product_cat.id
                else:
                    # Create a new category if no match is found
                    new_product_category_data = {
                        "name": category["name"],
                        "search_keywords": ",".join(elm for elm in extract_keywords(category["name"]))
                    }
                    new_product_category_data = HardwareProductCategory(**new_product_category_data)
                    db.add(new_product_category_data)
                    db.flush()
                    category["id"] = new_product_category_data.id

            # Assign the category ID to hardware_product_category_id
            hardware_product_category_id = category["id"]

        return hardware_product_category_id

    except Exception as error:
        raise error
    

async def add_hardware_material(
    material_req_data: OpeningHardwareMaterial, 
    current_member: Members, 
    db: Session
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
            # Ensure that only set fields are considered
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            # Set created_by field to the current member's ID
            material_req_data['created_by'] = current_member.id

            # Calculate final amount based on total amount and quantity
            total_amount = material_req_data["total_amount"]
            quantity = material_req_data["quantity"]
            material_req_data["total_base_amount"] = total_amount
            material_req_data["total_sell_amount"] = total_amount
            material_req_data["total_extended_sell_amount"] = total_amount
            material_req_data["final_amount"] = total_amount * quantity
            material_req_data["final_base_amount"] = total_amount * quantity
            material_req_data["final_sell_amount"] = total_amount * quantity
            material_req_data["final_extended_sell_amount"] = total_amount * quantity

            # Check if the provided shortcode is unique within the project
            short_code = material_req_data["short_code"]

            # fetch raw_material with code 'HWD' which stands for Hardware
            raw_material_hwd = (
                db.query(RawMaterials.id)
                .filter(RawMaterials.code == 'HWD')
            ).first()
            # we need the id to associate the hardware_material with the raw_material
            material_req_data['raw_material_id'] = None if raw_material_hwd is None else raw_material_hwd.id

            project_short_code_exist = await is_opening_hw_short_code_exists(material_req_data["project_id"], short_code, db)
            if not project_short_code_exist:
                # Manage product catehory of the hardware
                product_category = material_req_data["product_category"]
                material_req_data["hardware_product_category_id"] = await add_category_info(db, product_category)
                del material_req_data["product_category"]
                # We need to apply the markup, margin, discount, surcharge automatically based on an exisiting project_material
                add_estimation_breakups_to_opening_hardware(db, material_req_data)
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

                del material_req_data['raw_material_id']

                material_data = OpeningHardwareMaterials(**material_req_data)
                db.add(material_data)
                db.flush()
                opening_hw_material_id = material_data.id
                material_costs = await update_opening_hw_material_charges(
                    db, opening_hw_material_id, return_updated_values=True
                )

                # calculate the total base cost and sell cost and final base cost and final base cost sell cost
                if material_costs is not None: 
                    total_sell_amount = material_costs["total_sell_amount"]
                    total_base_amount = material_costs["total_base_amount"]
                    total_extended_sell_amount = material_costs["total_extended_sell_amount"]
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
                material_data.final_base_amount = final_base_amount
                material_data.final_sell_amount = final_sell_amount
                material_data.final_extended_sell_amount = final_extended_sell_amount
                db.flush()
                db.commit()
                # Return success message and created material ID
                return {"id": opening_hw_material_id, "message": "Opening Hardware material added.", "status": "success"}
            else:
                return JSONResponse(content={"message": "Short Code already exits in the current project"}, status_code=400)
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error



async def update_hardware_material(
    material_req_data: OpeningHardwareMaterial, 
    current_member: Members, 
    db: Session
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
                return JSONResponse(content={"message": "Invalid request payload."}, status_code=400)
            
            opening_hw_material_data = db.query(OpeningHardwareMaterials).get(material_req_data['id'])
                
            # Calculate final amount based on total amount and quantity
            final_amount = None
            if "total_amount" in material_req_data:  
                total_amount = material_req_data["total_amount"]
            else:
                total_amount = opening_hw_material_data.total_amount

            if "quantity" in material_req_data:
                quantity = material_req_data["quantity"]
            else:
                quantity = opening_hw_material_data.quantity

            final_amount = total_amount * quantity

            # Check and update shortcode if provided
            if "short_code" in material_req_data:
                short_code = material_req_data["short_code"]
                project_short_code_exist = await is_opening_hw_short_code_exists(opening_hw_material_data.project_id, short_code, db, material_req_data['id'])
                if project_short_code_exist:
                    return JSONResponse(content={"message": "Shortcode Already in used"}, status_code=400)

            # Manage product catehory of the hardware
            if "product_category" in material_req_data and material_req_data["product_category"] is not None:
                product_category = material_req_data["product_category"]
                material_req_data["hardware_product_category_id"] = await add_category_info(db, product_category)
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
            material_req_data['updated_by'] = current_member.id
            for key, value in material_req_data.items():
                setattr(opening_hw_material_data, key, value)
            
            db.flush()

            material_costs = await update_opening_hw_material_charges(
                db, opening_hw_material_data.id, return_updated_values=True
            )
            db.flush()
            db.commit()

        hardware_material_id = material_req_data['id']
        schedule_material_ids = db.query(ScheduleOpeningHardwareMaterials.schedule_id).filter(ScheduleOpeningHardwareMaterials.opening_hardware_material_id == hardware_material_id).all()
        for schedule in schedule_material_ids:
            await compare_hardware_data(db, current_member, schedule.schedule_id)

        # Return success message and updated material ID
        return {"id": material_req_data['id'], "message": "Opening Hardware material updated.", "status": "success"}
    
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error



async def delete_hardware_material(
    hardware_material_id: str, 
    current_member: Members, 
    db: Session
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
            opening_hardware_material_data = db.query(OpeningHardwareMaterials).get(hardware_material_id)

            # Check if hardware group material data exists
            if not opening_hardware_material_data:
                return JSONResponse(content={"message": "Invalid opening hardware ID"}, status_code=400)
            assigned_schedule_data = db.query(ScheduleOpeningHardwareMaterials).filter(ScheduleOpeningHardwareMaterials.opening_hardware_material_id==opening_hardware_material_data.id).first()
            if assigned_schedule_data:
                return JSONResponse(content={"message": "Hardware item is assigned to opening.In order to delete the item this needs to be unassigned."}, status_code=400)
            update_data = {'is_deleted': True, 'deleted_at': datetime.now()}
            db.query(OpeningHardwareMaterials).filter(OpeningHardwareMaterials.id == opening_hardware_material_data.id).update(update_data)
        schedule_material_ids = db.query(ScheduleOpeningHardwareMaterials.schedule_id).filter(ScheduleOpeningHardwareMaterials.opening_hardware_material_id == hardware_material_id).all()
        for schedule in schedule_material_ids:
            await compare_hardware_data(db, current_member, schedule.schedule_id)
        
        return {"message": "Material Deleted.", "status": "success"}
    
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"delete_hardware_material:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def clone_opening_hardware_material(project_id: str, opening_hardware_id: str, short_code: str, current_member: Members, db: Session):
    """Clone a opening hardware material."""
    try:
        # Check for existing opening hardware material with the same name and project ID
        short_code_exists = db.query(OpeningHardwareMaterials).filter(
            OpeningHardwareMaterials.short_code == short_code,
            OpeningHardwareMaterials.project_id == project_id
        ).first()

        if short_code_exists:
            return JSONResponse(content={"message": "Opening Hardware short code already exists", "status": "error"}, status_code=422)

        # Retrieve the original hardware material data
        opening_hardware_data = db.query(OpeningHardwareMaterials).get(opening_hardware_id)
        if not opening_hardware_data:
            return JSONResponse(content={"message": "Opening Hardware Material not found", "status": "error"}, status_code=404)

        # Prepare the new hardware material data
        new_opening_hardware_data = opening_hardware_data.to_dict
        new_opening_hardware_data["created_by"] = current_member.id
        new_opening_hardware_data["short_code"] = short_code
        new_opening_hardware_data["project_id"] = project_id
        del new_opening_hardware_data["id"]

        # Create and add the new hardware material
        new_opening_hardware_data = OpeningHardwareMaterials(**new_opening_hardware_data)
        db.add(new_opening_hardware_data)
        db.flush()  # Flush to get the ID of the new hardware group
        new_opening_hardware_material_id = new_opening_hardware_data.id
        db.commit()

        # Return the result of the operation
        return {"id": new_opening_hardware_material_id, "message": "Data cloned successfully.", "status": "success"}

    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        return JSONResponse(content={"message": "An integrity error occurred.", "status": "error"}, status_code=500)

    except Exception as error:
        logger.exception(f"clone_opening_hardware_material:: An unexpected error occurred: {error}")
        db.rollback()
        return JSONResponse(content={"message": "An unexpected error occurred.", "status": "error"}, status_code=500)
    


async def get_opening_hardware_items(db: Session, project_id: str, keyword: str = None):
    """Retrieve opening hardware items belonging to a project with change order flag."""

    try:
        # Base query
        query = db.query(OpeningHardwareMaterials).filter(
            OpeningHardwareMaterials.project_id == project_id,
            OpeningHardwareMaterials.is_deleted == False,
        )

        # Apply keyword filter if provided
        if keyword:
            query = query.filter(
                OpeningHardwareMaterials.short_code.ilike(f"%{keyword}%")
            )

        item_data = query.order_by(
            OpeningHardwareMaterials.created_at.desc()
        ).all()

        response = []

        for data in item_data:
            data_dict = data.to_dict

            # --- Check if this hardware is in an active change order ---
            is_in_active_change_order = (
                db.query(exists().where(
                    and_(
                        ScheduleOpeningHardwareMaterials.opening_hardware_material_id == data.id,
                        ScheduleOpeningHardwareMaterials.schedule_id == Schedules.id,
                        ChangeOrder.project_id == project_id,
                        ChangeOrder.current_status.in_(
                            [ChangeOrderStatusEnum.APPROVED, ChangeOrderStatusEnum.IN_REVIEW]
                        )
                    )
                )
                .where(
                    Schedules.id == ScheduleOpeningHardwareMaterials.schedule_id
                )
                .where(
                    ChangeOrder.id == CoSchedules.co_id
                )
                .where(
                    CoSchedules.schedule_id == Schedules.id
                )
                ).scalar()
            )

            # Update dictionary with relationships + new flag
            data_dict.update({
                "manufacturer_code": data.opening_hardware_manufacturer.code,
                "brand_code": data.opening_hardware_brand.code if data.opening_hardware_brand else None,
                "product_category": (
                    {
                        "category": {
                            "id": data.opening_hardware_product_category.id,
                            "name": data.opening_hardware_product_category.name
                        }
                    }
                    if data.opening_hardware_product_category else None
                ),
                "is_in_active_change_order": bool(is_in_active_change_order),
            })

            response.append(data_dict)

        return {
            "data": response,
            "message": "Data Fetch Successfully.",
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"get_opening_hardware_items:: An unexpected error occurred: {error}")
        raise error



async def assign_hardware_to_opening(
    db: Session,
    request_data: ScheduleHardwarMaterialRequest, 
    schedule_id: str,
    current_member: str
):
    """
    **Assign Hardware Materials to a Schedule**

    This function assigns hardware materials to a specific schedule for a project. The request payload contains a mapping of hardware material IDs to their quantities. It performs the following actions:
    - Materials in the request but not already assigned to the schedule are **added**.
    - Materials already assigned to the schedule but not included in the request are **removed**.
    - Materials already assigned to the schedule and included in the request have their quantities updated.

    **Parameters:**
    - `db` (Session): The database session used to query and commit changes.
    - `request_data` (ScheduleHardwarMaterialRequest): The data containing hardware material IDs and quantities to assign to the schedule.
    - `schedule_id` (str): The unique identifier of the schedule to which the hardware materials should be assigned.
    - `current_member` (str): The member making the request, used to track who created the schedule materials.
    """
    try:
        hardware_materials = request_data.hardware_materials
        if not hardware_materials or not schedule_id:
            return JSONResponse(content={"message": "No hardware material IDs or schedule ID provided", "status": "error"}, status_code=400)

        results = {"added": [], "removed": [], "updated": []}

        # Fetch existing scheduled materials filtered by schedule ID
        scheduled_materials = db.query(ScheduleOpeningHardwareMaterials).filter(
            ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
        ).all()

        # Create a dictionary of existing material IDs and their quantities in the schedule
        existing_materials = {material.opening_hardware_material_id: material.quantity for material in scheduled_materials}

        # Determine materials to add, update, and remove
        to_remove = set(existing_materials.keys()) - set(hardware_materials.keys())
        to_add = set(hardware_materials.keys()) - set(existing_materials.keys())
        to_update = set(hardware_materials.keys()) & set(existing_materials.keys())

        # Remove materials
        if to_remove:
            deleted_count = db.query(ScheduleOpeningHardwareMaterials).filter(
                ScheduleOpeningHardwareMaterials.opening_hardware_material_id.in_(to_remove),
                ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
            ).delete(synchronize_session="fetch")

            if deleted_count > 0:
                results["removed"].extend(to_remove)

        # Add new materials
        if to_add:
            materials_to_add = db.query(OpeningHardwareMaterials).filter(
                OpeningHardwareMaterials.id.in_(to_add)
            ).all()

            for material in materials_to_add:
                quantity = hardware_materials[material.id]
                schedule_material = ScheduleOpeningHardwareMaterials(
                    opening_hardware_material_id=material.id,
                    quantity=quantity,  # Use quantity from request payload
                    total_amount=material.total_amount,
                    total_sell_amount=material.total_sell_amount,
                    total_base_amount=material.total_base_amount,
                    total_extended_sell_amount=material.total_extended_sell_amount,
                    final_amount=material.final_amount * quantity,
                    final_sell_amount=material.final_sell_amount * quantity,
                    final_base_amount=material.final_base_amount * quantity,
                    final_extended_sell_amount=material.final_extended_sell_amount * quantity,
                    schedule_id=schedule_id,  # Ensure schedule_id is set
                    is_active=True,
                    created_by=current_member.id,  # Use dynamic user information for the creator
                )
                db.add(schedule_material)
                results["added"].append({"id": material.id, "quantity": hardware_materials[material.id]})

        # Update quantities for existing materials
        if to_update:
            for material_id in to_update:
                db.query(ScheduleOpeningHardwareMaterials).filter(
                    ScheduleOpeningHardwareMaterials.opening_hardware_material_id == material_id,
                    ScheduleOpeningHardwareMaterials.schedule_id == schedule_id
                ).update({"quantity": hardware_materials[material_id]})
                results["updated"].append({"id": material_id, "quantity": hardware_materials[material_id]})
        db.flush()
        # Update the schedule stats
        await update_schedule_stats(db, schedule_id)
        db.flush()
        # Commit changes to the database
        db.commit()
        print("calling compare_hardware_data start")
        await compare_hardware_data(db, current_member, schedule_id)
        print("calling compare_hardware_data end")
        # Return a response with the results
        return {"status": "success", "results": results}
    
    except Exception as error:
        logger.exception(f"assign_hardware_to_opening:: An unexpected error occurred: {error}")
        raise error


async def get_assigned_hardwares(
    db: Session,
    schedule_id: str
):
    try:
        schedule_info = db.query(Schedules).get(schedule_id)
        if not schedule_info:
            return JSONResponse(content={"message": "Invalid schedule id provided", "status": "error"}, status_code=400)
        data_dict = {}
        for elm in schedule_info.schedule_hardware_materials:
            obj = {
                "schedule_opening_hardware_material_id": elm.id,
                "quantity": elm.quantity,
                "total_amount": elm.total_amount,
                "total_base_amount": elm.total_base_amount,
                "total_sell_amount": elm.total_sell_amount,
                "total_extended_sell_amount": elm.total_extended_sell_amount,
                "final_amount": elm.final_amount,
                "final_base_amount": elm.final_base_amount,
                "final_sell_amount": elm.final_sell_amount,
                "final_extended_sell_amount": elm.final_extended_sell_amount,
            }
            data_dict[str(elm.opening_hardware_material_id)] = obj
        schedule_hw_materials = list(data_dict.keys())
        opening_hardware_materials = db.query(OpeningHardwareMaterials).filter(OpeningHardwareMaterials.id.in_(schedule_hw_materials)).all()
        for indx, elm in enumerate(opening_hardware_materials):
            obj = elm.to_dict
            opening_hardware_brand = elm.opening_hardware_brand
            obj["brand_code"] = opening_hardware_brand.code if hasattr(opening_hardware_brand, 'code') else opening_hardware_brand or None
            obj["manufacturer_code"] = elm.opening_hardware_manufacturer.code
            obj["quantity"] = data_dict[obj["id"]]["quantity"]
            obj["total_amount"] = data_dict[obj["id"]]["total_amount"]
            obj["total_base_amount"] = data_dict[obj["id"]]["total_base_amount"]
            obj["total_sell_amount"] = data_dict[obj["id"]]["total_sell_amount"]
            obj["total_extended_sell_amount"] = data_dict[obj["id"]]["total_extended_sell_amount"]
            obj["final_amount"] = data_dict[obj["id"]]["final_amount"]
            obj["final_base_amount"] = data_dict[obj["id"]]["final_base_amount"]
            obj["final_sell_amount"] = data_dict[obj["id"]]["final_sell_amount"]
            obj["final_extended_sell_amount"] = data_dict[obj["id"]]["final_extended_sell_amount"]
            obj["schedule_opening_hardware_material_id"] = data_dict[obj["id"]]["schedule_opening_hardware_material_id"]
            opening_hardware_materials[indx] = obj
        return {"status": "success", "data": opening_hardware_materials}
    except Exception as error:
        logger.exception(f"get_assigned_hardwares:: An unexpected error occurred: {error}")
        raise error



async def get_hardware_product_categories(db: Session, keyword: str = None):
    """**Summary:**
    Retrieve all list of hardware product categories.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - keyword (str): This will be useful for keyword search on name.

    Returns:
    - dict: A dictionary containing the retrieved data.

    Raises:
    - Exception: If an unexpected error occurs during the data retrieval process.
    """
    try:
        # Fetch top-level categories
        if keyword is not None:
            item_data = (
                db.query(HardwareProductCategory)
                .filter(
                    HardwareProductCategory.is_active == True,
                    HardwareProductCategory.name.ilike(f'%{keyword}%')
                )
                .order_by(HardwareProductCategory.created_at.desc())
                .all()
            )
        else:
            item_data = (
                db.query(HardwareProductCategory)
                .filter(
                    HardwareProductCategory.is_active == True,
                )
                .order_by(HardwareProductCategory.created_at.desc())
                .all()
            )

        return {"data": item_data, "message": "Data Fetch Successfully.", "status": "success"}

    except Exception as error:
        logger.exception(f"get_hardware_product_categories:: An unexpected error occurred: {error}")
        raise error


async def get_hardware_prep_fields(db: Session, schedule_opening_hardware_material_id: str):
    """**Summary:**
    Retrieve all list of hardware product categories.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - keyword (str): this will be usefull for keyword search on name.

    Returns:
    - dict: A dictionary containing the retrieved data.

    Raises:
    - Exception: If an unexpected error occurs during the data retrieval process.
    """
    try:
        resp_data = {}
        schedule_opening_hardware_material_data = db.query(ScheduleOpeningHardwareMaterials).get(schedule_opening_hardware_material_id)
        if schedule_opening_hardware_material_data:
            opening_hardware_material_data = schedule_opening_hardware_material_data.opening_hardware_material
            if opening_hardware_material_data and opening_hardware_material_data.opening_hardware_product_category:
                opening_hardware_product_category_data = opening_hardware_material_data.opening_hardware_product_category
                keywords = []
                if opening_hardware_product_category_data.parent_id is None:
                    # In case this is a category
                    keywords.extend(opening_hardware_product_category_data.search_keywords.split(","))
                else:
                    keywords.extend(opening_hardware_product_category_data.search_keywords.split(","))
                    product_category_data = db.query(HardwareProductCategory).get(opening_hardware_product_category_data.parent_id)
                    if product_category_data:
                        keywords.extend(product_category_data.search_keywords.split(","))
                if len(keywords) > 0:
                    print(schedule_opening_hardware_material_data.to_dict)
                    catalog_series_schedule_data = (
                        db.query(ScheduleData)
                        .filter(
                            ScheduleData.schedule_id == schedule_opening_hardware_material_data.schedule_id,
                            or_(
                                ScheduleData.name.ilike(f'%_catalog%'),
                                ScheduleData.name.ilike(f'%_series%')
                            )
                        )
                        .all()
                    )
                    print("catalog_series_schedule_data:: ",len(catalog_series_schedule_data))
                    if len(catalog_series_schedule_data) == 0:
                        return JSONResponse(content={"message": "In Order to Manage prep of the opening You need to select door and/or frame catalog and series", "status": "error"}, status_code=400)
                    else:
                        # Door & frame field customizations
                        door_series = None
                        door_catalog = None
                        frame_series = None
                        frame_catalog = None
                        for row in catalog_series_schedule_data:
                            print(row.name)
                            if not hasattr(row, "name") or not hasattr(row, "value"):
                                continue  # Skip rows without the required attributes
                            match row.name:
                                case "door_catalog":
                                    door_catalog = await get_brand_manufacture(db, row.value)
                                case "frame_catalog":
                                    frame_catalog = await get_brand_manufacture(db, row.value)
                                case "door_series":
                                    door_series = row.value
                                case "frame_series":
                                    frame_series = row.value
                                case _:
                                    print(f"Unexpected row.name: {row.name}")
                        if door_catalog is not None:
                            # door prep filed customization
                            if door_catalog["brand_code"] is not None:
                                param_data = {
                                    "manufacturerCode": door_catalog["manufacture_code"],
                                    "brandCode": door_catalog["brand_code"],
                                    "seriesCode": door_series,
                                    "keywords": ",".join(elm for elm in keywords),
                                }
                            else:
                                param_data = {
                                    "manufacturerCode": door_catalog["manufacture_code"],
                                    "seriesCode": door_series,
                                    "keywords": ",".join(elm for elm in keywords),
                                }
                            door_data_response = await call_get_api("diamond/adonFeatures/get_adon_feature_options", param_data)
                            if door_data_response["status_code"] == 200:
                                categorized_data = defaultdict(list)
                                for item in door_data_response["response"]["data"]:
                                    adon_feature = item.get("adonFeatureCode", "Unknown")
                                    categorized_data[adon_feature].append(item)

                                # Convert defaultdict to a regular dictionary for cleaner output
                                categorized_data = dict(categorized_data)
                                resp_data["door"] = categorized_data
                            else:
                                resp_data["door"] =  {}  
                        if frame_catalog is not None:
                            # frame prep filed customization
                            if frame_catalog["brand_code"] is not None:
                                param_data = {
                                    "manufacturerCode": frame_catalog["manufacture_code"],
                                    "brandCode": frame_catalog["brand_code"],
                                    "seriesCode": frame_series,
                                    "keywords": ",".join(elm for elm in keywords),
                                }
                            else:
                                param_data = {
                                    "manufacturerCode": frame_catalog["manufacture_code"],
                                    "seriesCode": frame_series,
                                    "keywords": ",".join(elm for elm in keywords),
                                }
                            frame_data_response =  await call_get_api("diamond/adonFeatures/get_adon_feature_options", param_data)   
                            if frame_data_response["status_code"] == 200:
                                categorized_data = defaultdict(list)
                                for item in frame_data_response["response"]["data"]:
                                    adon_feature = item.get("adonFeatureCode", "Unknown")
                                    categorized_data[adon_feature].append(item)

                                # Convert defaultdict to a regular dictionary for cleaner output
                                categorized_data = dict(categorized_data)
                                resp_data["frame"] = categorized_data
                            else:
                                resp_data["frame"] =  {}  
                        # # hardware prep filed customization
                        # if opening_hardware_material_data.brand_id is not None:
                        #     param_data = {
                        #         "manufacturerCode": opening_hardware_material_data.opening_hardware_manufacturer.code,
                        #         "brandCode": opening_hardware_material_data.opening_hardware_brand.code,
                        #         "seriesCode": opening_hardware_material_data.series,
                        #         "keywords": ",".join(elm for elm in keywords),
                        #     }
                        # else:
                        #     param_data = {
                        #         "manufacturerCode": opening_hardware_material_data.opening_hardware_manufacturer.code,
                        #         "seriesCode": opening_hardware_material_data.series,
                        #         "keywords": ",".join(elm for elm in keywords),
                        #     }
                        # resp_data["hardware"] = await call_get_api("diamond/adonFeatures/get_adon_feature_options", param_data)
        return {"data": resp_data, "message": "Data Fetch Successfully.", "status": "success"}
    except Exception as error:
        logger.exception(f"get_hardware_prep_fields:: An unexpected error occurred: {error}")
        raise error

