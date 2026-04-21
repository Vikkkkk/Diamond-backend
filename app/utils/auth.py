"""
This module contains several auth related utility functions
"""
import datetime
import jwt
from fastapi import Depends
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from models import members
from schemas.auth_schemas import credential_exception
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from models import get_db, get_db_instance
import pytz
import os
from utils.common import get_user_time
from dotenv import load_dotenv
from sqlalchemy import or_
load_dotenv()
user_timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))


password_context = CryptContext(schemes="bcrypt", deprecated="auto")
# Define an OAuth2PasswordBearer instance
# oauth2_schema = OAuth2PasswordBearer(tokenUrl="token")
oauth2_schema = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(plain_text_password: str):
    """**Summary:**
    Generate and return a hash of the input plain text password.

    **Args:**
        - plain_text_password (String): actual password
    """
    try:
        return password_context.hash(plain_text_password)
    except Exception as error:
        logger.exception("hash_password:: error - " + str(error))
        raise error



def compare_password(hashed_password: str, plain_text_password: str):
    """**Summary:**
    Compare user provided password with hased password from Databse and
    check if the user provided password is correct or not

    **Args:**
        - plain_text_password (String): user provided password
        - hashed_password (String): hashed password from DB
    """
    try:
        return password_context.verify(plain_text_password, hashed_password)
    except Exception as error:
        logger.exception("compare_password:: error - " + str(error))
        raise error


def create_access_token(token_data: dict, db: Session, login: bool = False, expires_delta: timedelta = None):
    """**Summary:**
    Create JWT access token keping the token_data as the payload of the token

    **Args:**
        - token_data (Dict): access token payload that needts to be imposed in the token
        - db (Session): db session referance
        - login (bool): flag that will indicate if it is triggered by loin or not
        - expires_delta (timedelta): access token expiration time
    """
    try:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes= int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")))
        token_data.update({"exp": expire})
        jwt_token = jwt.encode(
            token_data, os.getenv("ENCRYPTION_KEY"), algorithm="HS256"
        )
        if jwt_token:
            member_item = db.query(members.Members).get(token_data["member_id"])
            # Add user token details to the user tokens table
            member_item.token = jwt_token
            if login:
                member_item.last_login = datetime.now()
            # db.commit()
            return jwt_token
        else:
            return None
    except Exception as error:
        db.rollback()
        logger.exception("create_access_token:: error - " + str(error))
        return None


def create_refresh_token(token_data: dict, db: Session, expires_delta: timedelta = None):
    """**Summary:**
    Create JWT refresh token keping the token_data as the payload of the token

    **Args:**
        - token_data (Dict): refresh token payload that needts to be imposed in the token
        - db (Session): db session referance
        - expires_delta (timedelta): refresh token expiration time
    """
    try:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days= int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "2")))
        token_data.update({"exp": expire})
        jwt_token = jwt.encode(
            token_data, os.getenv("ENCRYPTION_KEY"), algorithm="HS256"
        )
        if jwt_token:
            return jwt_token
        else:
            return None
    except Exception as error:
        db.rollback()
        logger.exception("create_refresh_token:: error - " + str(error))
        return None



def get_current_member(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """**Summary:**
    validate the acces token and return the current member for the access token

    **Args:**
        - credentials (HTTPAuthorizationCredentials): access token
    """
    db = get_db_instance()
    try:
        token = credentials.credentials
        payload = jwt.decode(token, os.getenv("ENCRYPTION_KEY"), algorithms="HS256")
        member_token = (
            db.query(members.Members)
            .filter_by(id=payload["member_id"], token=token, is_deleted= False)
            .first()
        )
        if not member_token:
            raise credential_exception
        else:
            current_member = db.query(members.Members).filter_by(id=payload["member_id"], is_deleted = False).first()
            current_member.token = token
            # print("current_member:: ",current_member.to_dict)
            return current_member
    except jwt.exceptions.ExpiredSignatureError:
        raise credential_exception
    except jwt.exceptions.InvalidTokenError:
        raise credential_exception
    except Exception as error:
        logger.exception("get_current_member:: error - " + str(error))
        raise error
    finally:
        db.close()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """**Summary:**
    validate the acces token is correct or not

    **Args:**
        - credentials (HTTPAuthorizationCredentials): access token
    """
    db = get_db_instance()
    try:
        token = credentials.credentials
        payload = jwt.decode(token, os.getenv("ENCRYPTION_KEY"), algorithms="HS256")
        member_token = (
            db.query(members.Members)
            .filter_by(id=payload["member_id"], token=token, is_deleted= False)
            .first()
        )
        if not member_token:
            return False
        else:
            return True
    except jwt.exceptions.ExpiredSignatureError:
        return False
    except jwt.exceptions.InvalidTokenError:
        return False
    except Exception as error:
        logger.exception("verify_token:: error - " + str(error))
        raise error
    finally:
        db.close()



def verify_refresh_token(token: str = Depends(oauth2_schema)):
    """**Summary:**
    validate the refresh token is correct or not

    **Args:**
        - token (String): refesh token
    """
    try:
        payload = jwt.decode(token, os.getenv("ENCRYPTION_KEY"), algorithms="HS256")
        return payload
    except jwt.exceptions.ExpiredSignatureError:
        return False
    except jwt.exceptions.InvalidTokenError:
        return False
    except Exception as error:
        logger.exception("verify_refresh_token:: error - " + str(error))
        raise False

