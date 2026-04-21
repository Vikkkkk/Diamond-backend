"""
This module contains all logical operations and db operations related to opening door/frame materials.
"""
import json
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import exists, and_
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from models.opening_door_frame_materials import OpeningDoorFrameMaterials
from models.schedule_opening_door_frame_material import ScheduleOpeningDoorFrameMaterials
from models.schedules import Schedules
from models.schedule_data import ScheduleData
from models.co_schedules import CoSchedules
from models.change_order import ChangeOrder, ChangeOrderStatusEnum
from models.members import Members
from models.raw_materials import RawMaterials
from repositories.opening_door_frame_material_repositories import is_opening_door_frame_short_code_exists
from repositories.opening_door_frame_material_repositories import add_estimation_breakups_to_opening_door_frame
from repositories.opening_door_frame_material_repositories import update_opening_door_frame_material_charges
from repositories.material_repositories import get_description
from repositories.schedule_summary_repositories import update_schedule_charges, update_schedule_stats
from schemas.materials_schema import OpeningDoorFrameMaterial, UpdateMaterialDescriptionRequest
from controller.transfer_opening_controller import sync_material_schedule_data
from typing import Optional 


async def get_opening_door_frame_materials(db: Session, project_id: str, keyword: str = None, material_type: str = None):
    """Retrieve opening door/frame materials belonging to a project.
    
    Args:
        db (Session): Database session
        project_id (str): Project ID to filter materials
        keyword (str, optional): Keyword to search in short_code
        material_type (str, optional): Filter by material type (DOOR or FRAME)
    
    Returns:
        dict: Dictionary containing list of door/frame materials with status and message
    """

    try:
        # Base query
        query = db.query(OpeningDoorFrameMaterials).filter(
            OpeningDoorFrameMaterials.project_id == project_id,
            OpeningDoorFrameMaterials.is_active == True,
            OpeningDoorFrameMaterials.is_deleted == False
        )

        # Apply keyword filter if provided
        if keyword:
            query = query.filter(
                OpeningDoorFrameMaterials.short_code.ilike(f"%{keyword}%")
            )
        
        # Apply material type filter if provided
        if material_type:
            query = query.filter(
                OpeningDoorFrameMaterials.material_type == material_type
            )

        item_data = query.order_by(
            OpeningDoorFrameMaterials.created_at.desc()
        ).all()

        response = []

        for data in item_data:
            data_dict = data.to_dict

            # --- Check if this door/frame material is in an active change order ---
            is_in_active_change_order = (
                db.query(exists().where(
                    and_(
                        ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id == data.id,
                        ScheduleOpeningDoorFrameMaterials.schedule_id == Schedules.id,
                        ChangeOrder.project_id == project_id,
                        ChangeOrder.current_status.in_(
                            [ChangeOrderStatusEnum.APPROVED, ChangeOrderStatusEnum.IN_REVIEW]
                        )
                    )
                )
                .where(
                    Schedules.id == ScheduleOpeningDoorFrameMaterials.schedule_id
                )
                .where(
                    ChangeOrder.id == CoSchedules.co_id
                )
                .where(
                    CoSchedules.schedule_id == Schedules.id
                )
                ).scalar()
            )

            # Update dictionary with relationships + change order flag
            data_dict.update({
                "material_manufacturer": data.opening_door_frame_manufacturer.to_dict if data.opening_door_frame_manufacturer else None,
                "brand_code": data.opening_door_frame_brand.code if data.opening_door_frame_brand else None,
                "is_in_active_change_order": bool(is_in_active_change_order),
            })

            response.append(data_dict)

        return {
            "data": response,
            "message": "Data Fetch Successfully.",
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"get_opening_door_frame_materials:: An unexpected error occurred: {error}")
        raise error


async def get_unassigned_door_frame_materials(
    db: Session, 
    project_id: str, 
    schedule_id: str,
    raw_material_code: str = None,
    material_type: str = None,
    keyword: str = None
):
    """Retrieve unassigned door/frame materials for a project and schedule.
    
    Args:
        db (Session): Database session
        project_id (str): Project ID to filter materials
        schedule_id (str): Schedule ID to check which materials are not assigned
        raw_material_code (str, optional): Filter by raw material code
        material_type (str, optional): Filter by material type (DOOR or FRAME)
        keyword (str, optional): Keyword to search in short_code
    
    Returns:
        dict: Dictionary containing list of unassigned door/frame materials
    """
    try:
        # Get all material IDs already assigned to this schedule
        assigned_material_ids = db.query(
            ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id
        ).filter(
            ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id,
            ScheduleOpeningDoorFrameMaterials.material_type == material_type.upper() if material_type else ScheduleOpeningDoorFrameMaterials.material_type.in_(["DOOR", "FRAME"])
        ).subquery()
        
        # Base query for unassigned materials
        query = db.query(OpeningDoorFrameMaterials).filter(
            OpeningDoorFrameMaterials.project_id == project_id,
            OpeningDoorFrameMaterials.is_active == True,
            ~OpeningDoorFrameMaterials.id.in_(assigned_material_ids)
        )
        
        # Apply raw_material_code filter if provided
        if raw_material_code:
            query = query.filter(
                OpeningDoorFrameMaterials.raw_material_code == raw_material_code
            )
        
        # Apply material_type filter if provided
        if material_type:
            query = query.filter(
                OpeningDoorFrameMaterials.material_type == material_type
            )
        
        # Apply keyword filter if provided
        if keyword:
            query = query.filter(
                OpeningDoorFrameMaterials.short_code.ilike(f"%{keyword}%")
            )
        
        # Execute query
        materials = query.order_by(
            OpeningDoorFrameMaterials.created_at.desc()
        ).all()
        
        response = []
        for material in materials:
            material_dict = material.to_dict
            material_dict.update({
                "manufacturer_code": material.opening_door_frame_manufacturer.code if material.opening_door_frame_manufacturer else None,
                "brand_code": material.opening_door_frame_brand.code if material.opening_door_frame_brand else None,
            })
            response.append(material_dict)
        
        return {
            "data": response,
            "message": "Unassigned materials fetched successfully.",
            "status": "success"
        }
    
    except Exception as error:
        logger.exception(f"get_unassigned_door_frame_materials:: An unexpected error occurred: {error}")
        raise error


async def get_assigned_door_frame_materials(
    db: Session, 
    project_id: str, 
    schedule_id: str,
    raw_material_code: str = None,
    material_type: str = None,
    keyword: str = None
):
    """Retrieve assigned door/frame materials for a project and schedule.
    
    Args:
        db (Session): Database session
        project_id (str): Project ID to filter materials
        schedule_id (str): Schedule ID to check which materials are not assigned
        raw_material_code (str, optional): Filter by raw material code
        material_type (str, optional): Filter by material type (DOOR or FRAME)
        keyword (str, optional): Keyword to search in short_code
    
    Returns:
        dict: Dictionary containing list of unassigned door/frame materials
    """
    try:
        # Get all material IDs already assigned to this schedule
        assigned_material_ids = db.query(
            ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id
        ).filter(
            ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id,
            ScheduleOpeningDoorFrameMaterials.material_type == material_type.upper() if material_type else ScheduleOpeningDoorFrameMaterials.material_type.in_(["DOOR", "FRAME"])
        ).subquery()
        
        # Base query for unassigned materials
        query = db.query(OpeningDoorFrameMaterials).filter(
            OpeningDoorFrameMaterials.project_id == project_id,
            OpeningDoorFrameMaterials.is_active == True,
            OpeningDoorFrameMaterials.id.in_(assigned_material_ids)
        )
        
        # Apply raw_material_code filter if provided
        if raw_material_code:
            query = query.filter(
                OpeningDoorFrameMaterials.raw_material_code == raw_material_code
            )
        
        # Apply material_type filter if provided
        if material_type:
            query = query.filter(
                OpeningDoorFrameMaterials.material_type == material_type
            )
        
        # Apply keyword filter if provided
        if keyword:
            query = query.filter(
                OpeningDoorFrameMaterials.short_code.ilike(f"%{keyword}%")
            )
        
        # Execute query
        materials = query.order_by(
            OpeningDoorFrameMaterials.created_at.desc()
        ).all()
        
        schedule_materials = db.query(ScheduleOpeningDoorFrameMaterials).filter(
            ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id,
            ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id.in_([m.id for m in materials])
        ).all()
        schedule_material_by_material_id = {
            sm.opening_door_frame_material_id: sm for sm in schedule_materials
        }

        response = []
        for material in materials:
            material_dict = material.to_dict
            material_dict.update({
                "manufacturer_code": material.opening_door_frame_manufacturer.code if material.opening_door_frame_manufacturer else None,
                "brand_code": material.opening_door_frame_brand.code if material.opening_door_frame_brand else None,
            })

            schedule_material = schedule_material_by_material_id.get(material.id)
            if schedule_material and schedule_material.material_type and schedule_material.material_type.value == "DOOR":
                material_dict["part_number"] = schedule_material.part_number

            response.append(material_dict)
        
        return {
            "data": response,
            "message": "assigned materials fetched successfully.",
            "status": "success"
        }
    
    except Exception as error:
        logger.exception(f"get_assigned_door_frame_materials:: An unexpected error occurred: {error}")
        raise error

async def add_door_frame_material(
    material_req_data: OpeningDoorFrameMaterial, 
    current_member: Members, 
    db: Session
):
    """**Summary:**
    This module is responsible for creating a door/frame material for a project.

    **Args:**
    - material_req_data (OpeningDoorFrameMaterial): door/frame material create data.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current logged in member.

    **Return:**
    - `id` (str): created door/frame material id:
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
            project_short_code_exist = await is_opening_door_frame_short_code_exists(
                material_req_data["project_id"], short_code, db
            )
            
            if not project_short_code_exist:
                raw_material_code = material_req_data['raw_material_code']
                
                # Apply the markup, margin, discount, surcharge automatically based on an existing material
                add_estimation_breakups_to_opening_door_frame(db, material_req_data)
                desc = await get_description(
                    db,
                    {},
                    material_req_data["series"],
                    raw_material_code,
                    material_req_data["base_feature"],
                    material_req_data["adon_feature"],
                )
                material_req_data["desc"] = desc
                
                # Create the door/frame material
                material_data = OpeningDoorFrameMaterials(**material_req_data)
                db.add(material_data)
                db.flush()
                opening_door_frame_material_id = material_data.id
                
                # Update material charges (calculate base/sell amounts with discounts, margins, etc.)
                material_costs = await update_opening_door_frame_material_charges(
                    db, opening_door_frame_material_id, return_updated_values=True
                )

                # Calculate the total base cost and sell cost and final base cost and final sell cost
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
                
                # Sync schedule master data if material is associated with schedules
                await sync_material_schedule_data(db, opening_door_frame_material_id)
                
                db.commit()
                
                # Return success message and created material ID
                return {
                    "id": opening_door_frame_material_id, 
                    "message": "Opening Door/Frame material added.", 
                    "status": "success"
                }
            else:
                return JSONResponse(
                    content={"message": "Short Code already exists in the current project"}, 
                    status_code=400
                )
                
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"add_door_frame_material:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def update_door_frame_material(
    material_req_data: OpeningDoorFrameMaterial, 
    current_member: Members, 
    db: Session
):
    """**Summary:**
    Update opening door/frame material in the database.

    **Args:**
    - material_req_data (OpeningDoorFrameMaterial): door/frame material update data.
    - current_member (Members): The current member (user) making the request.
    - db (Session): The database session.

    **Return:**
    - `id` (str): updated door/frame material id
    - `message` (str): A message indicating the result of the operation.
    - `status` (str): Status of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Ensure that only set fields are considered
            material_req_data = material_req_data.model_dump(exclude_unset=True)
            
            # Retrieve existing door/frame material data
            door_frame_material_data = db.query(OpeningDoorFrameMaterials).get(material_req_data['id'])
            
            if not door_frame_material_data:
                return JSONResponse(
                    content={"message": "Invalid opening door/frame material ID"}, 
                    status_code=400
                )
            
            # Get quantity and total_amount for recalculation
            quantity = material_req_data.get("quantity", door_frame_material_data.quantity)
            total_amount = material_req_data.get("total_amount", door_frame_material_data.total_amount)

            # Check and update shortcode if provided
            if "short_code" in material_req_data:
                short_code = material_req_data["short_code"]
                project_short_code_exist = await is_opening_door_frame_short_code_exists(
                    door_frame_material_data.project_id, short_code, db, material_req_data['id']
                )
                if project_short_code_exist:
                    return JSONResponse(
                        content={"message": "Shortcode Already in used"}, 
                        status_code=400
                    )

            # Generate description if relevant fields are provided
            if all(k in material_req_data for k in ["series", "base_feature", "adon_feature"]):
                raw_material_code = material_req_data.get('raw_material_code', door_frame_material_data.raw_material_code)
                desc = await get_description(
                    db,
                    {},
                    material_req_data["series"],
                    raw_material_code,
                    material_req_data["base_feature"],
                    material_req_data["adon_feature"],
                )
                material_req_data["desc"] = desc

            # Update material data with current member's ID
            material_req_data['updated_by'] = current_member.id
            for key, value in material_req_data.items():
                setattr(door_frame_material_data, key, value)
            
            db.flush()

            # Update material charges (calculate base/sell amounts with discounts, margins, etc.)
            material_costs = await update_opening_door_frame_material_charges(
                db, door_frame_material_data.id, return_updated_values=True
            )
            
            # Update final amounts based on quantity and recalculated costs
            quantity = door_frame_material_data.quantity
            if material_costs is not None:
                door_frame_material_data.final_base_amount = quantity * material_costs["total_base_amount"]
                door_frame_material_data.final_sell_amount = quantity * material_costs["total_sell_amount"]
                door_frame_material_data.final_extended_sell_amount = quantity * material_costs["total_extended_sell_amount"]
            
            db.flush()
            
            # Sync schedule master data with latest material changes
            await sync_material_schedule_data(db, door_frame_material_data.id)
            
            db.commit()

        # Return success message and updated material ID
        return {
            "id": material_req_data['id'], 
            "message": "Opening Door/Frame material updated.", 
            "status": "success"
        }
    
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"update_door_frame_material:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def delete_door_frame_material(
    door_frame_material_id: str, 
    current_member: Members, 
    db: Session
):
    """**Summary:**
    Delete door/frame material from the database (soft delete).

    **Args:**
    - door_frame_material_id (str): The ID of the door/frame material to be removed.
    - current_member (Members): The current member (user) making the request.
    - db (Session): The database session.

    **Return:**
    - `message` (str): A message indicating the result of the operation.
    - `status` (str): Status of the operation.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Retrieve door/frame material data based on the provided ID
            door_frame_material_data = db.query(OpeningDoorFrameMaterials).get(door_frame_material_id)

            # Check if door/frame material data exists
            if not door_frame_material_data:
                return JSONResponse(
                    content={"message": "Invalid opening door/frame material ID"}, 
                    status_code=400
                )
            
            # Check if material is assigned to any schedule
            assigned_schedule_data = db.query(ScheduleOpeningDoorFrameMaterials).filter(
                ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id == door_frame_material_data.id
            ).first()
            
            if assigned_schedule_data:
                return JSONResponse(
                    content={
                        "message": "Door/Frame material is assigned to opening. In order to delete the item this needs to be unassigned."
                    }, 
                    status_code=400
                )
            
            # Soft delete the material
            update_data = {'is_deleted': True, 'deleted_at': datetime.now()}
            db.query(OpeningDoorFrameMaterials).filter(
                OpeningDoorFrameMaterials.id == door_frame_material_data.id
            ).update(update_data)
            db.flush()
            db.commit()
        
        return {"message": "Material Deleted.", "status": "success"}
    
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"delete_door_frame_material:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def clone_door_frame_material(
    project_id: str, 
    door_frame_material_id: str, 
    short_code: str, 
    current_member: Members, 
    db: Session
):
    """**Summary:**
    Clone an opening door/frame material.

    **Args:**
    - project_id (str): The project ID where the material will be cloned.
    - door_frame_material_id (str): The ID of the door/frame material to clone.
    - short_code (str): The new short code for the cloned material.
    - current_member (Members): The current member (user) making the request.
    - db (Session): The database session.

    **Return:**
    - `id` (str): cloned door/frame material id
    - `message` (str): A message indicating the result of the operation.
    - `status` (str): Status of the operation.
    """
    try:
        # Check for existing door/frame material with the same short code and project ID
        short_code_exists = db.query(OpeningDoorFrameMaterials).filter(
            OpeningDoorFrameMaterials.short_code == short_code,
            OpeningDoorFrameMaterials.project_id == project_id
        ).first()

        if short_code_exists:
            return JSONResponse(
                content={"message": "Opening Door/Frame short code already exists", "status": "error"}, 
                status_code=422
            )

        # Retrieve the original door/frame material data
        door_frame_material_data = db.query(OpeningDoorFrameMaterials).get(door_frame_material_id)
        if not door_frame_material_data:
            return JSONResponse(
                content={"message": "Opening Door/Frame Material not found", "status": "error"}, 
                status_code=404
            )

        # Prepare the new door/frame material data
        new_door_frame_material_data = door_frame_material_data.to_dict
        new_door_frame_material_data["created_by"] = current_member.id
        new_door_frame_material_data["short_code"] = short_code
        new_door_frame_material_data["project_id"] = project_id
        del new_door_frame_material_data["id"]

        # Create and add the new door/frame material
        new_door_frame_material = OpeningDoorFrameMaterials(**new_door_frame_material_data)
        db.add(new_door_frame_material)
        db.flush()  # Flush to get the ID of the new material
        new_door_frame_material_id = new_door_frame_material.id
        db.commit()

        # Return the result of the operation
        return {
            "id": new_door_frame_material_id, 
            "message": "Data cloned successfully.", 
            "status": "success"
        }

    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        return JSONResponse(
            content={"message": "An integrity error occurred.", "status": "error"}, 
            status_code=500
        )

    except Exception as error:
        logger.exception(f"clone_door_frame_material:: An unexpected error occurred: {error}")
        db.rollback()
        return JSONResponse(
            content={"message": "An unexpected error occurred.", "status": "error"}, 
            status_code=500
        )


async def assign_door_frame_material_to_schedule(
    opening_door_frame_material_id: str,
    schedule_id: str,
    part_number: Optional[str],
    current_member: Members,
    db: Session
):
    """**Summary:**
    Assign a door/frame material to a schedule and populate ScheduleData from master data.

    This function:
    - Creates the junction table entry (ScheduleOpeningDoorFrameMaterials)
    - Extracts schedule_master_data from the material
    - Creates ScheduleData records for each field in the master data
    - Links all data to the specified schedule

    **Args:**
    - opening_door_frame_material_id (str): ID of the door/frame material to assign
    - schedule_id (str): ID of the schedule to assign to
    - current_member (Members): The current member (user) making the request
    - db (Session): The database session

    **Return:**
    - Dictionary with success message and count of created schedule data records
    - JSONResponse with error message if operation fails
    """
    try:
        if db.in_transaction():
            db.commit()
        
        with db.begin():
            # Verify the material exists
            material = db.query(OpeningDoorFrameMaterials).filter(
                OpeningDoorFrameMaterials.id == opening_door_frame_material_id,
                OpeningDoorFrameMaterials.is_active == True
            ).first()
            
            if not material:
                return JSONResponse(
                    content={"message": "Door/Frame material not found or inactive"}, 
                    status_code=404
                )
            material_type = material.material_type
            material_type= material_type.upper() if isinstance(material_type, str) else material_type.value.upper()
            if material_type=="DOOR" and not part_number:
                return JSONResponse(
                    content={"message": "Part number is required for door materials"}, 
                    status_code=400
                )
            # Verify the schedule exists
            schedule = db.query(Schedules).filter(
                Schedules.id == schedule_id
            ).first()
            
            if not schedule:
                return JSONResponse(
                    content={"message": "Schedule not found"}, 
                    status_code=404
                )
            
            # Validate material_type

            if material_type not in ['DOOR', 'FRAME']:
                return JSONResponse(
                    content={"message": "Invalid material_type. Must be 'DOOR' or 'FRAME'"}, 
                    status_code=400
                )
            
            # Check if any other material is already assigned to this schedule
            other_material_assignment = db.query(ScheduleOpeningDoorFrameMaterials).filter(
                ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id,
                ScheduleOpeningDoorFrameMaterials.material_type == material_type,
                ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id != opening_door_frame_material_id
            ).first()
            
            if other_material_assignment:
                return JSONResponse(
                    content={
                        "message": "Another material is already assigned to this schedule. Please remove the previous assignment first."
                    }, 
                    status_code=400
                )
            
            # Check if this exact material is already assigned to this schedule
            existing_assignment = db.query(ScheduleOpeningDoorFrameMaterials).filter(
                ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id == opening_door_frame_material_id,
                ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id
            ).first()
            
            if existing_assignment:
                return JSONResponse(
                    content={"message": "This material is already assigned to this schedule"}, 
                    status_code=400
                )
            
            component_type = material_type
            
            # Create the junction table entry
            schedule_material_data = {
                'desc': material.desc,
                'material_type': component_type,
                'total_amount': material.total_amount,
                'total_sell_amount': material.total_sell_amount,
                'total_base_amount': material.total_base_amount,
                'total_extended_sell_amount': material.total_extended_sell_amount,
                'quantity': material.quantity or 1,
                'final_amount': material.final_amount,
                'final_sell_amount': material.final_sell_amount,
                'final_base_amount': material.final_base_amount,
                'final_extended_sell_amount': material.final_extended_sell_amount,
                'opening_door_frame_material_id': opening_door_frame_material_id,
                'schedule_id': schedule_id,
                'part_number': part_number
                
            }
            
            new_schedule_material = ScheduleOpeningDoorFrameMaterials(**schedule_material_data)
            db.add(new_schedule_material)
            db.flush()
            
            # Extract schedule_master_data and create ScheduleData records
            schedule_data_records = []
            
            if material.schedule_master_data:
                master_data = material.schedule_master_data
                
                # The structure is: {component_type: {fields: {field_name: field_data}, price_details: {...}}}
                if component_type in master_data:
                    component_data = master_data[component_type]
                    fields = component_data.get('fields', {})
                    print("fields", json.dumps(fields, indent=2, default=str))                   
                    
                    # Create ScheduleData records from the fields
                    for field_name, field_data in fields.items():
                        # Prepare ScheduleData entry
                        schedule_data_entry = {
                            'schedule_id': schedule_id,
                            'name': field_data.get('name', field_name),
                            'feature_code': field_data.get('feature_code', field_name),
                            'value': field_data.get('value'),
                            'component': component_type,
                            'is_adon_field': field_data.get('is_adon_field', False),
                            'has_price_dependancy': field_data.get('has_price_dependancy', True),
                            'price_data': field_data.get('price_data'),
                            'markup': field_data.get('markup', 0),
                            'margin': field_data.get('margin', 0),
                            'discount': field_data.get('discount', 0),
                            'discount_type': field_data.get('discount_type', 'PERCENTAGE'),
                            'surcharge': field_data.get('surcharge', 0),
                            'surcharge_type': field_data.get('surcharge_type', 'PERCENTAGE'),
                            'is_basic_discount': field_data.get('is_basic_discount', True),
                            'quantity': material.quantity or 1,
                            'latest_data': True,
                            'part_number': part_number
                            # 'created_by': current_member.id
                        }
                        
                        # Create the ScheduleData record
                        new_schedule_data = ScheduleData(**schedule_data_entry)
                        schedule_data_records.append(new_schedule_data)
                    
                    # Bulk insert all ScheduleData records
                    if schedule_data_records:
                        db.add_all(schedule_data_records)
                        db.flush()
                        
                        # Update schedule charges to recalculate pricing
                        await update_schedule_charges(db, schedule_id)
                        db.flush()
                        await update_schedule_stats(db, schedule_id)
                        db.flush()
            
            db.commit()
            
            return {
                "message": "Door/Frame material assigned to schedule successfully",
                "status": "success",
                "schedule_data_count": len(schedule_data_records),
                "component_type": component_type
            }
    
    except Exception as error:
        logger.exception(f"assign_door_frame_material_to_schedule:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def unassign_door_frame_material_from_schedule(
    opening_door_frame_material_id: str,
    schedule_id: str,
    current_member: Members,
    db: Session
):
    """**Summary:**
    Unassign a door/frame material from a schedule and remove associated ScheduleData.

    This function:
    - Verifies the assignment exists
    - Deletes all ScheduleData records associated with the schedule and material
    - Removes the junction table entry (ScheduleOpeningDoorFrameMaterials)

    **Args:**
    - opening_door_frame_material_id (str): ID of the door/frame material to unassign
    - schedule_id (str): ID of the schedule to unassign from
    - current_member (Members): The current member (user) making the request
    - db (Session): The database session

    **Return:**
    - Dictionary with success message
    - JSONResponse with error message if operation fails
    """
    try:
        if db.in_transaction():
            db.commit()
        
        with db.begin():
            # Verify the assignment exists
            assignment = db.query(ScheduleOpeningDoorFrameMaterials).filter(
                ScheduleOpeningDoorFrameMaterials.opening_door_frame_material_id == opening_door_frame_material_id,
                ScheduleOpeningDoorFrameMaterials.schedule_id == schedule_id
            ).first()
            
            if not assignment:
                return JSONResponse(
                    content={"message": "This material is not assigned to this schedule"}, 
                    status_code=404
                )
            
            # Get the material type from the assignment
            component_type = assignment.material_type.upper() if isinstance(assignment.material_type, str) else assignment.material_type.value.upper()
            
            # Delete all ScheduleData records for this schedule and component type
            deleted_count = db.query(ScheduleData).filter(
                ScheduleData.schedule_id == schedule_id,
                ScheduleData.component == component_type
            ).delete(synchronize_session=False)
            
            # Delete the junction table entry
            db.delete(assignment)
            db.flush()
            
            # Update schedule charges and stats after removal
            await update_schedule_charges(db, schedule_id)
            db.flush()
            await update_schedule_stats(db, schedule_id)
            db.flush()
            
            db.commit()
            
            return {
                "message": "Door/Frame material unassigned from schedule successfully",
                "status": "success",
                "schedule_data_deleted": deleted_count,
                "component_type": component_type
            }
    
    except Exception as error:
        logger.exception(f"unassign_door_frame_material_from_schedule:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def update_door_and_frame_material_desc(
    material_id: str,
    material_desc: UpdateMaterialDescriptionRequest,
    current_member: Members,
    db: Session,
):
    """**Summary:**
    Update an opening door/frame material description.

    **Args:**
    - material_id (str): The ID of the opening door/frame material to update.
    - material_desc (UpdateMaterialDescriptionRequest): Updated material description.
    - current_member (Members): Current logged-in member details.
    - db (Session): The database session.

    **Return:**
    - JSONResponse with success message and opening_door_frame_material_id.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            existing_material = (
                db.query(OpeningDoorFrameMaterials)
                .filter(
                    OpeningDoorFrameMaterials.id == material_id,
                    OpeningDoorFrameMaterials.is_deleted == False,
                )
                .first()
            )

            if not existing_material:
                return JSONResponse(
                    status_code=404,
                    content={
                        "message": "Opening door/frame material not found",
                        "status": "error",
                    },
                )

            update_data = {
                "desc": material_desc.description,
                "updated_by": current_member.id,
                "updated_at": datetime.now(),
            }

            db.query(OpeningDoorFrameMaterials).filter(
                OpeningDoorFrameMaterials.id == material_id
            ).update(update_data)
            db.flush()

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Opening material updated successfully",
                    "status": "success",
                    "opening_material_id": material_id,
                },
            )

    except Exception as error:
        logger.exception(f"update_door_and_frame_material_desc error: {error}")
        return JSONResponse(content={"message": str(error)}, status_code=500)

