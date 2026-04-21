"""
This module containes all routes those are related to permissions add/update/read/delete.
"""
from typing import List
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status as starlette_status
from models import get_db
from models.members import Members
from schemas.permission_schema import Permission, RolePermissions, PermissionsRequest, MemberPermissionResponse, ModuleMemberResponse
from controller import permission_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required

router = APIRouter(prefix="/permission", tags=["Permission APIs"])


@router.get("/get_member_role_permission/{member_id}", response_model=MemberPermissionResponse, status_code=starlette_status.HTTP_200_OK)
@logger.catch 
async def get_member_role_permission(
    member_id: str,
    role_id: str = Query(description="role id of the member"),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving the permission details of the input member id

    **Args:**
    - `db` (Session): db session referance.
    - `member_id` (String): member Id for which it will run the fetch query.
    - `role_id` (String): role Id for which it will run the fetch query.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not

    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await permission_controller.get_member_role_permission(db, member_id, role_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/create_permissions", status_code=starlette_status.HTTP_200_OK)
async def create_permissions(
    role_permissions: RolePermissions,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
    ):
    """**Summary:**
    Create permissions for a given role.

    This endpoint allows you to create or update permissions for a specific role.
    It performs the following operations:
    - Checks if the role_id exists in the roles table.
    - If the role_id exists, it deletes any existing permissions for that role_id.
    - Inserts the new list of submodule permissions for the role.

    Parameters:
    - role_permissions: A RolePermissions object containing the role ID and a list of permissions.
    - db: Database session dependency.
    - current_member: The current authenticated member (dummy dependency for illustration).
    """
    try:
        return await permission_controller.create_permissions(role_permissions, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

