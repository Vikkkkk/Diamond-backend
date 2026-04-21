from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from starlette import status
from models import get_db
from models.members import Members
from schemas.role_schemas import RoleCreate, RoleUpdate, Role
from schemas.project_details_schema import ProjectResponse, ProjectsResponse, ProjectModuleMemberResponse
from controller import role_controller
from loguru import logger
from utils.auth import verify_token
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required

router = APIRouter(prefix="", tags=["Role APIs"])


@router.post("/roles", status_code=status.HTTP_200_OK)
@logger.catch
async def create_role(
    role: RoleCreate, 
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
    
):
    try:
        return await role_controller.create_role(role, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/roles/{role_id}", status_code=status.HTTP_200_OK)
@logger.catch
async def get_role(
    role_id: str, 
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await role_controller.get_role(role_id, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/roles/", status_code=status.HTTP_200_OK)
async def list_all_roles(
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    try:
        return await role_controller.get_all_roles(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/roles/{role_id}", status_code=status.HTTP_200_OK)
async def update_role(
    role_id: str, 
    role: RoleUpdate,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    try:
        return await role_controller.update_role(role_id, role, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

#TODO
@router.delete("/roles/{role_id}", status_code=status.HTTP_200_OK)
async def delete_role(
    role_id: str, 
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator", "Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    try:
        if not verified_token:
            return invalid_credential_resp
        return await role_controller.delete_role(role_id, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
