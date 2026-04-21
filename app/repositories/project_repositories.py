"""
This file contains all the database operations related to projects.
"""
from typing import List
from loguru import logger
from models.members import Members
from models.member_role import MemberRole
from models.client_projects import ClientProjects
from models.role_permissions import RolePermissions
from models.roles import Roles
from models.modules import Modules
from models.sub_modules import SubModules
from models.projects import Projects
from models.project_members import ProjectMembers
from sqlalchemy.orm import Session
from schemas.member_schema import RoleAssign
from sqlalchemy.exc import IntegrityError
import os
from sqlalchemy import or_, text, and_, not_, asc, desc


async def project_client_association(db: Session, project_id: str, client_ids: List, current_member: Members):
    """**Summary:**
    Associates project members with a specific module (e.g., "Estimation") in the database.

    **Parameters:**
    - db: The database session to perform the operation.
    - project_id: The identifier of the project to associate members with.
    - client_ids: The identifier(s) of the client(s) to associate with the project.
                It will be list of client IDs.
    - current_member (Members): This will contain member details of current loggedin member.

    Raises:
    - IntegrityError: If there is an integrity violation when trying to add the association to the database.
    - Exception: If an unexpected error occurs during the association process.
    """
    try:
        project_id = str(project_id)
        # Remove all old project client association information
        db.query(ClientProjects).filter_by(project_id=project_id).delete()
        for client_id in client_ids:
            # id = generate_uuid()
            created_by = current_member.id
            new_record = ClientProjects(client_id = client_id, project_id = project_id, created_by= created_by)
            db.add(new_record)
            db.flush()
    except IntegrityError as e:
        logger.exception(f"IntegrityError: {e}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise e



async def project_member_association(
    db: Session,
    project_id: str, 
    member_ids: List, 
    role_id: str, 
    current_member: Members, 
    update=False
    ):

    """**Summary:**
    Associates project members with a specific module (e.g., "Estimation") in the database.

    **Parameters:**
    - db: The database session to perform the operation.
    - project_id: The identifier of the project to associate members with.
    - member_id: The identifier(s) of the member(s) to associate with the project.
                It can be a comma-separated string or a list of member IDs.
    - role_id: This will indicate member is associating with which role of the project.
    - current_member (Members): This will contain member details of current loggedin member.

    Raises:
    - IntegrityError: If there is an integrity violation when trying to add the association to the database.
    - Exception: If an unexpected error occurs during the association process.
    """
    try:
        if not update:
            project_id = str(project_id)
            for member_id in member_ids:
                # id = generate_uuid()
                existing_member_role = (
                    db.query(MemberRole).filter(
                        (MemberRole.member_id == member_id) &
                        (MemberRole.role_id == role_id)
                    ).first()
                )
                existing_record = None
                if existing_member_role is not None:
                    existing_record = (
                        db.query(ProjectMembers).filter(
                            (ProjectMembers.member_role_id == existing_member_role.id) &
                            (ProjectMembers.project_id == project_id)
                        ).first()
                    )
                created_by = current_member.id
                if existing_record is None:
                    if existing_member_role is not None:
                        new_record = ProjectMembers(member_role_id = existing_member_role.id, project_id = project_id, created_by= created_by)
                        db.add(new_record)
                        db.flush()
                    else:
                        raise Exception("NOT_AN_ESTIMATOR")
        else:
            # delete existing project menbers/ estimators
            db.query(ProjectMembers).filter(ProjectMembers.project_id == project_id).delete()
            # add estimators to the oroject
            for member_id in member_ids:
                # id = generate_uuid()
                existing_member_role = (
                    db.query(MemberRole).filter(
                        (MemberRole.member_id == member_id) &
                        (MemberRole.role_id == role_id)
                    ).first()
                )
                existing_record = None
                if existing_member_role is not None:
                    existing_record = (
                        db.query(ProjectMembers).filter(
                            (ProjectMembers.member_role_id == existing_member_role.id) &
                            (ProjectMembers.project_id == project_id)
                        ).first()
                    )
                created_by = current_member.id
                if existing_record is None:
                    if existing_member_role is not None:
                        new_record = ProjectMembers(member_role_id = existing_member_role.id, project_id = project_id, created_by= created_by)
                        db.add(new_record)
                        db.flush()
                    else:
                        raise Exception("NOT_AN_ESTIMATOR")
                    
    except IntegrityError as e:
        logger.exception(f"IntegrityError: {e}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise e


async def get_sort_order(sort_by):

    SORT_DICT = {
        'name': "asc", 
        "quotation_due_date": "asc", 
        "priority": "desc", 
        "start_date": "asc", 
        "due_date": "asc",
        "is_estimation": "desc"
        }
    
    sort_by = [field.strip() for field in sort_by[0].split(",")]

    # Validate and construct order_by clauses
    order_by_clauses = []
    for sort_field in sort_by:
        column = getattr(Projects, str(sort_field), None)
        if column:
            # Add to order_by_clauses (default to ascending)
            sort_order = SORT_DICT.get(sort_field, 'asc')
            # Convert string sort_order to actual SQLAlchemy function
            if sort_order == "asc":
                order_by_clauses.append(asc(column))
            elif sort_order == "desc":
                order_by_clauses.append(desc(column))

    return order_by_clauses