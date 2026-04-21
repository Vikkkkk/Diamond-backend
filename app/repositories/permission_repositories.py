"""
This file contains all the database operations related to members.
"""
from typing import List
from loguru import logger
from models.members import Members
from models.role_permissions import RolePermissions
from models.roles import Roles
from models.sub_modules import SubModules
from sqlalchemy.orm import Session
from models.role_permissions import RolePermissions
from fastapi.responses import JSONResponse
from sqlalchemy import or_, and_
from sqlalchemy.dialects import mysql
from schemas.permission_schema import Permission
from sqlalchemy.exc import NoResultFound
import os


def get_role_by_id(db: Session, role_id: str):
    try:
        return db.query(Roles).filter(Roles.id == role_id).one()
    except NoResultFound:
        return None
    

def delete_role_permissions(db: Session, role_id: str):
    try:
        db.query(RolePermissions).filter(RolePermissions.role_id == role_id).delete()
        db.commit()
    except Exception as e:
        logger.exception(f"delete_role_permissions:: An unexpected error occurred: {e}")
        raise


def insert_role_permissions(db: Session, role_id: str, permissions: List[Permission], current_member: Members):
    try:
        for perm in permissions:
            role_permission = RolePermissions(
                role_id=role_id,
                sub_module_id=perm.sub_module_id,
                is_read=perm.is_read,
                is_write=perm.is_write,
                is_delete=perm.is_delete,
                created_by=current_member.id
            )
            db.add(role_permission)
        db.commit()
    except Exception as e:
        logger.exception(f"insert_role_permissions:: An unexpected error occurred: {e}")
        raise


async def get_allowed_roles_by_name(db: Session, role_name: str, sub_module_label: str):
    """
    Retrieves the allowed roles for a specific role and sub-module by their names.

    Args:
        db (Session): SQLAlchemy database session.
        role_name (str): The name of the role to filter by.
        sub_module_label (str): The name of the sub-module to filter by.

    Returns:
        Optional[List[str]]: The list of allowed roles if found, otherwise None.
    """
    print("role_name", role_name)
    print("sub_module_label", sub_module_label)
    result = (
        db.query(RolePermissions.allowed_roles)
        .join(Roles, RolePermissions.role_id == Roles.id)
        .join(SubModules, RolePermissions.sub_module_id == SubModules.id)
        .filter(
            Roles.name == role_name,
            SubModules.label == sub_module_label
        )
    )
    print(">>>>>>>>>>>>>", str(result))
    result = result.first()

    if result:
        return result.allowed_roles
    return None