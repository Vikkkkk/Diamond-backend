"""
This module containes all logical operation and db operations those are related to permissions add/update/read/delete.
"""
from typing import List
from loguru import logger
from sqlalchemy.exc import IntegrityError
from models.members import Members
from models.modules import Modules
from models.sub_modules import SubModules
from models.member_role import MemberRole
from models.roles import Roles
from models.role_permissions import RolePermissions
from fastapi.responses import JSONResponse
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from repositories.permission_repositories import get_role_by_id, delete_role_permissions, insert_role_permissions


async def get_member_role_permission(db: Session, member_id: str, role_id: str):
    """**Summary:**
    This method is responsible for retreaving the permission details of the input member id

    **Args:**
    - `db` (Session): db session referance
    - `member_id` (String): member Id for which it will run the fetch query
    - `role_id` (String): role Id for which it will run the fetch query.

    """
    try:
        permission_data = {}
        # print("role_id:: ",role_id)
        member_permission_data = (
            db.query(Members, MemberRole)
            .outerjoin(MemberRole, and_(Members.id == MemberRole.member_id, MemberRole.role_id == role_id))
            .outerjoin(Roles, MemberRole.role_id == Roles.id)
            .outerjoin(RolePermissions, RolePermissions.role_id == MemberRole.role_id)
            .outerjoin(SubModules, RolePermissions.sub_module_id == SubModules.id)
            .outerjoin(Modules, and_(Modules.id == SubModules.module_id, Modules.is_active == True))
            .filter(
                Members.is_deleted == False,
                Members.id == member_id,
            )
            .order_by(Modules.sort_order.asc(), SubModules.sort_order.asc())
            .first()
        )
        member_role = member_permission_data[1]
        member_permission_data = member_permission_data[0]
        # from pprint import pprint
        if member_permission_data:
            member_data = member_permission_data.to_dict
            # print(member_data)
            member_data["permissions"] = []
            member_data["roles"] = []
            if member_role.role:
                member_data["roles"].append(member_role.role.to_dict)
            for role_sub_module in member_role.role.role_sub_modules:
                sub_module_data = role_sub_module.sub_module.to_dict
                # sub_module_data["sort_order"] = sub_module_data.sort_order
                sub_module_data["is_read"] = role_sub_module.is_read
                sub_module_data["is_write"] = role_sub_module.is_write
                sub_module_data["is_delete"] = role_sub_module.is_delete
                sub_module_data["allowed_roles"] = role_sub_module.allowed_roles
                # print(sub_module_data)

                module_data = role_sub_module.sub_module.module.to_dict
                filterred_modules = [obj for (indx, obj) in enumerate(member_data["permissions"]) if obj["id"] == module_data["id"]]
                if len(filterred_modules) == 0:
                    module_data["sub_modules"] = [sub_module_data]
                    member_data["permissions"].append(module_data)
                else:
                    filterred_sub_modules = [obj for (indx, obj) in enumerate(filterred_modules[0]["sub_modules"]) if obj["id"] == sub_module_data["id"]]
                    if len(filterred_sub_modules) == 0:
                        filterred_modules[0]["sub_modules"].append(sub_module_data)
            permission_data = member_data
            # pprint(permission_data)
        return  {"data": permission_data, "status": "success"}
    except Exception as error:
        logger.exception("get_member_role_permission:: error - " + str(error))
        raise error
    


def create_permissions(role_permissions: RolePermissions, current_member: Members, db: Session):
    """**Summary:**
    This method is responsible for creating the role permissions
    """
    try:
        # Check if the role_id exists in the roles table
        role = get_role_by_id(db, role_permissions.role_id)
        if not role:
            return JSONResponse(content={"message": "Role ID not found."}, status_code=404)
        
        # Check if sub_module_id is valid
        for perm in role_permissions.permission:
            sub_module = db.query(SubModules).filter(SubModules.id == perm.sub_module_id).first()
            if not sub_module:
                raise JSONResponse(content=f"Sub Module ID {perm.sub_module_id} not found", status_code=404)

        # Check if there is already a record with the role_id in the role_permissions table
        existing_permissions = db.query(RolePermissions).filter(RolePermissions.role_id == role_permissions.role_id).all()
        if existing_permissions:
            # Delete the existing data for that particular role_id
            delete_role_permissions(db, role_permissions.role_id)

        # Insert the new list of submodule data for that particular role
        insert_role_permissions(db, role_permissions.role_id, role_permissions.permission, current_member)

        return {"status": "success", "role_id": role_permissions.role_id}
    except Exception as error:
        logger.exception("get_member_role_permission:: error - " + str(error))
        raise error