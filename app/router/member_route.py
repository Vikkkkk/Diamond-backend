"""
This module containes all routes those are related to members add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path
from starlette import status as starlette_status
from models import get_db
from models.members import Members
from schemas.member_schema import Member, MemberResponse, MembersResponse, ChangePasswordRequest, RoleAssign, ProfileSwitchRequest
from schemas.project_schemas import ProjectResponse
from controller import member_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from schemas.auth_schemas import invalid_credential_resp
from middleware.permission_middleware import role_required
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/member", tags=["Member APIs"])

@router.get("/get_members", status_code=starlette_status.HTTP_200_OK)
async def get_members(
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    role_id: str = Query(None, alias="role_id"),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving paginated list of members depending on the input range

    This method fetches a subset of members from the database based on the specified
    page number and page size.

    **Args:**
    - `db`: The database session object.
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `keyword` (str): this will be usefull for keyword search on name and email.
    """
    try:
        return await member_controller.get_members(db, page, page_size, keyword, role_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/get_member/{id}", response_model=MemberResponse, status_code=starlette_status.HTTP_200_OK)
@logger.catch 
async def get_member(
    id: str,
    verified_token: bool = Depends(verify_token),
    role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving the details of the input member id

    **Args:**
    - `db` (Session): db session referance. Defaults to Depends(get_db).
    - `id` (str): member Id for which it will run the fetch query. Defaults to Query(description="Member ID").
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not

    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await member_controller.get_member(db, id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/me", response_model=MemberResponse, status_code=starlette_status.HTTP_200_OK)
@logger.catch 
async def get_member(
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    """**Summary:**
    This method is responsible for retreaving the details of the input member id

    **Args:**
    - `db` (Session): db session referance. Defaults to Depends(get_db).
    - `current_member` (Members): This will contain member details of current loggedin member.

    """
    try:
        return await member_controller.get_me_data(db, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/insert_member", status_code=starlette_status.HTTP_201_CREATED)
@logger.catch
async def create_member(
    member_create_request: Member,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Chief Estimator", "Chief Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method takes single member data and add the member to the DB

    **Args:**
    - `member_create_request` (Member): Member data to be added. reffer to the member schema for the structure
    - `db` (Session): db session referance. Defaults to Depends(get_db).
    - `current_member` (Members): This will contain member details of current loggedin member.

    """
    try:
        return await member_controller.create_member(member_create_request, db, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.post("/assign_role/{member_id}", status_code=starlette_status.HTTP_201_CREATED)
@logger.catch
async def assign_role(
    member_id: str,
    member_assign_role_request: RoleAssign,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Chief Estimator", "Chief Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method takes single member data and add the member to the DB

    **Args:**
    - `member_create_request` (Member): Member data to be added. reffer to the member schema for the structure
    - `db` (Session): db session referance. Defaults to Depends(get_db).
    - `current_member` (Members): This will contain member details of current loggedin member.

    """
    try:
        roleIds = member_assign_role_request.roleIds
        return await member_controller.assign_role(member_id, roleIds, db, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.delete("/delete_member/{id}", status_code=starlette_status.HTTP_200_OK)
@logger.catch
async def delete_member(
    id: str,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method deletes a member from the DB based on the provided id.

    **Args:**
    - `id` (int): The unique identifier of the member to be deleted.
    - `db` (Session): DB session reference. Defaults to Depends(get_db).
    - `current_member` (Members): This will contain member details of current loggedin member.

    """
    try:
        # Delete the member
        return await member_controller.delete_member_soft(db, id, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.put("/update_member/{id}", status_code=starlette_status.HTTP_200_OK)
@logger.catch
async def update_member(
    id: str,
    member_update_request: Member,
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Chief Estimator", "Chief Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method updates a member's data in the DB

    **Args:**
    - `id` (int): ID of the member to be updated
    - `member_update_request` (Members): Updated member data. Refer to the Members schema for the structure
    - `db` (Session): db session reference. Defaults to Depends(get_db).
    - `current_member` (Members): This will contain member details of current loggedin member.
    """
    try:
        return await member_controller.update_member(db, id, member_update_request, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/change_password/{id}", status_code=starlette_status.HTTP_200_OK)
@logger.catch
async def change_password(
    id: str,
    request_data: ChangePasswordRequest,
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """**Summary:**
    Update password for member.

    **Args:**
    - `id` (str): The unique identifier of the member whose password is to be changed.
    - `request_data` (ChangePasswordRequest): The request data containing the new password and confirm password.
    - `current_member` (Members): The currently authenticated member obtained from the token.
    - `db` (Session): The database session.

    **Returns:**
    - `JSONResponse`: A JSON response indicating the success of the password change.

    **Raises:**
    - `HTTPException`: If there's an issue with the password change process, a 500 Internal Server Error is returned.
    """
    try:
        return await member_controller.change_password(db, id, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/get_assigned_projects/{member_id}", status_code=starlette_status.HTTP_200_OK)
async def get_assigned_projects(
    member_id: str,
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    verified_token: bool = Depends(verify_token),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving paginated list of projects far a specific memder depending on the input range

    This method fetches a subset of members from the database based on the specified
    page number and page size.

    **Args:**
    - `member_id` (int): member_id of the member to be search
    - `db`: The database session object.
    - `page` (Union[None,int]): The page number to retrieve.
    - `page_size` (Union[None,int]): The number of items per page.
    - `keyword` (str): this will be usefull for keyword search on name and email.
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:

        if not verified_token:
            return invalid_credential_resp
        return await member_controller.get_assigned_projects(db, member_id, page, page_size, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/get_role_members/{role_id}", status_code=starlette_status.HTTP_200_OK)
@logger.catch
async def get_role_members(
    role_id: str = Path(..., title="Role ID", description="The ID of the Role"),
    page_size: Union[None, int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    current_member: Members = Depends(get_current_member),
    # role_required = Depends(role_required(["Admin", "Estimator","Project Manager"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    Get members of a module with optional filtering and pagination.

    **Args:**
    - `role_id` (str, query, optional): The ID of the module for which to retrieve members.
    - `current_member` (Member, dependency): Dependency to verify the user's token and return the current member.
    - `db` (Session, dependency): The database session dependency.
    """
    try:
        return await member_controller.get_role_members(db, role_id, page_size, keyword)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.get("/get_member_detailed_list", status_code=starlette_status.HTTP_200_OK)
@logger.catch
async def get_member_detailed_list(
    current_member: Members = Depends(get_current_member),
    page: Union[None,int] = Query(None, alias="page"),
    page_size: Union[None,int] = Query(None, alias="page_size"),
    keyword: str = Query(None, alias="keyword"),
    # role_required = Depends(role_required(["Admin", "Estimator"])),  # Specify allowed roles here
    db: Session = Depends(get_db)
):
    """**Summary:**
    Get members of a module with optional filtering and pagination.

    **Args:**
    - `current_member` (Member, dependency): Dependency to verify the user's token and return the current member.
    - `page` (int, query, optional): The page number for pagination (default: None).
    - `page_size` (int, query, optional): The number of items per page for pagination (default: None).
    - `keyword` (str, query, optional): A keyword to filter members (default: None).
    - `db` (Session, dependency): The database session dependency.
    """
    try:
        return await member_controller.get_member_detailed_list(db, page, page_size, keyword, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    


@router.put("/switch_profile", status_code=starlette_status.HTTP_200_OK)
@logger.catch
async def switch_profile(
    request_data: ProfileSwitchRequest,
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    try:
        return await member_controller.switch_profile(db, request_data, current_member)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)