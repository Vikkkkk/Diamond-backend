from typing import List
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query, Path
from starlette import status as starlette_status
from models import get_db
from models.members import Members
from schemas.auth_schemas import LoginRequest, LoginResponse, RefreshTokenRequest,  RefreshTokenResponse
from controller import auth_controller
from loguru import logger
from utils.auth import verify_token, get_current_member

router = APIRouter(prefix="/auth", tags=["Auth APIs"])


@router.post("/login", response_model=LoginResponse, status_code=starlette_status.HTTP_200_OK)
async def login(
    login_request_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for login a member to the system.

    **Args:**
    - `login_request_data` (dict): This will contain the login credentials, i.e email and password.
    - `db` (Session): db session referance. Defaults to Depends(get_db).

    """
    try:
        return await auth_controller.login(login_request_data, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.delete("/logout", status_code=starlette_status.HTTP_200_OK)
async def logout(
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    """**Summary:**
    This method is responsible for logout a member from the system.

    **Args:**
    - `current_member` (Members): This will contain member details of current loggedin member.
    - `db` (Session): db session referance. Defaults to Depends(get_db).

    """
    try:
        # print("current_member:: ",current_member)
        return await auth_controller.logout(current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.put("/refresh_token", response_model=RefreshTokenResponse, status_code=starlette_status.HTTP_200_OK)
async def refresh_token(
    refresh_token_request_data: RefreshTokenRequest,
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    """**Summary:**
    This method is responsible for logout a member from the system.

    **Args:**
    - `refresh_token_request_data` (RefreshTokenRequest): token for refreshing the access token.
    - `current_member` (Members): This will contain member details of current loggedin member.
    - `db` (Session): db session referance. Defaults to Depends(get_db).

    """
    try:
        # print("current_member:: ",current_member)
        return await auth_controller.refresh_token(refresh_token_request_data, current_member, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

