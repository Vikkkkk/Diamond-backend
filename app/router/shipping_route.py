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
from controller import shipping_controller
from loguru import logger
from utils.auth import verify_token, get_current_member
from utils.auth import verify_token
from schemas.brand_schema import BrandRequest
from schemas.auth_schemas import invalid_credential_resp
from schemas.shippimg_schema import GenerateLabelRequest
from schemas.take_off_sheet_item_schema import TakeOffSheetItem
from middleware.permission_middleware import role_required, project_access_required

router = APIRouter(prefix="/shipping", tags=["Sipping Order APIs"])


@router.post("generate_item_labels", status_code=status.HTTP_200_OK)
@logger.catch
async def get_unrequested_items(
    request_data: GenerateLabelRequest,
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member),
    role_required = Depends(role_required(["Admin", "Project Manager", "Shipping Personal", "Receiving Personal"])),  # Specify allowed roles here
):
    """
    Generate shipping labels for a given order item.
    Args:
        order_item_id (str): The order item ID.
        request_data (GenerateLabelRequest): The request data containing the crate numbers.
        db (Session): The database session.
        current_member (Members): The current member.
    Returns:
        JSONResponse: The response containing the generated shipping labels.
    """
    try:
        return await shipping_controller.generate_shipping_label(request_data, db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

