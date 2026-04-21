"""
This file contains all the database operations related to quotations.
"""
from loguru import logger
from models.projects import Projects
from models.project_take_off_sheets import ProjectTakeOffSheets
from models.members import Members
from models.clients import Clients
from models.quotation_revision import QuotationRevision
from models.project_take_of_sheet_notes import ProjectTakeOffSheetNotes
from sqlalchemy import or_, and_, update, case, func, Column, Integer, String, cast, Float, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

async def get_project_info(db: Session, project_id: str):
    """
    Retrieve project information based on project ID.
    """
    try:
        project = (
            db.query(
                Projects.id,
                Projects.name.label('project_name'),
                Projects.project_code.label('project_code'),
                func.concat(Projects.street_address, ', ', Projects.province, ', ', Projects.country, ', ', Projects.postal_code).label('project_location'),
                Projects.has_quotation,
                Projects.quotation_number
            )
            .filter(
                Projects.id == project_id,
                Projects.is_deleted == False
            )
            .first()
        )
        return project
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"Error getting project info: {e}")
        raise e


async def update_project(db: Session, project_id: int, new_data: dict):
    """
    Update take-off sheet for a project with new data.
    """
    try:
        # Step 1: Retrieve the Projects
        project = (
            db.query(Projects)
            .filter(
                Projects.id == project_id,
                Projects.is_deleted == False
            )
            .first()
        )

        if not project:
            raise Exception("Invalid project ID.")

        # Step 2: Update the Projects's attributes if it exists
        for key, value in new_data.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        # Step 3: Commit the changes
        db.commit()
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"Error updating project: {e}")
        raise e


async def get_user_details(db: Session, member_id: str):
    """
    Retrieve user details based on member ID.
    """
    try:
        user = (
                db.query(
                    func.concat(Members.first_name, ' ', Members.last_name).label('full_name'),
                    Members.email.label('email'),
                    Members.phone.label('phone'),
                )
                .filter(
                    Members.id == member_id,
                    Members.is_deleted==False
                )
                .first()
            )
        return user
    except Exception as e:
        # Log the exception with a detailed error message
        logger.exception(f"Error getting user details: {e}")
        raise e
    

async def add_revision(db: Session, project_id: str, current_member: Members):
    try:
        # Query to get the maximum revision number
        max_revision = (db.query(func.max(cast(QuotationRevision.revision_number, Integer)))
                .join(Projects, QuotationRevision.project_id == Projects.id)
                .filter(QuotationRevision.project_id == project_id, Projects.is_deleted == False)
                .scalar())
        
        # Increment the max_revision or set it to 1 if None
        if max_revision is not None:
            generated_revision_number = max_revision + 1
        else:
            generated_revision_number = 1

        # Create a new QuotationRevision instance
        quotation_revision_dict = {
            "project_id": project_id, 
            "file_path": "", 
            "revision_number": generated_revision_number, 
            "created_by": current_member.id
            }
        quotation_revision = QuotationRevision(**quotation_revision_dict)
        db.add(quotation_revision)
        db.commit()
        inserted_id = quotation_revision.id

        return quotation_revision_dict['revision_number'], inserted_id

    except Exception as e:
        # Handle exceptions
        logger.exception(f"Error adding revision: {e}")
        raise e
    

async def generate_quotation_number(db: Session, project_id: str):
    try:
        # Execute the query to get the max quotation number
        max_quotation_number = (db.query(
            func.max(cast(Projects.quotation_number, Integer)))
            .filter(Projects.id == project_id, Projects.is_deleted == False).scalar())
        
        # Calculate the next quotation number
        generated_quotation_number = max_quotation_number if max_quotation_number else 0 + 1

        # Return the formatted quotation number as a zero-padded string
        return f"{generated_quotation_number:04}"
    
    except SQLAlchemyError as e:
        # Log the exception with a detailed error message
        logger.exception(f"Error generating quotation number: {e}")
        raise e



# Need to add client project validation
async def get_client_details(db: Session, client_id: str):
    try:
        # Query the Clients table to fetch the client with the given ID
        # and ensure the client is not marked as deleted.
        client = (
                db.query(Clients)
                .filter(
                    Clients.id == client_id,
                    Clients.is_deleted == False
                )
                .first()
            )
        # Return the client object if found, otherwise None
        return client
    
    except SQLAlchemyError as e:
        # Log the exception with a detailed error message
        logger.exception(f"Error fetching client details: {e}")
        raise e



async def get_general_notes(db: Session, project_id: str):
    
    # Query the ProjectTakeOffSheets table to get the ID of the take-off sheet
    project_take_off_sheet_data = (
            db.query(ProjectTakeOffSheets.id)
            .filter(
                ProjectTakeOffSheets.project_id == project_id
            )
            .first()
        )
    # Extract the take-off sheet ID from the query result
    project_take_off_sheet_id = project_take_off_sheet_data.id

    # Query the ProjectTakeOffSheetNotes table to get the notes for the take-off sheet
    note_data = (db.query(ProjectTakeOffSheetNotes)
           .filter(
               ProjectTakeOffSheetNotes.project_take_off_sheet_id == project_take_off_sheet_id,
               ProjectTakeOffSheetNotes.is_deleted == False,
               ProjectTakeOffSheetNotes.note_template_id.isnot(None)
           ).all())
    # Initialize an empty list to hold the notes
    notes = []
    # Convert each note to a dictionary and append to the notes list
    for item in note_data:
        notes.append(item.to_dict)
    # Return the list of notes
    return notes



async def check_for_empty_opening(db, project_id):
    try:
        query_text = """
            SELECT
				* 
			FROM
				(
					SELECT
						opening_number,
						MAX(opening_schedule_id) AS opening_schedule_id
					FROM
						(
							SELECT 
								id,
								opening_number
							FROM 
								project_take_off_sheet_section_area_items
							WHERE
								project_take_off_sheet_id in (
									SELECT
										id
									FROM
										project_take_off_sheets
									WHERE
										project_id = :project_id
								)
						) AS area_opening
						LEFT JOIN
						(
							SELECT
								id AS opening_schedule_id,
								project_take_off_sheet_section_area_item_id
							FROM
								opening_schedules
							WHERE
								project_id = :project_id
						) AS opening_schedule
						ON opening_schedule.project_take_off_sheet_section_area_item_id = area_opening.id
					GROUP BY 
						opening_number
				) AS temp
                WHERE
					temp.opening_schedule_id is NULL
        """
        result = db.execute(
            text(query_text), 
            {
                "project_id": project_id,
            }
        )
        columns = result.keys()
        rows = result.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        logger.exception(f"check_for_empty_opening:: Error : {e}")
        return None
    
