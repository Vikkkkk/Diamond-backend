"""
This module containes all schemas those are related to auth add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from fastapi import status as fast_api_status
from fastapi.responses import JSONResponse
from fastapi import Form
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
    
# Credential exceptions error
invalid_credential_resp = JSONResponse(
    status_code=401,
    content={"message": "Unauthenticated"}
)

credential_exception = HTTPException(
    status_code=401,
    detail="Unauthenticated"
)

class LoginRequest(BaseModel):
    """**Summary:**
    This class contains the schema of each login request
    """
    password: str = Field(description="login password")
    email: str = Field(description="login email")

    
class LoginResponse(BaseModel):
    """**Summary:**
    This class contains the schema of each login response
    """
    access_token: str = Field(description="jwt access token")
    refresh_token: str = Field(description="jwt refresh token")
    status: str


class RefreshTokenRequest(BaseModel):
    """**Summary:**
    This class contains the schema of each refresh token request
    """
    refresh_token: str = Field(description="jwt refresh token")


class RefreshTokenResponse(BaseModel):
    """**Summary:**
    This class contains the schema of each refresh token response
    """
    access_token: str = Field(description="jwt access token")
    status: str

    
    