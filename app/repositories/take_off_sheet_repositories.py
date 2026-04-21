"""
This file contains all the database operations related to take off sheets.
"""
from datetime import datetime
from loguru import logger
from models.project_take_off_sheet_section_area_items import ProjectTakeOffSheetSectionAreaItems
from models.opening_schedules import OpeningSchedules
from models.project_materials import ProjectMaterials
from models.raw_materials import RawMaterials
from utils.common import get_user_time
from models.adon_opening_fields import AdonOpeningFields
from models.adon_opening_field_options import AdonOpeningFieldOptions
from models.members import Members
from repositories.update_stats_repositories import update_opening_schedule_stats, update_area_item_stats, update_section_stats, update_take_off_sheet_stats, update_raw_material_stats
from sqlalchemy.orm import Session


async def get_installed_raw_materials(db, project_id):
    try:
        # Finding out all ids of door related raw materials as installation is related to doors
        door_raw_materials = (
            db.query(RawMaterials.id)
            .filter(RawMaterials.name.ilike("%door%"))
            .all()
        )
        door_raw_material_ids = []
        for elm in door_raw_materials:
            door_raw_material_ids.append(elm[0])
        # finding out all doors that are used any area item where there is no installation charge added to it
        opening_raw_materials = (
            db.query(OpeningSchedules.raw_material_id)
            .join(
                ProjectTakeOffSheetSectionAreaItems,
                ProjectTakeOffSheetSectionAreaItems.id == OpeningSchedules.project_take_off_sheet_section_area_item_id
            )
            .filter(
                OpeningSchedules.project_id == project_id,
                OpeningSchedules.raw_material_id.in_(door_raw_material_ids),
                OpeningSchedules.is_active == True,
                ProjectTakeOffSheetSectionAreaItems.installation_charge != None,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False,
            )
            .distinct()
            .all()
        )
        installing_opening_raw_material_ids = []
        for elm in opening_raw_materials:
            installing_opening_raw_material_ids.append(elm[0])
        return installing_opening_raw_material_ids
    except Exception as error:
        print("error:: ",error)
        raise error
    
    

async def get_door_count_mapping(db):
    """
    Fetches door type data from the database and maps door type names to their respective counts.

    Args:
        db: Database session object.

    Returns:
        tuple: A tuple containing two dictionaries:
            - id_to_count_mappings: Maps door type option IDs to their respective counts.
            - name_to_count_mappings: Maps door type names to their respective counts.
    """
    try:
        door_types_data = (
            db.query(AdonOpeningFields, AdonOpeningFieldOptions)
            .join(AdonOpeningFieldOptions)
            .filter(
                AdonOpeningFields.is_active == True,
                AdonOpeningFields.name == "door_type"
            )
            .all()
        )

        name_to_count_mappings = {"single": 1, "double": 2, "multi": 3}
        id_to_count_mappings = {}
        for adon_fields, adon_field_options in door_types_data:
            id_to_count_mappings[adon_field_options.id] = name_to_count_mappings[adon_field_options.name]
        return id_to_count_mappings, name_to_count_mappings
    except Exception as e:
        print("get_door_count_mapping:: error - ",e)
        raise e


async def delete_opening(id, current_member, db):
    """**Summary:**
    This module is responsible for deleting an item for a take off sheet.

    **Note:** This module does not update any stats, it needs to handled explicitly.

    **Args:**
    - id (str): take off sheet item id to be deleted.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

        - `message` (str): A message indicating the result of the operation.
    """
    try:
        # check if its a valid opening id
        project_takeoffsheet_item_exist = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.id == id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .first()
        )
        if project_takeoffsheet_item_exist:
            # collect all project materials that are directly associated with the opening, that we are going to delete
            prject_material_ids = []
            opeing_schedule_data = (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.hardware_group_id == None,
                    OpeningSchedules.project_take_off_sheet_section_area_item_id == project_takeoffsheet_item_exist.id
                )
                .all()
            )
            for opening_mat in opeing_schedule_data:
                prject_material_ids.append(opening_mat.project_material_id)
            prject_material_ids = list(prject_material_ids)
            
            # check if any project material will be unused if we delete it from the opening if so then soft delete the material
            for prject_material_id in prject_material_ids:
                
                # delete the project material
                update_data = {'is_deleted': True, 'deleted_at': datetime.now(), 'deleted_by': current_member.id}
                (
                    db.query(ProjectMaterials)
                    .filter(
                        ProjectMaterials.id == prject_material_id,
                        ProjectMaterials.is_deleted == False
                    )
                    .update(update_data)
                )
                db.flush()
            # delete the opening schedule for the opening which we are going to delete
            (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.project_take_off_sheet_section_area_item_id == project_takeoffsheet_item_exist.id
                )
                .delete()
            )
            db.flush()
            # delte the area item/opening
            (
                db.query(ProjectTakeOffSheetSectionAreaItems)
                .filter(
                    ProjectTakeOffSheetSectionAreaItems.id == project_takeoffsheet_item_exist.id,
                )
                .delete()
            )
            db.flush()
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
    


async def is_opening_number_exists(project_take_off_sheet_id: str, opening_number: str, db: Session):
    """**Summary:**
    This module is responsible for checking if the input opening number is already exists or not in the input take off sheet.

    **Args:**
    - project_take_off_sheet_id (str): take off sheet id for which we need to check the existance.
    - opening_number (str): opening number for which we need to check the existance.
    - `db` (Session): The database session.

    **Return:**
    - `is_exists` (bool): return True if already exists otherwise False. 
    """
    try:
        is_exists = False
        
        project_takeoffsheet_section_opening_exist = (
            db.query(ProjectTakeOffSheetSectionAreaItems)
            .filter(
                ProjectTakeOffSheetSectionAreaItems.opening_number == opening_number,
                ProjectTakeOffSheetSectionAreaItems.project_take_off_sheet_id == project_take_off_sheet_id,
                ProjectTakeOffSheetSectionAreaItems.is_deleted == False
            )
            .all()
        )
        if len(project_takeoffsheet_section_opening_exist) > 0:
            is_exists = True
        return is_exists
    except Exception as error:
        logger.exception(f"is_opening_number_exists:: An unexpected error occurred: {error}")
        raise error


async def clone_sheet_area_item(
    db: Session, 
    old_opening_data: dict, 
    take_off_sheet_section_area_id: str, 
    take_off_sheet_section_id: str, 
    opening_number: str, 
    current_member: Members
):
    """**Summary:**
    Clones an existing item in the ProjectTakeOffSheetSectionAreaItems table along with its related OpeningSchedules.
    Steps:
    - step-1: Prepare and filter the collected data so that we can create a new opening with the same metadata.
    - step-2: Create a new openning with the same metadata but as a differnt opening.
    - step-3: Collect the openning schedule so that we know whate are the items associated with the opening to be cloned
    - step-4: update the stats of the section.
    - step-5: update the stats of the take off sheet.

    Parameters:
        db: SQLAlchemy database session.
        old_opening_data (dict): all metadata of the item that need to be cloned.
        take_off_sheet_section_area_id (int): The ID of the section area in which we want to place the cloned opening.
        take_off_sheet_section_id (int): The ID of the section in which we want to place the cloned opening.
        current_member: The current member performing the action.
    Returns:
        JSONResponse: A JSON response indicating the success or failure of the operation.
    """
    try:
        project_take_off_sheet_id = None
        project_id = None
        take_off_sheet_section_area_item_id = None
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # step-1: Prepare and filter the collected data so that we can create a new opening with the same metadata.
            take_off_sheet_section_area_item_id = old_opening_data["id"]
            # Update opening data with the provided opening number
            old_opening_data['opening_number'] = opening_number
            # Update opening data with the provided project_take_off_sheet_section_area_id
            old_opening_data['project_take_off_sheet_section_area_id'] = take_off_sheet_section_area_id
            # Update opening data with the provided project_take_off_sheet_section_id
            old_opening_data['project_take_off_sheet_section_id'] = take_off_sheet_section_id
            # Set the creator of the cloned item
            old_opening_data['created_by'] = current_member.id
            # Remove unnecessary fields

            if 'id' in old_opening_data:
                del old_opening_data['id']
            if 'created_at' in old_opening_data:
                del old_opening_data['created_at']
            if 'updated_at' in old_opening_data:
                del old_opening_data['updated_at']
            if 'updated_by' in old_opening_data:    
                del old_opening_data['updated_by']

            project_take_off_sheet_id = old_opening_data["project_take_off_sheet_id"]
            old_opening_data["installation_charge"] = None
            # step-2: Create a new openning with the same metadata but as a differnt opening.
            new_opening_data = ProjectTakeOffSheetSectionAreaItems(**old_opening_data)
            db.add(new_opening_data)
            db.flush()

            # Fetch opening schedule data related to the opening to be cloned.
            old_opening_opening_schedule_data = (
                db.query(OpeningSchedules)
                .filter(
                    OpeningSchedules.project_take_off_sheet_section_area_item_id == take_off_sheet_section_area_item_id
                )
                .all()
            )
            # step-3: Collect the openning schedule so that we know whate are the items associated with the opening to be cloned
            # Iterate through opening schedule data and create new entries related to the cloned item
            for opening in old_opening_opening_schedule_data:
                data_dict = opening.to_dict
                data_dict['project_take_off_sheet_section_area_item_id'] = new_opening_data.id
                data_dict['created_by'] = current_member.id
                if project_id is None:
                    project_id = data_dict['project_id']

                # Remove unnecessary fields
                if 'id' in data_dict:
                    del data_dict['id']
                if 'created_at' in data_dict:
                    del data_dict['created_at']
                if 'updated_at' in data_dict:
                    del data_dict['updated_at']
                if 'updated_by' in data_dict:    
                    del data_dict['updated_by']
                    
                # Create a new entry in the OpeningSchedules table
                new_opening_opening_schedule_data = OpeningSchedules(**data_dict)
                db.add(new_opening_opening_schedule_data)
                db.flush()

            # step-4: update the stats of the section.
            await update_section_stats(db, project_take_off_sheet_section_id=take_off_sheet_section_id)

            # step-5: update the stats of the take off sheet.
            if project_take_off_sheet_id is not None:
                await update_take_off_sheet_stats(db, project_take_off_sheet_id)
                
                #update the raw material stats after deleting the section area and its associated openings
                await update_raw_material_stats(db,project_id= project_id)

    except Exception as error:
        # Log and raise an exception in case of an unexpected error
        logger.exception(f"clone_sheet_area_item:: An unexpected error occurred: {error}")
        db.rollback()
        raise error

