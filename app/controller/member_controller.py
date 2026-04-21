"""
This module containes all logical operation and db operations those are related to members add/update/read/delete.
"""
from datetime import datetime
from utils.common import get_user_time
from utils.auth import hash_password
from loguru import logger
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from models.members import Members
from models.member_role import MemberRole
from models.role_permissions import RolePermissions
from models.roles import Roles
from models.member_role import MemberRole
from models.modules import Modules
from models.sub_modules import SubModules
from models.projects import Projects
from models.project_members import ProjectMembers
from models.clients import Clients
from models.client_projects import ClientProjects
from repositories.member_repositories import get_member_details, get_member_projects, get_member_permission, get_member_project_permission, get_role_project_involvement, get_role_by_id, get_role_names_by_ids
from repositories.permission_repositories import get_allowed_roles_by_name
from schemas.member_schema import ProfileSwitchRequest
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status
import math
from sqlalchemy import cast, or_, null
from sqlalchemy.types import String
from dotenv import load_dotenv
from schemas.member_schema import Member, MemberResponse, MembersResponse, ChangePasswordRequest, ProfileSwitchRequest, RoleAssign

load_dotenv()


async def get_members(db: Session, page: int, page_size: int, keyword: str, role_id: str):
    """
    Retrieve a paginated list of members with optional keyword and role filtering.

    Args:
        db (Session): Database session.
        page (int): Page number.
        page_size (int): Number of items per page.
        keyword (str): Search keyword for first name, last name, or email.
        role_id (str): Role ID to filter members by specific role.

    Returns:
        dict: A dictionary containing paginated member data and metadata.
    """
    try:
        if page_size:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = db.query(Members).filter(Members.is_deleted == False).count()
            page = 1

        # Build base subquery for member IDs
        subquery = db.query(cast(Members.id, String)).filter(Members.is_deleted == False)

        if keyword:
            subquery = subquery.filter(
                or_(
                    Members.first_name.ilike(f'%{keyword}%'),
                    Members.last_name.ilike(f'%{keyword}%'),
                    Members.email.ilike(f'%{keyword}%')
                )
            )

        if role_id:
            subquery = subquery.join(MemberRole, Members.id == MemberRole.member_id)\
                               .filter(MemberRole.role_id == role_id)

        subquery_result = subquery.order_by(Members.created_at.asc()).offset(skip).limit(limit).all()

        member_ids = [str(row[0]) for row in subquery_result]

        if page_size is None:
            page_size = len(member_ids)

        if keyword or role_id:
            item_count = len(member_ids)
        else:
            item_count = db.query(Members).filter(Members.is_deleted == False).count()

        # Main query to fetch full member data
        member_items = (
            db.query(Members)
            .outerjoin(MemberRole, Members.id == MemberRole.member_id)
            .outerjoin(Roles, Roles.id == MemberRole.role_id)
            .outerjoin(RolePermissions, RolePermissions.role_id == MemberRole.role_id)
            .outerjoin(SubModules, RolePermissions.sub_module_id == SubModules.id)
            .outerjoin(Modules, Modules.id == SubModules.module_id)
            .outerjoin(ProjectMembers, MemberRole.id == ProjectMembers.member_role_id)
            .outerjoin(
                Projects,
                (Projects.id == ProjectMembers.project_id) &
                (Projects.is_deleted == False) &
                (Projects.is_active == True)
            )
            .filter(
                Members.is_deleted == False,
                Members.id.in_(member_ids)
            )
            .order_by(Members.created_at.asc(), Modules.sort_order.asc(), SubModules.sort_order.asc())
            .all()
        )

        # Build response
        member_data = []
        for member in member_items:
            temp = member.to_dict
            temp['name'] = f"{temp['first_name']} {temp['last_name']}"
            temp["permissions"] = []

            for member_role in member.member_roles:
                for role_sub_module in member_role.role.role_sub_modules:
                    sub_module_data = role_sub_module.sub_module.to_dict
                    sub_module_data["is_read"] = role_sub_module.is_read
                    sub_module_data["is_write"] = role_sub_module.is_write
                    sub_module_data["is_delete"] = role_sub_module.is_delete

                    module_data = role_sub_module.sub_module.module.to_dict
                    existing_module = next((m for m in temp["permissions"] if m["id"] == module_data["id"]), None)

                    if existing_module:
                        if all(sm["id"] != sub_module_data["id"] for sm in existing_module["sub_modules"]):
                            existing_module["sub_modules"].append(sub_module_data)
                    else:
                        module_data["sub_modules"] = [sub_module_data]
                        temp["permissions"].append(module_data)

            member_data.append(temp)

        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0
        item_count = item_count if page_count > 0 else 0

        return {
            "data": member_data,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

    except Exception as error:
        logger.exception("get_members:: error - " + str(error))
        raise error

    

async def get_member(db: Session, id: str):
    """**Summary:**
    This method is responsible for retreaving the details of the input member id

    **Args:**
        - db (Session): db session referance
        - id (String): member Id for which it will run the fetch query

    """
    try:
        data = await get_member_details(db, id)
        return  {"data": data, "status": "success"}
    except Exception as error:
        logger.exception("get_member:: error - " + str(error))
        raise error
        

async def get_me_data(db: Session, current_member: Members):
    """**Summary:**
    This method is responsible for retreaving the details of the current member

    **Args:**
        - db (Session): db session referance
        - current_member (dict): it will contain all informations of current member.

    """
    try:
        data = await get_member_details(db, current_member.id)
        return  {"data": data, "status": "success"}
    except Exception as error:
        logger.exception("get_me_data:: error - " + str(error))
        raise error
        

async def create_member(data: Member, db:Session, current_member: Members):
    """**Summary:**
    This method takes single member data as input, it check if the member is already exists or not,
    depending on its email. If not exists then add the member to the DB

    **Args:**
        - data (Member): Member data. reffer to the member schema for the structure
        - db (Session): db session referance
        - current_member (Members): This will contain member details of current loggedin member.
    """
    member_data = data.dict()
    # Check if the same data already exists in the table
    if not db.query(Members).filter(Members.email==member_data["email"]).first():
        try:
            # member_id = generate_uuid()
            # member_data['id'] = member_id
            member_data['created_by'] = current_member.id
            member_data['password'] = hash_password(member_data['password'])
            new_member = Members(**member_data)
            db.add(new_member)
            db.commit()
            member_id = new_member.id
            return {"id": member_id, "message": "Member Data inserted successfully."}
        except IntegrityError as i_error:
            logger.exception(f"IntegrityError: {i_error}")
            db.rollback()
            raise i_error
        except Exception as error:
            logger.exception(f"An unexpected error occurred: {error}")
            db.rollback()
            raise error
    else:
        return JSONResponse(content={"message": "Member with the given email already exists."}, status_code=400)



async def assign_role(
    member_id: str, 
    roleIds: RoleAssign, 
    db: Session, 
    current_member: Members
    ):
    """**Summary:**
    This method takes single member data as input, it check if the member is already exists or not,
    depending on its email. If not exists then add the member to the DB

    **Args:**
        - data (Member): Member data. reffer to the member schema for the structure
        - db (Session): db session referance
        - current_member (Members): This will contain member details of current loggedin member.
    """
   
    member_role_ids = []

    try:
        with db.begin():
            
            role_names = await get_role_names_by_ids(roleIds, db)

            current_role_obj = db.query(Roles).join(MemberRole).filter(
                MemberRole.member_id == current_member.id,
                MemberRole.active_role == True
            ).first()
            current_role_name = current_role_obj.name
            current_role_id = current_role_obj.id

            current_member_list_role_permission = (db.query(RolePermissions).join(SubModules).
             filter(RolePermissions.role_id == current_role_id, SubModules.name == "Member List").first())
            allowed_roles = current_member_list_role_permission.allowed_roles

            for role in role_names:
                if role not in allowed_roles:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"message": f"You don't have permission to assign {role}"}
                    )

            role_project_involvement = get_role_project_involvement(db, member_id, roleIds)

            if role_project_involvement['flag']:
                raise Exception(f"Role {role_project_involvement['role']} cannot be removed as the member is already associated with a project.")

            if role_project_involvement['deleted_ids']:
                db.query(MemberRole).filter(MemberRole.member_id == member_id, MemberRole.role_id.in_(role_project_involvement['deleted_ids'])).delete(synchronize_session=False)
                db.flush()

            if role_project_involvement['created_ids']:
                for role_id in role_project_involvement['created_ids']:
                    new_member_role_data = MemberRole(
                        role_id=role_id,
                        member_id=member_id,
                        created_by=current_member.id
                    )
                    db.add(new_member_role_data)
                    db.flush()
                    member_role_ids.append(new_member_role_data.id)
            active_member_role = db.query(MemberRole).filter(MemberRole.member_id == member_id, MemberRole.active_role == True).first()
            if not active_member_role:
                rand_role_id = roleIds[0]
                db.query(MemberRole).filter(MemberRole.role_id == rand_role_id, MemberRole.member_id == member_id).update({"active_role": True})

        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    return member_role_ids



async def delete_member_soft(db: Session, id: str, current_member: Members):
    """
    Soft delete a member by updating the is_deleted flag.
    Args:
        db (Session): DB session reference.
        id (int): The unique identifier of the member to be soft deleted.
        current_member (Members): This will contain member details of current loggedin member.
    """
    member_exist = db.query(Members).filter(Members.id == id, Members.is_deleted == False).first()
    if member_exist:
        member = db.query(Members).get(id)
        member.is_deleted = True
        member.deleted_at = datetime.now()
        member.deleted_by = current_member.id
        db.commit()
        return {"message": "Data deleted successfully.", "status": "success"}
    else:
        return JSONResponse(content={"message": "member not found"}, status_code=400)
    


async def update_member(db: Session, id: str, member_data: Member, current_member: Members):
    """**Summary:**
    This method updates member data based on the provided member ID.

    **Args:**
        - db (Session): db session reference
        - id (int): ID of the member to be updated
        - member_data (Members): Updated member data. Refer to the Member schema for the structure
        - current_member (Members): This will contain member details of current loggedin member.
    """
    try:
        existing_member = db.query(Members).filter(Members.id == id, Members.is_deleted == False).first()
        if existing_member:
            member_data = member_data.model_dump(exclude_unset=True)
            if 'email' in member_data:
                duplicate_member = (
                    db.query(Members).filter(
                        Members.email == member_data['email'], 
                        Members.phone == member_data['phone'],
                        Members.id != id, 
                        Members.is_deleted == False
                        ).first()
                    )
                if duplicate_member:
                    return JSONResponse(content={"message": "Member with the given email or phone number already exists."}, status_code=400)
                
            if 'password' in member_data:
                member_data['password'] = hash_password(member_data['password'])
            # Update existing member data
            member_data['updated_by'] = current_member.id
            # Update the attributes of the existing member with the values from the member_data dictionary.
            for key, value in member_data.items():
                setattr(existing_member, key, value)
            db.commit()
            return {"message": f"Member with ID {id} updated successfully.", "status": "success"}
        else:
            return JSONResponse(content={"message": f"Member not found."}, status_code=400)

    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    

async def change_password(db: Session, id: str, request_data: ChangePasswordRequest, current_member: Members):
    """**Summary:**
    Update password for member.

    Parameters:
    - id (str): The unique identifier of the member whose password is to be changed.
    - request_data (ChangePasswordRequest): The request data containing the new password and confirm password.
    - current_member (Members): The currently authenticated member obtained from the token.
    - db (Session): The database session.

    Returns:
    - JSONResponse: A JSON response indicating the success of the password change.
    """
    try:
        request_data = request_data.dict()
        existing_member = db.query(Members).filter(Members.id == id, Members.is_deleted == False).first()
        if not existing_member:
            return JSONResponse(content={"message": "Member doesn’t exist."}, status_code=400)
        
        if request_data['password'] != request_data['confirm_password']:
            return JSONResponse(content={"message": "Password and confirm password do not match."}, status_code=422)
        
        existing_member.password = hash_password(request_data['password'])
        existing_member.updated_by = current_member.id

        db.commit()
        return {"message": "Member password updated successfully.", "status": "success"}
    
    except IntegrityError as i_error:
        logger.exception(f"IntegrityError: {i_error}")
        db.rollback()
        raise i_error
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        db.rollback()
        raise error
    

async def get_assigned_projects(db: Session, member_id: int, page: int = None, page_size: int = None, keyword: str = None):
    """Retrieve a paginated list of projects assigned to a specific member."""
    try:
        # Set default values for page and page_size if they are None
        if page is None:
            page = 1
        if page_size is None:
            page_size = 10  # or any default value

        # Calculate pagination limits
        skip = (page - 1) * page_size

        # Base query for filtering projects assigned to the member
        base_query = db.query(Projects).join(ProjectMembers, Projects.id == ProjectMembers.project_id).join(MemberRole, MemberRole.id == ProjectMembers.member_role_id).filter(
            MemberRole.member_id == member_id, Projects.is_deleted == False
        )

        # Apply keyword filtering if provided
        if keyword:
            base_query = base_query.filter(
                or_(Projects.name.ilike(f'%{keyword}%'), Projects.project_code.ilike(f'%{keyword}%'))
            )

        # Get the total count of items
        item_count = base_query.count()

        # Retrieve the paginated list of projects
        project_assignments = base_query.order_by(Projects.created_at.asc()).offset(skip).limit(page_size).all()

        # Process each project assignment and retrieve associated clients
        data = []
        for project in project_assignments:
            project_dict = project.to_dict
            project_dict['client'] = [
                client_project.client.to_dict for client_project in db.query(ClientProjects).join(Clients).filter(
                    ClientProjects.project_id == project.id, Clients.is_deleted == False
                ).all() if client_project.client
            ]
            data.append(project_dict)

        # Calculate the total number of pages
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        # Prepare the response dictionary
        response = {
            "data": data,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }
        return response

    except SQLAlchemyError as error:
        logger.exception(f"Database error: {error}")
        return JSONResponse(content={"message": "An error occurred while retrieving the projects.", "status": "error"}, status_code=500)
    
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        return JSONResponse(content={"message": "An unexpected error occurred.", "status": "error"}, status_code=500)



async def get_role_members(db: Session, role_id: str, page_size: int, keyword: str):
    """**Summary:**
    Retrieve role members with optional filtering and pagination.

    Parameters:
    - `db` (Session): The database session.
    - `role_id` (str): The ID of the module for which to retrieve members.
    """
    try:
        items = (
            db.query(Members)
            .join(MemberRole)
            .group_by(MemberRole.member_id)
            .filter(
                Members.is_deleted == False, 
                MemberRole.role_id == role_id
            )
        )
        if keyword:
            items = items.filter(or_(
                Members.first_name.ilike(f'%{keyword}%'),
                Members.last_name.ilike(f'%{keyword}%')
            ))
        items = items.order_by(Members.created_at.asc()).limit(page_size).all()
        
        response_data = []
        for item in items:
            data = {}
            data['id'] = item.id
            data['name'] = f"{item.first_name} {item.last_name}"
            data['first_name'] = item.first_name
            data['last_name'] = item.last_name
            response_data.append(data)

        response = {"data": response_data, "status": "success"}
        return response
    
    except Exception as e:
        logger.exception("get_role_members:: error - " + str(e))
        raise e
    



async def get_member_detailed_list(db: Session, page: int, page_size: int, keyword: str, current_member: Members):
    """**Summary:**
    Retrieve role members with optional filtering and pagination.

    Parameters:
    - `db` (Session): The database session.
    - `page` (int, optional): The page number for pagination (default: None).
    - `page_size` (int, optional): The number of items per page for pagination (default: None).
    - `keyword` (str, optional): A keyword to filter members (default: None).
    - `current_member` (Member, dependency): Dependency to verify the user's token and return the current member.
    """
    try:
        role_details = await get_role_by_id(db, member_id = current_member.id, active_role = True)
        allowed_roles = await get_allowed_roles_by_name(db, role_name = role_details[0]['name'], sub_module_label = "Member List")

        if allowed_roles:

            if page_size is not None:
                skip = (page - 1) * page_size
                limit = page_size
            else:
                skip = 0
                items = (
                db.query(Members)
                .outerjoin(MemberRole, Members.id == MemberRole.member_id)  # LEFT JOIN
                .outerjoin(Roles, MemberRole.role_id == Roles.id)  # LEFT JOIN
                .group_by(Members.id)  # Grouping by Members.id instead of MemberRole.member_id
                .filter(
                    Members.is_deleted == False,
                    or_(Roles.name.in_(allowed_roles), Roles.id == None)  # Include members with no roles
                ).count()
            )

            items = (
                db.query(Members)
                .outerjoin(MemberRole, Members.id == MemberRole.member_id)  # LEFT JOIN
                .outerjoin(Roles, MemberRole.role_id == Roles.id)  # LEFT JOIN
                .group_by(Members.id)  # Grouping by Members.id instead of MemberRole.member_id
                .filter(
                    Members.is_deleted == False,
                    or_(Roles.name.in_(allowed_roles), Roles.id == None)  # Include members with no roles
                )
            )

            if keyword:
                items = items.filter(or_(
                    Members.first_name.ilike(f'%{keyword}%'),
                    Members.last_name.ilike(f'%{keyword}%')
                ))

            items = items.order_by(Members.created_at.asc()).offset(skip).limit(limit).all()

            response_data = []
            for item in items:
                data = {}
                data['id'] = item.id
                data['first_name'] = item.first_name
                data['last_name'] = item.last_name
                data['name'] = f"{item.first_name} {item.last_name}"
                data['email'] = item.email
                data['phone'] = item.phone
                data['is_super_admin'] = item.is_super_admin
                data['is_active'] = item.is_active
                data['last_login'] = item.last_login
                roles = []
                for member_role in item.member_roles:
                    if member_role.role.name not in roles:
                        roles.append({'id':member_role.role.id, 'name':member_role.role.name})

                projects = []
                project_ids = []
                for member_role in item.member_roles:
                    for project_member in member_role.project_members:
                        project = project_member.project
                        if project.id not in project_ids:
                            projects.append({'id':project.id,'name':project.name})
                            project_ids.append(project.id)

                data['roles'] = roles
                data['projects'] = projects
                response_data.append(data)

            if page_size is None:
                page_size = len(items)
            if keyword is None:
                item_count = (
                    db.query(Members)
                    .outerjoin(MemberRole, Members.id == MemberRole.member_id)  # LEFT JOIN
                    .outerjoin(Roles, MemberRole.role_id == Roles.id)  # LEFT JOIN
                    .group_by(Members.id)  # Grouping by Members.id instead of MemberRole.member_id
                    .filter(
                        Members.is_deleted == False,
                        or_(Roles.name.in_(allowed_roles), Roles.id == None)  # Include members with no roles
                    ).count()
                )

            else:
                item_count = len(items)

            page_count = math.ceil(item_count/limit) if page_size > 0 else 0
            item_count = item_count if page_count > 0 else 0
            response = {"data": response_data, "page_count": page_count, "item_count": item_count, "status": "success"}
        else:
            response = response = {"data": [], "page_count": 0, "item_count": 0, "status": "success"}

        return response
    
    except Exception as e:
        logger.exception("get_member_detailed_list:: error - " + str(e))
        raise e
    
    

async def switch_profile(db: Session, request_data: ProfileSwitchRequest, current_member: Members):
    try:
        # Fetch the new role
        request_data = dict(request_data)
        member_role = db.query(MemberRole).filter(MemberRole.member_id == current_member.id, \
                                            MemberRole.role_id == request_data['role_id']).first()
        if not member_role:
            return JSONResponse(content={"message": "Role not found"}, status_code=404)
        
        # Set all roles for the member to inactive
        db.query(MemberRole).filter(MemberRole.member_id == current_member.id).update({"active_role": False})
        
        # Perform the profile switch
        member_role.active_role = True
        db.commit()

        return {"message": "Profile switched successfully.", "status": "success"}
    
    except Exception as e:
        logger.exception("switch_profile:: error - " + str(e))
        raise e