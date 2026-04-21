"""
This module contains functions for handling notes.
"""
from datetime import datetime
from typing import List
from loguru import logger
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.note_templates import NoteTemplates
from models.project_take_of_sheet_notes import ProjectTakeOffSheetNotes
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from utils.common import get_user_time
from sqlalchemy.orm import Session
from models.members import Members
from schemas.notes_schemas import NoteTemplates as NoteTemplatesScheam, ProjectTakeOffSheetNotes as ProjectTakeOffSheetNotesSchema, \
    ProjectTakeOffSheetNotesDeleteRequest, ProjectTakeOffSheetNotesResponse


async def get_note_templates(db: Session):
    """**Summary:**
    fetch all note_templates.

    **Args:**
    - `db` (Session): The database session.

    **Returns:**
    - dict: A dictionary containing information about all note_templates
        - `data` (dict): A dictionary containing all note_template data:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        note_templates_data = (
            db.query(NoteTemplates)
            .filter(
                NoteTemplates.is_deleted == False
            )
            .all()
        )
        response = {"data": note_templates_data, "message": "Data fetch successfull"}
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error



async def get_take_off_sheet_notes(db: Session, project_id: str, project_raw_material_id: str):
    """**Summary:**
    fetch all notes for a take of sheet.

    **Args:**
    - `db` (Session): The database session.
    - `project_id` (str): The project_id of the take_off_sheet for which we want notes.
    - `project_raw_material_id` (str): The project_raw_material_id for which we want notes.

    **Returns:**
    - dict: A dictionary containing information about all notes of a take off sheet
        - `data` (dict): A dictionary containing all notes data of a take off sheet:
        - `message` (str): A message indicating the result of the operation.
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
        if not take_off_sheet_data:
            return JSONResponse(content={"message": f"Takeoff sheet not exist."}, status_code=406)
        
        take_off_sheet_id = take_off_sheet_data.id
        if project_raw_material_id is not None:
            notes_data = (
                db.query(ProjectTakeOffSheetNotes)
                .filter(
                    ProjectTakeOffSheetNotes.is_deleted == False,
                    ProjectTakeOffSheetNotes.project_take_off_sheet_id == take_off_sheet_id,
                    ProjectTakeOffSheetNotes.project_raw_material_id == project_raw_material_id,
                )
                .all()
            )
        else:
            notes_data = (
                db.query(ProjectTakeOffSheetNotes)
                .filter(
                    ProjectTakeOffSheetNotes.is_deleted == False,
                    ProjectTakeOffSheetNotes.project_take_off_sheet_id == take_off_sheet_id,
                    ProjectTakeOffSheetNotes.project_raw_material_id.is_(None),
                )
                .all()
            )

        response = {"data": notes_data, "message": "Data fetch successfull"}
        return response
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
    
async def add_take_off_sheet_notes(
    project_id: str, 
    take_off_sheet_notes_req_data: List[ProjectTakeOffSheetNotesSchema], 
    current_member: Members, 
    db: Session
    ):
    """**Summary:**
    This module is responsible for creating a note for a take off sheet.

    **Args:**
    - `project_id` (str): The project_id of the take_off_sheet for which we want to add note.
    - `take_off_sheet_note_req_data` ([dict]): take off sheet notes create data.
    - `db` (Session): The database session.
    - `current_member` (Members): This will contain member details of current loggedin member.

        - `take_off_sheet_note_id` (str): created take off sheet note id:
        - `message` (str): A message indicating the result of the operation.
    """
    try:
        project_take_off_sheet_note_ids = []
        take_off_sheet_data = (
            db.query(ProjectTakeOffSheets)
            .filter(
                ProjectTakeOffSheets.is_deleted == False,
                ProjectTakeOffSheets.project_id == project_id,
            )
            .first()
        )
        take_off_sheet_id = take_off_sheet_data.id
        # check if there is no notes sent from api that means user wants to delete all general notes
        if len(take_off_sheet_notes_req_data) == 0:
            update_data = {'is_deleted': True, 'deleted_at': datetime.now(), 'deleted_by': current_member.id}
            (
                db.query(ProjectTakeOffSheetNotes)
                .filter(
                    ProjectTakeOffSheetNotes.project_take_off_sheet_id.in_([take_off_sheet_id]),
                    ProjectTakeOffSheetNotes.project_raw_material_id == None,
                    ProjectTakeOffSheetNotes.is_deleted == False
                )
                .update(update_data)
            )
        # Following section will check if the call is for adding page notes or adding project raw material notes
        # Collect those take off sheet ids for which user wants to add page notes
        # (i.e for which project_raw_material_id is none).
        found_sheet_id_list = []
        for take_off_sheet_note_req_data in take_off_sheet_notes_req_data:
            take_off_sheet_note_req_data = take_off_sheet_note_req_data.model_dump(exclude_unset=True)
            take_off_sheet_note_req_data["project_take_off_sheet_id"] = take_off_sheet_id
            if "project_raw_material_id" not in take_off_sheet_note_req_data:
                if take_off_sheet_note_req_data["project_take_off_sheet_id"] not in found_sheet_id_list:
                    found_sheet_id_list.append(take_off_sheet_note_req_data["project_take_off_sheet_id"])
        if len(found_sheet_id_list) > 0:
            # In case the call is indicationg its for adding page notes
            # temporaryly delete all notes for all of the take off sheet notes.
            update_data = {'is_deleted': True, 'deleted_at': datetime.now(), 'deleted_by': current_member.id}
            (
                db.query(ProjectTakeOffSheetNotes)
                .filter(
                    ProjectTakeOffSheetNotes.project_take_off_sheet_id.in_(found_sheet_id_list),
                    ProjectTakeOffSheetNotes.project_raw_material_id == None,
                    ProjectTakeOffSheetNotes.is_deleted == False
                )
                .update(update_data)
            )
            db.commit()

        for take_off_sheet_note_req_data in take_off_sheet_notes_req_data:
            take_off_sheet_note_req_data = take_off_sheet_note_req_data.model_dump(exclude_unset=True)
            take_off_sheet_note_req_data["project_take_off_sheet_id"] = take_off_sheet_id
            if "id" in take_off_sheet_note_req_data:
                if take_off_sheet_note_req_data.get("project_raw_material_id") is None:
                    # In case there is an id that means it will work as update.
                    update_data = {'is_deleted': False, 'deleted_at': None, 'deleted_by': None}
                    (
                        db.query(ProjectTakeOffSheetNotes)
                        .filter(
                            ProjectTakeOffSheetNotes.id == take_off_sheet_note_req_data["id"],
                            ProjectTakeOffSheetNotes.is_deleted == True
                        )
                        .update(update_data)
                    )
                project_take_off_sheet_note_ids.append(take_off_sheet_note_req_data["id"])
            else:
                # In case there is no id that means need to create the note
                take_off_sheet_note_req_data["created_by"] = current_member.id
                # Create an instance of the model
                notes_data = ProjectTakeOffSheetNotes(**take_off_sheet_note_req_data)
                # Add to the database and commit
                db.add(notes_data)
                db.flush()
                # Retrieve the ID and return the result
                project_take_off_sheet_note_id = notes_data.id
                project_take_off_sheet_note_ids.append(project_take_off_sheet_note_id)
        db.commit()
        return {"ids": project_take_off_sheet_note_ids, "message": "take off sheet note Added.", "status": "success"}
    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
    
    


async def delete_take_off_sheet_notes(
    delete_req_data: ProjectTakeOffSheetNotesDeleteRequest, 
    current_member: Members, 
    db: Session
    ):
    """**Summary:**
    This module is responsible for deleting a note from a take off sheet.

    **Args:**
    - delete_req_data (dict): request body will contain list of take off sheet note ids to be deleted.
    - `db` (Session): The database session.
    - current_member (Members): This will contain member details of current loggedin member.

        - `message` (str): A message indicating the result of the operation.
    """
    try:
        delete_req_data = dict(delete_req_data)
        take_off_sheet_note_ids = delete_req_data["take_off_sheet_note_ids"]
        (
            db.query(ProjectTakeOffSheetNotes)
            .filter(
                ProjectTakeOffSheetNotes.id.in_(take_off_sheet_note_ids)
            )
            .delete(synchronize_session=False) 
        )
        db.commit()
        return {"message": "Data deleted successfully.", "status": "success"}
    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        raise error
    
    
async def update_take_off_sheet_note(
    id: str, 
    take_off_sheet_note_req_data: ProjectTakeOffSheetNotesSchema, 
    current_member: Members, 
    db: Session
    ):
    """**Summary:**
    This method updates take_off_sheet_note data based on the provided take_off_sheet_note ID.

    **Args:**
        - db (Session): db session reference
        - id (int): ID of the take_off_sheet_note to be updated
        - take_off_sheet_note_req_data (Charges): Updated take_off_sheet_note data. Refer to the Notes schema for the structure
        - current_member (Members): This will contain member details of current loggedin member.
    """
    try:
        existing_sheet_note = db.query(ProjectTakeOffSheetNotes).filter(ProjectTakeOffSheetNotes.id == id, ProjectTakeOffSheetNotes.is_deleted == False).first()

        if existing_sheet_note:
            take_off_sheet_note_req_data = take_off_sheet_note_req_data.model_dump(exclude_unset=True)

            take_off_sheet_note_req_data['updated_by'] = current_member.id

            for key, value in take_off_sheet_note_req_data.items():
                setattr(existing_sheet_note, key, value)
            db.commit()
            return {"message": f"Data updated successfully.", "status": "success"}
        else:
            return JSONResponse(content={"message": f"sheet note not found."}, status_code=400)
    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error