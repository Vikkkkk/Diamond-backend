"""
This module containes all logical operation and db operations those are related to sub modules add/update/read/delete.
"""
from typing import List
from utils.common import get_utc_time, generate_uuid, get_random_hex_code
from loguru import logger
from models.sub_modules import SubModules
from sqlalchemy import or_
from sqlalchemy.orm import Session


async def get_sub_modules(db: Session, module_id: str):
    """**Summary:**
    This method is responsible for retreaving list of sub modules of a particular module or irrespective of module.
    depending on the module_id provided or not

    **Args:**
    - db (Session): db session referance
    - id (String): module Id for which it will run the fetch query
    """
    try:
        if module_id is not None:
            sub_module_items = (
                db.query(SubModules)
                .filter(
                    SubModules.module_id.in_([module_id]),
                )
                .order_by(SubModules.created_at.asc())
                .all()
            )
        else:
            sub_module_items = db.query(SubModules).filter(SubModules.is_deleted == False).order_by('created_at').all()
        response = {"data": sub_module_items, "status": "success"}
        return response
    except Exception as error:
        logger.exception("get_sub_modules:: error - " + str(error))
        raise error
    