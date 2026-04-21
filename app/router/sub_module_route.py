"""
This module containes all routes those are related to sub modules add/update/read/delete.
"""
from typing import List
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from controller import sub_module_controller
from loguru import logger
from schemas.sub_module_schema import SubModulesResponse
from utils.auth import verify_token
from schemas.auth_schemas import invalid_credential_resp

router = APIRouter(prefix="/sub_modules", tags=["Sub Module APIs"])

@router.get("/get_sub_modules", response_model=SubModulesResponse, status_code=status.HTTP_200_OK)
@logger.catch
async def get_modules(
    module_id: str = Query(description="module id for which it will return the sub modules",default=None),
    verified_token: bool = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """**Summary:**
    This method is responsible for retreaving list of sub modules of a particular module or irrespective of module.
    depending on the module_id provided or not

    **Args:**
    - `db` (Session): db session referance
    - `module_id` (String): module Id for which it will return the submodules
    - `verified_token` (Boolean): It will indicate if the request is authenticated or not
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        return await sub_module_controller.get_sub_modules(db, module_id)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)