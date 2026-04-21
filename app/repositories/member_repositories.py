"""
This file contains all the database operations related to members.
"""
from sqlalchemy import func
from loguru import logger
from models.members import Members
from models.member_role import MemberRole
from models.role_permissions import RolePermissions
from models.roles import Roles
from models.modules import Modules
from models.sub_modules import SubModules
from models.projects import Projects
from models.project_members import ProjectMembers
from sqlalchemy.orm import Session
from schemas.member_schema import RoleAssign
import os

async def get_member_name_by_id(db: Session, member_id: str):

    current_member_name = (
            db.query(func.concat(Members.first_name, ' ', Members.last_name).label('name'))
            .filter(Members.id == member_id)
            .first()
        )
    return current_member_name.name


async def get_project_member_permission(db: Session, project_id: str, role_id: str = None):
    """**Summary:**
    This method is responsible for retreaving the member list for a module id within a project

    **Args:**
        - db (Session): db session referance
        - id (String): project Id for which it will return the members.
        - module_id (String): module Id for which it will return the members of a project.

    """
    try:
        project = (
            db.query(Projects)
            .outerjoin(ProjectMembers, (Projects.id == ProjectMembers.project_id))
            .outerjoin(MemberRole, (MemberRole.id == ProjectMembers.member_role_id))
            .outerjoin(Members, ((Members.id == MemberRole.member_id)))
            .outerjoin(Roles, (Roles.id == MemberRole.role_id))
            .outerjoin(RolePermissions, (RolePermissions.role_id == Roles.id))
            .outerjoin(SubModules, (RolePermissions.sub_module_id == SubModules.id))
            .outerjoin(Modules, (SubModules.module_id == Modules.id))
            .filter(
                Projects.id == project_id,
                Projects.is_deleted==False
            )
            .first()
        )
        project_member_data = []
        if project and project.project_members:
            for project_member in project.project_members:
                member_data = {}
                member_role = project_member.project_member_roles
                if member_role:
                    member = member_role.member
                    role = member_role.role
                    if (role_id is None) or (role.id == role_id):
                        member_data = member.to_dict 
                        temp_data = role.to_dict
                        temp_data["permissions"] = []
                        if role and role.role_sub_modules:
                            for role_sub_modules in role.role_sub_modules:
                                sub_module_data = role_sub_modules.sub_module.to_dict
                                sub_module_data["is_read"] = role_sub_modules.is_read
                                sub_module_data["is_write"] = role_sub_modules.is_write
                                sub_module_data["is_delete"] = role_sub_modules.is_delete
                                module_data = role_sub_modules.sub_module.module.to_dict
                                filterred_modules = [obj for (indx, obj) in enumerate(temp_data["permissions"]) if obj["id"] == module_data["id"]]
                                if len(filterred_modules) == 0:
                                    module_data["sub_modules"] = [sub_module_data]
                                    temp_data["permissions"].append(module_data)
                                else:
                                    filterred_sub_modules = [obj for (indx, obj) in enumerate(filterred_modules[0]["sub_modules"]) if obj["id"] == sub_module_data["id"]]
                                    
                                    if len(filterred_sub_modules) == 0:
                                        filterred_modules[0]["sub_modules"].append(sub_module_data)
                        member_data["role_permission"] = temp_data
                        
                        filterred_members = [obj for (indx, obj) in enumerate(project_member_data) if obj["id"] == member_data["id"]]
                        if len(filterred_members) == 0:
                            member_data["role"] = role.to_dict
                            project_member_data.append(member_data)
                        else:
                            filterred_members[0]["role"].append(role.to_dict)
                        project_member_data.append(member_data)
        return project_member_data
    except Exception as e:
        logger.exception("get_project_member_permission:: error - " + str(e))
        raise e
        

async def get_project_members(db, project_id, role_id = None):
    """**Summary:**
    This method is responsible for retreaving the member list for a module id within a project

    **Args:**
        - db (Session): db session referance
        - id (String): project Id for which it will return the members.
        - module_id (String): module Id for which it will return the members of a project.

    """
    try:
        project = (
            db.query(Projects)
            .outerjoin(ProjectMembers, (Projects.id == ProjectMembers.project_id))
            .outerjoin(MemberRole, (MemberRole.id == ProjectMembers.member_role_id))
            .outerjoin(Members, ((Members.id == MemberRole.member_id)))
            .outerjoin(Roles, (Roles.id == MemberRole.role_id))
            .filter(
                Projects.id == project_id,
                Projects.is_deleted==False
            )
            .first()
        )
        project_member_data = []
        if project and project.project_members:
            for project_member in project.project_members:
                member_data = {}
                member_role = project_member.project_member_roles
                if member_role:
                    member = member_role.member
                    role = member_role.role
                    if (role_id is None) or (role.id == role_id):
                        member_data = member.to_dict 
                        filterred_members = [obj for (indx, obj) in enumerate(project_member_data) if obj["id"] == member_data["id"]]
                        if len(filterred_members) == 0:
                            member_data["roles"] = [role.to_dict]
                            project_member_data.append(member_data)
                        else:
                            filterred_members[0]["roles"].append(role.to_dict)
        return project_member_data
    except Exception as e:
        logger.exception("get_project_members:: error - " + str(e))
        raise e
        

async def get_member_project_permission(db, member_id, project_id):
    """**Summary:**
    Retrieves the project permissions for a given member in a specific project.

    Args:
        db (Session): The database session.
        member_id (int): The ID of the member.
        project_id (int): The ID of the project.

    Returns:
        list: A list of dictionaries containing the module and submodule data for the member's project permissions.

    """
    try:
        data = []
        member_roles = db.query(MemberRole.id).filter(MemberRole.member_id == member_id).all()
        member_roles = [member_role_id[0] for member_role_id in member_roles]
        member_project_permission_data = (
            db.query(ProjectMembers)
            .outerjoin(MemberRole, Members.id == MemberRole.member_id)
            .outerjoin(Roles, Roles.id == MemberRole.role_id)
            .outerjoin(RolePermissions, RolePermissions.role_id == MemberRole.role_id)
            .outerjoin(SubModules, RolePermissions.sub_module_id == SubModules.id)
            .outerjoin(Modules, (Modules.id == SubModules.module_id)& (Modules.is_active == True))
            .filter(
                ProjectMembers.project_id == project_id,
                ProjectMembers.member_role_id.in_(member_roles)
            )
            .order_by(Modules.sort_order.asc(), SubModules.sort_order.asc())
            .all()
        )
        if len(member_project_permission_data):
            for member_role in member_project_permission_data.project_member_roles:
                for role_sub_module in member_role.role.role_sub_modules:
                    sub_module_data = role_sub_module.sub_module.to_dict
                    sub_module_data["is_read"] = role_sub_module.is_read
                    sub_module_data["is_write"] = role_sub_module.is_write
                    sub_module_data["is_delete"] = role_sub_module.is_delete
                    module_data = role_sub_module.sub_module.module.to_dict
                    filterred_modules = [obj for (indx, obj) in enumerate(data) if obj["id"] == module_data["id"]]
                    if len(filterred_modules) == 0:
                        module_data["sub_modules"] = [sub_module_data]
                        data.append(module_data)
                    else:
                        filterred_sub_modules = [obj for (indx, obj) in enumerate(filterred_modules[0]["sub_modules"]) if obj["id"] == sub_module_data["id"]]
                        
                        if len(filterred_sub_modules) == 0:
                            filterred_modules[0]["sub_modules"].append(sub_module_data)
        return data
    except Exception as error:
        logger.exception("get_member_project_permission:: error - " + str(error))


        
async def get_member_permission(db, member_id):
    """**Summary:**
    Asynchronously retrieves the permissions for a given member from the database.

    Args:
    - db (Session): The database session object.
    - member_id (int): The ID of the member.

    Returns:
    - list: A list of dictionaries representing the permissions for the member. Each dictionary contains the following keys:
        - "id" (int): The ID of the permission.
        - "name" (str): The name of the permission.
        - "sub_modules" (list): A list of dictionaries representing the sub-modules associated with the permission. Each sub-module dictionary contains the following keys:
            - "id" (int): The ID of the sub-module.
            - "name" (str): The name of the sub-module.
            - "is_read" (bool): Indicates whether the member has read access to the sub-module.
            - "is_write" (bool): Indicates whether the member has write access to the sub-module.
            - "is_delete" (bool): Indicates whether the member has delete access to the sub-module.
    """
    try:
        data = []
        member_roles = db.query(MemberRole.id).filter(MemberRole.member_id == member_id).all()
        member_roles = [member_role_id[0] for member_role_id in member_roles]
        member_permission_data = (
            db.query(MemberRole)
            .outerjoin(Roles, Roles.id == MemberRole.role_id)
            .outerjoin(RolePermissions, RolePermissions.role_id == MemberRole.role_id)
            .outerjoin(SubModules, RolePermissions.sub_module_id == SubModules.id)
            .outerjoin(Modules, (Modules.id == SubModules.module_id)& (Modules.is_active == True))
            .filter(
                MemberRole.member_id == member_id
            )
            .order_by(Modules.sort_order.asc(), SubModules.sort_order.asc())
            .all()
        )
        if len(member_permission_data):
            for member_role in member_permission_data:
                for role_sub_module in member_role.role.role_sub_modules:
                    sub_module_data = role_sub_module.sub_module.to_dict
                    sub_module_data["is_read"] = role_sub_module.is_read
                    sub_module_data["is_write"] = role_sub_module.is_write
                    sub_module_data["is_delete"] = role_sub_module.is_delete
                    module_data = role_sub_module.sub_module.module.to_dict
                    filterred_modules = [obj for (indx, obj) in enumerate(data) if obj["id"] == module_data["id"]]
                    if len(filterred_modules) == 0:
                        module_data["sub_modules"] = [sub_module_data]
                        data.append(module_data)
                    else:
                        filterred_sub_modules = [obj for (indx, obj) in enumerate(filterred_modules[0]["sub_modules"]) if obj["id"] == sub_module_data["id"]]
                        
                        if len(filterred_sub_modules) == 0:
                            filterred_modules[0]["sub_modules"].append(sub_module_data)
        return data
    except Exception as error:
        logger.exception("get_member_permission:: error - " + str(error))

        
        
async def get_member_projects(db, member_id):
    """**Summary:**
    Asynchronously retrieves all projects associated with a given member.

    Args:
    - db (Session): The database session object.
    - member_id (int): The ID of the member for whom to retrieve projects.

    Returns:
    - list: A list of dictionaries representing projects associated with the member.
    """
    try:
        data = []
        member_roles = db.query(MemberRole.id).filter(MemberRole.member_id == member_id).all()
        member_roles = [member_role_id[0] for member_role_id in member_roles]
        # Query to get all unique project IDs filtered by the specific member_role_id
        unique_projects = (
            db.query(ProjectMembers.project_id)
            .filter(ProjectMembers.member_role_id.in_(member_roles))
            .distinct()
            .all()
        )
        project_ids = [project_id[0] for project_id in unique_projects]
        data = db.query(Projects).filter(Projects.id.in_(project_ids)).all()
        data = [project.to_dict for project in data]
        return data
    except Exception as error:
        logger.exception("get_member_projects:: error - " + str(error))


async def get_member_details(db, id):
    """**Summary:**
    This method is responsible for retreaving the details of the input member id

    **Args:**
        - db (Session): db session referance
        - id (String): member Id for which it will run the fetch member details

    **Returns:**
        list: A list containing the member details.
    """
    try:
        data = []
        member_permission_data = (
            db.query(Members)
            .join(MemberRole, Members.id == MemberRole.member_id)
            .join(Roles, Roles.id == MemberRole.role_id)
            .filter(
                Members.is_deleted == False,
                Members.id == id
            )
        ).first()

        member_roles_data = (
            db.query(
                Roles.id.label('role_id'),
                Roles.name.label('role_name'),
                MemberRole.active_role
            )
            .join(MemberRole, MemberRole.role_id == Roles.id)
            .join(Members, Members.id == MemberRole.member_id)
            .filter(
                Members.is_deleted == False,
                Members.id == id
            )
            .order_by(MemberRole.active_role.desc())
        ).all()

        role_data = [
            {
                "id": role.role_id,
                "name": role.role_name,
                "active_role": role.active_role
            }
            for role in member_roles_data
        ]

        if member_permission_data:
            member_data = member_permission_data.to_dict
            member_data["projects"] = await get_member_projects(db, id)
            member_data["roles"] = role_data
            member_data["tax"] = os.getenv('TAX')
            member_data["tax_type"] = os.getenv('TAX_TYPE')
            member_data["margin_threshold"] = os.getenv("MARGIN_THRESHOLD")
            
            data = [member_data]
        return data
    except Exception as error:
        logger.exception("get_member_details:: error - " + str(error))
        raise error


def get_role_project_involvement(db: Session, member_id: str, role_ids: RoleAssign):
    """
    This function checks the roles of a member and determines if there are any roles that should 
    be deleted or created based on the given role_ids. It also checks if any roles that are to be 
    deleted are involved in any projects.
    """
    # Query existing roles for the given member and role_ids
    existing_roles = db.query(MemberRole).filter(MemberRole.member_id == member_id).all()

    # Convert the ids to a set
    existing_role_ids = {member_role.role_id for member_role in existing_roles}
    given_role_ids = set(role_ids)

    deleted_role_ids = list(existing_role_ids - given_role_ids)
    created_role_ids = list(given_role_ids - existing_role_ids)

    flag = False
    role = ""

    # Iterate over the existing roles to check project involvement
    for role_id in deleted_role_ids:
        member_role_data = db.query(MemberRole).filter(MemberRole.member_id == member_id, MemberRole.role_id == role_id).first()
        project_member_count = db.query(ProjectMembers).filter(ProjectMembers.member_role_id == member_role_data.id).count()

        if project_member_count > 0:
            role_data = db.query(Roles.name).join(MemberRole).filter(MemberRole.id == member_role_data.id).first()
            flag = True
            role = role_data.name
            break

    response = {
        'flag': flag,
        'role': role,
        'deleted_ids': deleted_role_ids,
        'created_ids': created_role_ids
    }

    return response



async def get_role_by_id(db: Session, member_id: str, active_role=None):

    member_roles_data = (
                db.query(
                    Roles.id.label('role_id'),
                    Roles.name.label('role_name'),
                    MemberRole.active_role
                )
                .join(MemberRole, MemberRole.role_id == Roles.id)
                .join(Members, Members.id == MemberRole.member_id)
                .filter(
                    Members.is_deleted == False,
                    Members.id == member_id
                )
            )
    
    if active_role:
        member_roles_data = member_roles_data.filter(MemberRole.active_role == True)
    
    member_roles_data = member_roles_data.order_by(MemberRole.active_role.desc()).all()

    role_data = [
        {
            "id": role.role_id,
            "name": role.role_name,
            "active_role": role.active_role
        }
        for role in member_roles_data
    ]
    
    return role_data


async def get_role_names_by_ids(role_ids: list, db: Session):
    # Query to fetch role names where role_id is in the provided list
    roles = db.query(Roles.name).filter(Roles.id.in_(role_ids)).all()
    # Extract names from the result tuples
    role_names = [role.name for role in roles]
    return role_names