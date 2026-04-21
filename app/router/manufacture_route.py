"""
This module containes all routes those are related to takeoff-sheet add/update/read/delete.
"""
from typing import List, Union
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Request, Query
from starlette import status
from models import get_db
from models.manufacturers import Manufacturers
from controller import manufacture_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.manufacture_schema import Manufacturer
from schemas.auth_schemas import invalid_credential_resp


router = APIRouter(prefix="/manufacture", tags=["Manufacture APIs"])

@router.post("/addManufacture", status_code=status.HTTP_201_CREATED)
@logger.catch
async def addManufacture(
    request_data: Manufacturer,
    db: Session = Depends(get_db)
):
    """
    Add a new manufacturer or update an existing one.

    Args:
        request_data (Manufacturer): Data of the manufacturer to be added or updated.
        db (Session, optional): Database session object. Defaults to Depends(get_db).

    Returns:
        JSONResponse: JSON response indicating success or failure.
    """

    try:
        return await manufacture_controller.addManufacture(request_data, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)