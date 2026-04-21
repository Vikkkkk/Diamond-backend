"""
This file contains all the controller operations related to hardware groups.
"""
from datetime import datetime
from loguru import logger
from models.hardware_groups import HardwareGroups
from models.opening_schedules import OpeningSchedules
from models.raw_materials import RawMaterials
from models.hardware_group_materials import HardwareGroupMaterials
from models.project_materials import ProjectMaterials
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.project_take_off_sheets import ProjectTakeOffSheets
from repositories.update_stats_repositories import update_project_stats, update_opening_schedule_stats, update_area_item_stats, update_section_stats, update_take_off_sheet_stats, update_raw_material_stats
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, func
from fastapi.responses import JSONResponse
from utils.common import get_user_time
from sqlalchemy.orm import Session
from schemas.hardware_group_schemas import HardwareGroup, AssignToOpenings
from models.members import Members


async def get_hardware_groups(db: Session, project_id: str, keyword: str):
    """
    Summary:
    Retrieve a list of all hardware groups from the database.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - keyword (str): Useful for keyword search on group name.
    - project_id: ID of the project.

    Returns:
    dict: A dictionary containing the result of the operation.
          - If hardware groups are found, "data" will contain a list of hardware groups.
          - If no hardware groups are found, "message" will indicate that no groups were found.
          - "status" will indicate the status of the operation, either "success" or an error status.
    """
    try:
        # Construct the base query to retrieve hardware groups for the specified project
        query = db.query(HardwareGroups).filter(HardwareGroups.project_id == project_id)
        
        # Apply keyword filtering if provided
        if keyword:
            query = query.filter(HardwareGroups.name.ilike(f'%{keyword}%'))
        
        # Retrieve the hardware groups and order them by creation date in descending order
        hardware_groups = query.order_by(HardwareGroups.created_at.desc()).all()
        
        if not hardware_groups:
            return {"data": [], "status": "success"}
        
        # Retrieve all related opening schedules in a single query
        group_ids = [group.id for group in hardware_groups]
        opening_schedules = db.query(OpeningSchedules).filter(
            OpeningSchedules.project_id == project_id,
            OpeningSchedules.hardware_group_id.in_(group_ids)
        ).all()
        
        # Organize opening schedules by hardware group ID
        openings_by_group = {}
        for os in opening_schedules:
            if os.hardware_group_id not in openings_by_group:
                openings_by_group[os.hardware_group_id] = []
            openings_by_group[os.hardware_group_id].append(os.opening.id)
        
        # Populate response data
        resp = []
        for group in hardware_groups:
            response_data = group.to_dict
            assigned_openings = openings_by_group.get(group.id, [])
            response_data['number_of_opening_assigned'] = len(assigned_openings)
            response_data['assigned_openings'] = assigned_openings
            resp.append(response_data)
        
        # Return the response data along with the operation status
        return {"data": resp, "status": "success"}
    except Exception as error:
        logger.exception(f"get_hardware_groups:: An unexpected error occurred: {error}")
        raise error
    

async def add_hardware_group(db: Session, request_data: HardwareGroup, current_member: Members):
    """**Summary:**
    Add a new hardware group to the database.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - request_data (dict): A dictionary containing the data for the new hardware group.
    - current_member: The current member (user) who is adding the hardware group.

    Returns:
    dict: A dictionary containing the result of the operation.
          - "id": The ID of the newly inserted hardware group.
          - "message": A message indicating the success of the operation.
          - "status": The status of the operation, either "success" or an error status.

    Raises:
    IntegrityError: If there is a violation of the database integrity constraints.
    Exception: If an unexpected error occurs during the database operation.
    """
    try:
        # Exclude unset values from the request_data dictionary
        request_data = request_data.model_dump(exclude_unset=True)

        # Check if a hardware group with the same name and project ID already exists
        group_name_exists = db.query(HardwareGroups).filter(HardwareGroups.name == request_data['name'], HardwareGroups.project_id == request_data['project_id']).first()
        if not group_name_exists:
            # Add the current member ID to the request_data
            request_data['created_by'] = current_member.id
            # Create a new HardwareGroups instance with the provided data
            hardware_group = HardwareGroups(**request_data)
            # Add the new hardware group to the database session
            db.add(hardware_group)
            # Commit changes to the database
            db.commit()
            # Retrieve the ID of the newly inserted hardware group
            hardware_group_id = hardware_group.id
            return {"id": hardware_group_id,"message": "Data inserted successfully.", "status": "success"}
        
        # Return an error message if the group name already exists
        return JSONResponse(content={"message": "Group name already exists", "status": "error"}, status_code=422)
    
    except IntegrityError as i_error:
        # Log the IntegrityError and rollback the transaction in case of a database integrity violation
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        # Log any unexpected error and rollback the transaction
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    

async def update_hardware_group(db: Session, hardware_group_id: str, request_data: HardwareGroup, current_member: Members):
    """**Summary:**
    Update an existing hardware group in the database.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - id (int): The ID of the hardware group to be updated.
    - request_data (dict): A dictionary containing the updated data for the hardware group.
    - current_member: The current member (user) who is updating the hardware group.

    Returns:
    dict: A dictionary containing the result of the operation.
          - "message": A message indicating the success of the operation.
          - "status": The status of the operation, either "success" or an error status.

    Raises:
    IntegrityError: If there is a violation of the database integrity constraints.
    Exception: If an unexpected error occurs during the database operation.
    """
    try:
        request_data = request_data.model_dump(exclude_unset=True)
        # Check if the 'name' key is not present in the request_data
        if 'name' not in request_data:
            # Return a JSON response with an error message indicating that 'name' is required
            return JSONResponse(content={"message": "Name is required in the request data.", "status": "error"}, status_code=422)
        
        # Retrieve the existing hardware group data
        existing_data = db.query(HardwareGroups).filter(HardwareGroups.id == hardware_group_id).first()
        if existing_data:
            # Exclude unset values from the request data

            # Check if a hardware group with the same name already exists in the project
            group_name_exists = db.query(HardwareGroups).filter(HardwareGroups.name == request_data['name'], HardwareGroups.id !=hardware_group_id, HardwareGroups.project_id == request_data['project_id']).first()
            
            if not group_name_exists:
                # Update existing request data
                request_data['updated_by'] = current_member.id
                # Update the attributes of the existing request with the values from the request_data dictionary.
                for key, value in request_data.items():
                    setattr(existing_data, key, value)
                # Commit changes to the database
                db.commit()
                
                return {"message": f"Group updated successfully.", "status": "success"}
            
            # Return an error message if the group name already exists
            return JSONResponse(content={"message": "Group name already exists", "status": "error"}, status_code=422)
        
        else:
            # Return a not found error response if the hardware group does not exist
            return JSONResponse(content={"message": f"Hardware group not found.", "status": "error"}, status_code=400)
        
    except IntegrityError as i_error:
        # Handle IntegrityError by logging and rolling back the transaction
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        # Handle unexpected errors by logging and rolling back the transaction
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    

async def delete_hardware_group(db: Session, id: int, current_member: Members):
    """Delete a hardware group from the database."""
    try:
        hardware_group_data = db.query(HardwareGroups).get(id)
        if not hardware_group_data:
            return JSONResponse(content={"message": "Group not found.", "status": "error"}, status_code=400)

        hardware_group_in_use = db.query(OpeningSchedules).filter(OpeningSchedules.hardware_group_id == id).first()
        if hardware_group_in_use:
            return JSONResponse(content={"message": "This group is already in use!", "status": "error"}, status_code=400)

        hardware_group_materials = db.query(HardwareGroupMaterials).filter(HardwareGroupMaterials.hardware_group_id == id).all()
        project_material_ids = [material.project_material_id for material in hardware_group_materials]

        material_counts = db.query(
            HardwareGroupMaterials.project_material_id,
            func.count(HardwareGroupMaterials.project_material_id).label('count')
        ).filter(HardwareGroupMaterials.project_material_id.in_(project_material_ids)).group_by(HardwareGroupMaterials.project_material_id).all()

        material_ids_to_delete = [material.project_material_id for material in material_counts if material.count == 1]

        update_data = {'is_deleted': True, 'deleted_at': datetime.now(), 'deleted_by': current_member.id}
        db.query(ProjectMaterials).filter(ProjectMaterials.id.in_(material_ids_to_delete)).update(update_data, synchronize_session=False)
        db.query(HardwareGroupMaterials).filter(HardwareGroupMaterials.hardware_group_id == id).delete(synchronize_session=False)
        db.query(HardwareGroups).filter(HardwareGroups.id == id).delete(synchronize_session=False)

        db.commit()
        return JSONResponse(content={"message": "Data deleted successfully.", "status": "success"}, status_code=200)

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"Database error: {e}")
        return JSONResponse(content={"message": "An error occurred while deleting the data.", "status": "error"}, status_code=500)

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return JSONResponse(content={"message": "An unexpected error occurred.", "status": "error"}, status_code=500)



async def clone_hardware_group(db: Session, hardware_group_id: int, request_data: HardwareGroup, current_member: Members):
    """Clone a hardware group and its associated materials."""
    try:
        # Convert request_data to a dictionary
        request_data = request_data.model_dump(exclude_unset=True)

        # Check for existing hardware group with the same name and project ID
        group_name_exists = db.query(HardwareGroups).filter(
            HardwareGroups.name == request_data['name'],
            HardwareGroups.project_id == request_data['project_id']
        ).first()

        if group_name_exists:
            return JSONResponse(content={"message": "Group name already exists", "status": "error"}, status_code=422)

        # Retrieve the original hardware group data
        hardware_group_data = db.query(HardwareGroups).get(hardware_group_id)
        if not hardware_group_data:
            return JSONResponse(content={"message": "Hardware group not found", "status": "error"}, status_code=404)

        # Prepare the new hardware group data
        new_hardware_group_data = hardware_group_data.to_dict
        new_hardware_group_data["created_by"] = current_member.id
        new_hardware_group_data["name"] = request_data['name']
        new_hardware_group_data["project_id"] = request_data['project_id']
        del new_hardware_group_data["id"]
        # new_hardware_group_data = {
        #     'name': request_data['name'],
        #     'project_id': request_data['project_id'],
        #     'item_count': hardware_group_data.item_count,
        #     'quantity': hardware_group_data.quantity,
        #     'total_amount': hardware_group_data.total_amount,
        #     'created_by': current_member.id
        # }

        # Create and add the new hardware group
        new_hardware_group = HardwareGroups(**new_hardware_group_data)
        db.add(new_hardware_group)
        db.flush()  # Flush to get the ID of the new hardware group
        new_hardware_group_id = new_hardware_group.id

        # Retrieve and clone materials from the original hardware group
        hardware_group_materials = db.query(HardwareGroupMaterials).filter(
            HardwareGroupMaterials.hardware_group_id == hardware_group_id
        ).all()

        # new_materials = [
        #     HardwareGroupMaterials(
        #         hardware_group_id=new_hardware_group_id,
        #         project_material_id=material.project_material_id,
        #         quantity=material.quantity,
        #         created_by=current_member.id
        #     ) for material in hardware_group_materials
        # ]
        new_materials = []
        for material in hardware_group_materials:
            new_material = material.to_dict
            new_material["created_by"] = current_member.id
            new_material["hardware_group_id"] = new_hardware_group_id
            del new_material["id"]
            new_materials.append(
                HardwareGroupMaterials(
                    **new_material
                )
            )

        # Add all new material instances in a single batch
        db.add_all(new_materials)
        db.flush()
        db.commit()

        # Return the result of the operation
        return {"id": new_hardware_group_id, "message": "Data cloned successfully.", "status": "success"}

    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        return JSONResponse(content={"message": "An integrity error occurred.", "status": "error"}, status_code=500)

    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        return JSONResponse(content={"message": "An unexpected error occurred.", "status": "error"}, status_code=500)
    

async def assign_to_openings(db: Session, hardware_group_id: str, request_data: AssignToOpenings, current_member: Members):
    """
    Assign a hardware group to specified openings and update related schedules.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - hardware_group_id (int): The identifier of the hardware group.
    - request_data (dict): The request data containing the opening IDs.
    - current_member (YourMemberModel): The current member performing the assignment.

    Returns:
    - dict: A dictionary containing a success message if the assignment is successful.

    Raises:
    - IntegrityError: If there is an integrity violation during the database transaction.
    - Exception: If an unexpected error occurs during the assignment process.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Retrieve hardware group data from the database based on hardware_group_id
            hardware_group_data = db.query(HardwareGroups).get(hardware_group_id)
            
            # Check if hardware_group_data is found
            if hardware_group_data:
                # Extract relevant data from the request_data and exclude any unset values
                request_data = request_data.model_dump(exclude_unset=True) 
                hwd_raw_material = db.query(RawMaterials).filter(RawMaterials.code == "HWD").first()
                # Initialize a flag to track success
                SUCCESS = False
                deleted_opening_ids = []
                # Record the openings for which we need to delete the hw group 
                opening_schedule_deleting_datas = db.query(OpeningSchedules).filter(OpeningSchedules.hardware_group_id == hardware_group_id, OpeningSchedules.component == "HARDWARE").all()
                for opening_schedule_deleting_data in opening_schedule_deleting_datas:
                    deleted_opening_ids.append(opening_schedule_deleting_data.project_take_off_sheet_section_area_item_id)
                # Delete existing opening schedules related to the hardware group
                db.query(OpeningSchedules).filter(OpeningSchedules.hardware_group_id == hardware_group_id, OpeningSchedules.component == "HARDWARE").delete()
                
                hardware_group_ids = []
                if request_data['project_take_off_sheet_section_area_item_id']:
                    # Iterate through each project_take_off_sheet_section_area_item_id provided in the request data
                    for project_take_off_sheet_section_area_item_id in request_data['project_take_off_sheet_section_area_item_id']:
                        # Retrieve opening data from the database based on project_take_off_sheet_section_area_item_id
                        opening_data = db.query(ProjectTakeOffSheetSectionAreaItems).get(project_take_off_sheet_section_area_item_id)
                        
                        # Check if the opening exists
                        if opening_data:
                            # Record the hw groups for which we need to delete the openings 
                            opening_schedule_datas = db.query(OpeningSchedules).filter(OpeningSchedules.project_take_off_sheet_section_area_item_id == project_take_off_sheet_section_area_item_id, OpeningSchedules.component == "HARDWARE").all()
                            for opening_schedule_data in opening_schedule_datas:
                                # Need to delete the opening id for which we already have the hw group listed,
                                # As the opeinnig stats update is going to take care by the hw_group_update stats scenario
                                if opening_schedule_data.project_take_off_sheet_section_area_item_id in deleted_opening_ids:
                                    deleted_opening_ids.remove(opening_schedule_data.project_take_off_sheet_section_area_item_id)
                                hardware_group_ids.append(opening_schedule_data.hardware_group_id)

                            # Delete existing opening schedules related to the opening
                            db.query(OpeningSchedules).filter(OpeningSchedules.project_take_off_sheet_section_area_item_id == project_take_off_sheet_section_area_item_id, OpeningSchedules.component == "HARDWARE").delete()

                            # Create a new opening schedule data
                            new_opening_schedule_data = OpeningSchedules(
                                component = 'HARDWARE',
                                final_amount = hardware_group_data.total_amount,
                                final_sell_amount = hardware_group_data.total_sell_amount,
                                final_base_amount = hardware_group_data.total_base_amount,
                                total_extended_sell_amount = hardware_group_data.total_extended_sell_amount,
                                project_take_off_sheet_section_area_item_id = project_take_off_sheet_section_area_item_id,
                                raw_material_id = hwd_raw_material.id,
                                hardware_group_id = hardware_group_id,
                                project_id = hardware_group_data.project_id,
                                created_by = current_member.id
                            )
                            # Add the new opening schedule data to the session
                            db.add(new_opening_schedule_data)
                            db.flush()
                            # Set success flag to True
                            SUCCESS = True
                            message = "Opening assigned successfully"
                else:
                    db.query(OpeningSchedules).filter(OpeningSchedules.hardware_group_id == hardware_group_id, OpeningSchedules.component == "HARDWARE").delete()
                    SUCCESS = True
                    message = "Opening Unassigned successfully"
                # Check if any openings were successfully processed
                if SUCCESS:
                    for opening_id in deleted_opening_ids:
                        # update the stats of openings for which we have removed the hw association. 
                        await update_area_item_stats(
                            db,
                            project_take_off_sheet_section_area_item_id = opening_id
                        )
                        
                    hardware_group_ids.append(hardware_group_id)
                    for hardware_group_id in hardware_group_ids:
                        # Update opening scedule statistics related to the hardware group
                        take_off_sheet_section_area_item_ids = await update_opening_schedule_stats(
                            db, 
                            hardware_group_id = hardware_group_id
                        )
                        
                        for take_off_sheet_section_area_item_id in take_off_sheet_section_area_item_ids:
                            # Update area item statistics related to the hardware group
                            take_off_sheet_section_id = await update_area_item_stats(
                                db,
                                project_take_off_sheet_section_area_item_id = take_off_sheet_section_area_item_id
                            )

                            # Update section statistics related to the hardware group
                            await update_section_stats(
                                db,
                                project_take_off_sheet_section_id = take_off_sheet_section_id
                            )
                    # update the sheet stats after deleting the section area and its associated openings
                    project_take_off_data = (
                        db.query(ProjectTakeOffSheets)
                        .filter(
                            ProjectTakeOffSheets.project_id == hardware_group_data.project_id
                        )
                        .first()
                    )
                    
                    #update the sheet stats after deleting the section area and its associated openings
                    await update_take_off_sheet_stats(db,project_take_off_sheet_id= project_take_off_data.id)

                    #update the raw material stats after deleting the section area and its associated openings
                    await update_raw_material_stats(db,project_id= hardware_group_data.project_id)

                    return {"message": message, "status": "success"}
                else:
                    return {"message": "No valid openings were provided.", "status": "error"}
            else:
                # Return error message if the hardware group ID is invalid
                return {"message": "Invalid hardware group ID.", "status": "error"}
    
    except IntegrityError as i_error:
        # Handle IntegrityError by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        # Handle other unexpected errors by logging the exception, rolling back changes, and re-raising the exception
        logger.exception(f"assign_to_openings:: An unexpected error occurred: {error}")
        db.rollback()
        raise error


async def get_hardware_group_items(db: Session, hardware_group_id: str):
    """**Summary:**
    Retrieve items belonging to a hardware group from the database.

    Parameters:
    - db (Session): The SQLAlchemy database session.
    - hardware_group_id (str): The identifier of the hardware group.

    Returns:
    - dict: A dictionary containing the retrieved data.

    Raises:
    - Exception: If an unexpected error occurs during the data retrieval process.
    """
    try:
        item_data = (
            db.query(ProjectMaterials)
            .join(HardwareGroupMaterials)
            .filter(
                HardwareGroupMaterials.hardware_group_id == hardware_group_id,
                ProjectMaterials.is_deleted == False
            )
            .order_by(HardwareGroupMaterials.created_at.desc())
            .all()
        )
        response = []
        for data in item_data:
            data_dict = data.to_dict
            data_dict["product_category"] = (
                    {
                        "category": {
                            "id": data.take_off_hardware_product_category.id,
                            "name": data.take_off_hardware_product_category.name
                        }
                    }
                    if data.take_off_hardware_product_category else None
                )
            matching_entries = []
            for item in data.material_groups:
                if item.hardware_group_id == hardware_group_id:
                    matching_entries.append(item)
                    break

            data_dict['hardware_group_material_id'] = matching_entries[0].id
            data_dict['quantity'] = matching_entries[0].quantity
            data_dict['final_amount'] = matching_entries[0].final_amount
            data_dict['manufacturer_code'] = data.material_manufacturer.code
            data_dict['brand_code'] = data.material_brand.code if data.material_brand else None
            response.append(data_dict)

        return {"data": response, "message": "Data Fetch Successfully.", "status": "success"}
    except Exception as error:
        logger.exception(f"get_hardware_group_items:: An unexpected error occurred: {error}")
        raise error
