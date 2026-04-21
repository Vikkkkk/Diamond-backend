from typing import List
from utils.common import get_utc_time, generate_uuid, get_random_hex_code, generate_uuid
from loguru import logger
from models.sections import Sections
# from schemas.project_schemas import Project
from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import math
from utils.common import get_user_time
import json
import os
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

load_dotenv()
    

async def get_sections(db: Session):
    """
    Retrieve a list of sections from the database.
    Args:
        db (Database): The database session.
    Returns:
        dict: A dictionary containing the list of sections and a success status.
    Raises:
        Exception: Raises any unexpected error that occurs during the operation. The error is logged for debugging.
    """
    try:
        sections = (
            db.query(Sections)
            .filter(Sections.is_deleted == False)
            .order_by(Sections.sort_order.asc())
            .all()
        )
        response = []
        for section in sections:
            response.append(section.to_dict)

        response = {"data": response, "status": "success"}
        return response
    except Exception as e:
        logger.exception("get_projects:: error - " + str(e))
        raise e