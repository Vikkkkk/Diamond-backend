"""
This module containes all logical operation and db operations those are related to members authentication.
"""
from loguru import logger
from models.members import Members
from models.member_role import MemberRole
from fastapi.responses import JSONResponse
from utils.auth import hash_password, compare_password, create_access_token, create_refresh_token, verify_refresh_token
from schemas.auth_schemas import LoginRequest, LoginResponse, RefreshTokenRequest,  RefreshTokenResponse, credential_exception
from sqlalchemy.orm import Session


async def login(data: LoginRequest, db: Session):
    """**Summary:**
    This method is responsible for validating the login creadentials and generating the access token and refresh token

    **Args:**
        - db (Session): db session referance
        - data (LoginRequest): it will contain the user credentials
    """
    try:
        # Check if member exists or not
        is_member_exists = (
            db.query(Members)
            .filter(
                Members.email == data.email,
                Members.is_deleted == False
            )
            .first()
        )
        if is_member_exists:
            # Check if password is correct
            if is_member_exists.password and not compare_password(
                is_member_exists.password, data.password
            ):
                # Return error response
                return JSONResponse(
                    status_code=401,
                    content={"message": "Invalid Member Credentials"},
                )
            else:
                # Check if the member permission exists
                if not db.query(MemberRole).filter(MemberRole.member_id == is_member_exists.id).first():
                    return JSONResponse(
                        status_code=401,
                        content={"message": "You don't have any access"},
                    )
                # Create JWT token data parameter
                token_data = {
                    "member_id": str(is_member_exists.id),
                }
                # Generate JWT access token
                access_token = create_access_token(token_data, db, login=True)
                if access_token:
                    # Commit into DB
                    db.commit()
                    # Generate JWT refresh token
                    refresh_token = create_refresh_token(token_data, db)
                    if refresh_token:
                        # Return success response
                        response = {"access_token": access_token, "refresh_token": refresh_token, "status": "success"}
                        return response
                    else:
                        # Return error response
                        return JSONResponse(
                            status_code=500,
                            content={
                                "message": "Unable to generate refresh token",
                            },
                        )
                else:
                    # Return error response
                    return JSONResponse(
                        status_code=500,
                        content={
                            "message": "Unable to generate access token",
                        },
                    )
        else:
            return JSONResponse(
                status_code=401, content={"message": "Invalid Member credentials"}
            )
    except Exception as error:
        logger.exception("login:: error - " + str(error))
        raise error




async def logout(current_member: Members, db: Session):
    """**Summary:**
    This method is responsible for logout a member from the system.

    **Args:**
        - current_member (Members): This will contain member details of current loggedin member.
        - db (Session): db session referance. Defaults to Depends(get_db).

    """
    try:
        member_data = (
            db.query(Members)
            .filter(
                Members.id == current_member.id,
                Members.token == current_member.token,
                Members.is_deleted == False
            )
            .first()
        )
        member_data.token = None
        db.commit()
        return JSONResponse(
            status_code=200,
            content={"message": "Logged out successfully"},
        )
    except Exception as error:
        logger.exception("logout:: error - " + str(error))
        return credential_exception


async def refresh_token(data: RefreshTokenRequest, current_member: Members, db: Session):
    """**Summary:**
    This method is responsible for refreshing the acces token.

    **Args:**
        - data (RefreshTokenRequest): token for refreshing the access token.
        - current_member (Members): This will contain member details of current loggedin member.
        - db (Session): db session referance. Defaults to Depends(get_db).

    """
    try:
        is_verified = verify_refresh_token(data.refresh_token)
        print("is_verified:: ",is_verified)
        if not is_verified:
            return JSONResponse(
                status_code=401, content={"message": "Invalid refreshtoken"}
            )
        else:
            # Create JWT token data parameter
            token_data = {
                "member_id": str(current_member.id),
            }
            # Generate JWT access token
            access_token = create_access_token(token_data, db)
            if access_token:
                # Commit into DB
                db.commit()
                # Return success response
                response = {"access_token": access_token, "status": "success"}
                return response
            else:
                # Return error response
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": "Unable to generate access token",
                    },
                )
    except Exception as error:
        logger.exception("logout:: error - " + str(error))
        return credential_exception
