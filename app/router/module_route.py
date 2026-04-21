"""
This module containes all routes those are related to modules add/update/read/delete.
"""
from typing import List
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from controller import module_controller
from loguru import logger
from schemas.module_schema import ModulesResponse
from utils.auth import verify_token
from schemas.auth_schemas import invalid_credential_resp

router = APIRouter(prefix="/modules", tags=["Module APIs"])

@router.get("/get_modules", response_model=ModulesResponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_modules(
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving list of modules.

    **Args:**
    - `db` (Session): db session referance
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await module_controller.get_modules(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
