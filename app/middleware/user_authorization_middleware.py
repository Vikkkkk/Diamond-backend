from fastapi.responses import JSONResponse
from fastapi import status
from models import get_db_instance
from loguru import logger
from fastapi.responses import JSONResponse
from functools import wraps
from models.modules import Modules
from models.roles import Roles
from models.member_role import MemberRole
from models.role_permissions import RolePermissions
from schemas.auth_schemas import invalid_credential_resp


def admin_required(func):
    """**summary**
    This module is responsible for validating the authorization of the incomming request.
    It Checks if the Request is comming from admin or not
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            current_member = kwargs.get('current_member')
            db = get_db_instance()
            try:
                role_data = db.query(Roles).filter_by(name="Admin").first()
                permissions = db.query(MemberRole).filter_by(member_id=current_member.id, role_id=role_data.id).all()
                if len(permissions) == 0:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={'message': "Unauthorized aceess, Not admin"}
                    )
            except Exception as error:
                logger.exception(f"admin_required:: An unexpected error occurred: {error}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={'message': "Error while checking for Authorization"}
                )
            finally:
                # Closing the DB instance connection.
                db.close()
        except Exception as error:
            logger.exception(f"admin_required:: An unexpected error occurred: {error}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={'message': "Error while checking for Authorization"}
            )
        return await func(*args, **kwargs)
    return wrapper



def estimator_required(func):
    """**summary**
    This module is responsible for validating the authorization of the incomming request.
    It Checks if the Request is comming from estimator or not
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            current_member = kwargs.get('current_member')
            db = get_db_instance()
            try:
                role_data = db.query(Roles).filter_by(name="Estimator").first()
                permissions = db.query(MemberRole).filter_by(member_id=current_member.id, role_id=role_data.id).all()
                if len(permissions) == 0:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={'message': "Unauthorized aceess, Not Estimator"}
                    )
            except Exception as error:
                logger.exception(f"estimator_required:: An unexpected error occurred: {error}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={'message': "Error while checking for Authorization"}
                )
            finally:
                # Closing the DB instance connection.
                db.close()
        except Exception as error:
            logger.exception(f"estimator_required:: An unexpected error occurred: {error}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={'message': "Error while checking for Authorization"}
            )
        return await func(*args, **kwargs)
    return wrapper



def admin_or_estimator_required(func):
    """**summary**
    This module is responsible for validating the authorization of the incomming request.
    It Checks if the Request is comming from estimator/admin or not
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            current_member = kwargs.get('current_member')
            db = get_db_instance()
            accessed_by = ["Estimation","Admin"]
            try:
                module_data = db.query(Modules).filter(Modules.name.in_(accessed_by), Modules.is_deleted==False).all()
                module_data_ids = [elm.id for elm in module_data]
                permissions = db.query(MemberPermissions).filter(MemberPermissions.member_id==current_member.id, MemberPermissions.module_id.in_(module_data_ids)).all()
                if len(permissions) == 0:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={'message': "Unauthorized aceess, Not Estimator Nor Admin"}
                    )
            except Exception as error:
                logger.exception(f"admin_or_estimator_required:: An unexpected error occurred: {error}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={'message': "Error while checking for Authorization"}
                )
            finally:
                # Closing the DB instance connection.
                db.close()
        except Exception as error:
            logger.exception(f"admin_or_estimator_required:: An unexpected error occurred: {error}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={'message': "Error while checking for Authorization"}
            )
        return await func(*args, **kwargs)
    return wrapper