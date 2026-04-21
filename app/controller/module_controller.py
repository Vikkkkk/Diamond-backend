"""
This module containes all logical operation and db operations those are related to modules add/update/read/delete.
"""
from loguru import logger
from models.modules import Modules
from sqlalchemy import or_
from sqlalchemy.orm import Session


async def get_modules(db: Session):
    """**Summary:**
    This method is responsible for retreaving list of modules.

    **Args:**
    - db (Session): db session referance
    """
    try:
        module_items = (
            db.query(Modules)
            .filter()
            .order_by(Modules.created_at.asc())
            .all()
        )
        response = {"data": module_items, "status": "success"}
        return response
    except Exception as error:
        logger.exception("get_modules:: error - " + str(error))
        raise error
    