"""
This module containes all logical operation and db operations those are related to sub modules add/update/read/delete.
"""
from datetime import datetime
from typing import List
from utils.common import get_utc_time, generate_uuid, get_random_hex_code
from loguru import logger
from models.roles import Roles
from sqlalchemy import or_
from models import get_db
from fastapi import APIRouter, Depends, Request, Query, Path, UploadFile, Form, File
from sqlalchemy.orm import Session
from schemas.role_schemas import RoleCreate, RoleUpdate, Role
from utils.common import get_user_time
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse


async def get_role(role_id: str, db: Session = Depends(get_db)):
    try:
        result = db.query(Roles).filter(Roles.id == role_id).first()
        response = {'data': result.to_dict, 'status': 'success'}
        return JSONResponse(response)
    
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise


async def get_all_roles(db: Session = Depends(get_db)):
    try:
        result = db.query(Roles).all()
        role_list = []
        for role in result:
            role_list.append(role.to_dict)

        response = {'data': role_list, 'status': 'success'}
        return JSONResponse(response)
    
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise

async def create_role(role: RoleCreate, current_member, db: Session = Depends(get_db)):
    try:
        role_data = role.dict()
        role_data['created_by'] = current_member.id
        db_role = Roles(**role_data)
        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        return db_role
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise


async def update_role(role_id: str, role: RoleUpdate, current_member, db: Session = Depends(get_db)):
    try:
        db_role = db.query(Roles).filter(Roles.id == role_id).first()
        if db_role:
            role_data = role.model_dump(exclude_unset=True)
            role_data['updated_by'] = current_member.id
            role_data['updated_at'] = datetime.now()
            for key, value in role.model_dump(exclude_unset=True).items():
                setattr(db_role, key, value)
            db.commit()
            db.refresh(db_role)
        return db_role
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise

async def delete_role(role_id: str, db: Session = Depends(get_db)):
    try:
        db_role = db.query(Roles).filter(Roles.id == role_id).first()
        if db_role:
            db.delete(db_role)
            db.commit()
        return db_role
    except HTTPException as e:
        logger.exception(f"An unexpected error occurred: {e}")
        raise