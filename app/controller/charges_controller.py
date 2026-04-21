"""
This file contains all operations related to take-off sheet charges.
"""
from loguru import logger
from repositories.update_stats_repositories import get_installation_adon_charges, update_raw_material_stats
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.project_take_off_sheet_charges import ProjectTakeOffSheetCharges
from models.project_raw_materials import ProjectRawMaterials, CATEGORY, DISCOUNT_TYPE, SURCHARGE_TYPE
from models.raw_materials import RawMaterials
from models.sections import Sections
from sqlalchemy.orm import Session
from schemas.charges_schemas import ProjectTakeOffSheetCharges as ProjectTakeOffSheetChargesSchema
from models.members import Members
from fastapi.responses import JSONResponse
from repositories.charge_repositories import update_installtion_stats
from starlette import status
from datetime import datetime
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from sqlalchemy import func


async def add_take_off_sheet_charge(
    db: Session, 
    project_id: str, 
    take_off_sheet_charge_req_data: ProjectTakeOffSheetChargesSchema, 
    current_member: Members,
):
    """
    Adds or updates a take-off sheet charge associated with a project in the database.

    Args:
        db: Database session object.
        project_id (int): Identifier of the project.
        take_off_sheet_charge_req_data (dict): Request data for the take-off sheet charge.
        current_member: Current member object performing the operation.
    """
    try:
        take_off_sheet_data = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.is_deleted == False,
                ProjectTakeOffSheets.project_id == project_id,
            )
            .first()
        )
        take_off_sheet_id = take_off_sheet_data.id
        
        charges_data = (
            db.query(ProjectTakeOffSheetCharges)
            .filter(
                ProjectTakeOffSheetCharges.project_take_off_sheet_id == take_off_sheet_id,
                ProjectTakeOffSheetCharges.charge_type == take_off_sheet_charge_req_data.charge_type,
            )
            .first()
        )

        take_off_sheet_charge_req_data = take_off_sheet_charge_req_data.model_dump(exclude_unset=True)
        take_off_sheet_charge_req_data['project_take_off_sheet_id'] = take_off_sheet_id
        if charges_data:
            
            take_off_sheet_charge_req_data['updated_by'] = current_member.id
            
            for key, value in take_off_sheet_charge_req_data.items():
                setattr(charges_data, key, value)
            db.commit()

            response = {"message": "Charge updated successfully"}

        else:
            take_off_sheet_charge_req_data['created_by'] = current_member.id
            new_record = ProjectTakeOffSheetCharges(**take_off_sheet_charge_req_data)
            db.add(new_record)
            db.commit()
            created_id = new_record.id

            response = {"id": created_id, "message": "Charge added successfully"}

        return response
    
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_take_off_sheet_charges(db: Session, project_id: str):
    """
    Retrieves charges data associated with a project's take-off sheet from the database.

    Args:
        db: Database session object.
        project_id (int): Identifier of the project.

    Returns:
        dict: A dictionary containing charges data and a success message.
            {
                "data": List[ProjectTakeOffSheetCharges]: List of charge data objects.
                "message": str: A message indicating successful data fetch.
            }

    Raises:
        Exception: If an unexpected error occurs during data retrieval.
    """
    try:
        take_off_sheet_data = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.is_deleted == False,
                ProjectTakeOffSheets.project_id == project_id
            )
            .first()
        )

        if not take_off_sheet_data:
            return JSONResponse(content={"message": f"Takeoff sheet not exist."}, status_code=406)
        
        take_off_sheet_id = take_off_sheet_data.id

        
        charges_data = (
            db.query(ProjectTakeOffSheetCharges)
            .filter(

                ProjectTakeOffSheetCharges.project_take_off_sheet_id == take_off_sheet_id,
            )
            .all()
        )

        response = {"data": charges_data, "message": "Data fetch successfully"}
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def update_installation_charge(
    db: Session, 
    project_id: str, 
    takeoff_sheet_section_area_item_id: str,
    charge_amount: float,
    current_member: Members,
):
    """
    Adds or updates an installation charge for a specific section area item within a project's take-off sheet.

    This function locates the specified project take-off sheet by project ID and updates the installation charge
    for the given section area item. If the take-off sheet or section area item is not found, an error response is returned.

    Args:
        db (Session): The active database session.
        project_id (str): Unique identifier of the project.
        takeoff_sheet_section_area_item_id (str): Unique identifier of the take-off sheet section area item.
        charge_amount (float): The amount to set for the installation charge.
        current_member (Members): The member performing the update, used to log the change.

    Returns:
        JSONResponse: A JSON response with a success message upon updating the installation charge, 
        or an error message if the operation fails.

    Raises:
        Exception: If any unexpected error occurs during the operation.
    """
    try:
        with db.begin():
            # Get the project take-off sheet to validate `project_id`
            take_off_sheet_data = (
                db.query(ProjectTakeOffSheets)
                .filter(
                    ProjectTakeOffSheets.is_deleted == False,
                    ProjectTakeOffSheets.project_id == project_id,
                )
                .first()
            )
            
            if not take_off_sheet_data:
                return JSONResponse(
                    content={"message": "No take-off sheet found for the provided project ID."},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Find the specific section area item by ID
            takeoff_sheet_section_area_item = db.query(ProjectTakeOffSheetSectionAreaItems).filter(
                ProjectTakeOffSheetSectionAreaItems.id == takeoff_sheet_section_area_item_id,
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == take_off_sheet_data.id
            ).first()

            if not takeoff_sheet_section_area_item:
                return JSONResponse(
                    content={"message": "No take-off sheet section area item found for the provided ID."},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Update the installation charge
            takeoff_sheet_section_area_item.installation_charge = None if charge_amount == 0 else charge_amount
            
            takeoff_sheet_section_area_item.updated_at = datetime.now()
            takeoff_sheet_section_area_item.updated_by = current_member.id
            db.flush()
            await update_raw_material_stats(db, project_id)
            # await update_installtion_stats(db, take_off_sheet_data.id, project_id)
        db.commit()

        return JSONResponse(status_code=200, content={"message": "Installation charge updated successfully.", "status": "success"})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        return JSONResponse(content={"message": "Failed to update installation charge."}, status_code=500)

