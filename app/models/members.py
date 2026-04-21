"""
This module Represents the table structure/Schema of Members Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    # Float,
    String,
    DateTime,
    Text,
    ForeignKey,
    # PrimaryKeyConstraint,
    # JSON,
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import pytz
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class Members(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Members Table
    """
    __tablename__ = 'members'

    id = Column(String(36),default=generate_uuid, primary_key=True, unique=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True)
    phone = Column(String(20), unique=True)
    password = Column(String(100))
    token = Column(Text)
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Relations/associations
    member_roles = relationship('MemberRole', back_populates='member')


    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "name": f"{self.first_name} {self.last_name}",
            "email": self.email,
            "phone": self.phone,
            # "password": self.password,
            "token": self.token,
            # "is_super_admin": self.is_super_admin,
            # "is_active": self.is_active,
            "last_login": self.last_login if self.last_login is None else self.last_login.strftime("%d/%m/%Y %H:%M:%S")
        }