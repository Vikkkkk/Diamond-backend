"""
This module containes all routes those are related to takeoff-sheet add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.members import Members
from controller import brand_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.brand_schema import BrandRequest
from schemas.auth_schemas import invalid_credential_resp
from schemas.take_off_sheet_item_schema import TakeOffSheetItem

router = APIRouter(prefix="/brand", tags=["Brand APIs"])

@router.post("/addBrand", status_code=status.HTTP_201_CREATED)
@logger.catch
async def addBrand(
    brand_request: BrandRequest,
    db: Session = Depends(get_db)
):
    """**Summary:**
    add brand.

    **Args:**
    - `brand_request` (BrandRequest): Brand Request body.
    - `db` (Session): Dependency to get the database session.

    **Returns:**
    - `JSONResponse`: A JSON response containing the manufacturers.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        return await brand_controller.add_brand(brand_request, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

