"""
This module Represents the table structure/Schema of Modules Table
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
    JSON,
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

class RolePermissions(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Modules Table
    """
    __tablename__ = 'role_permissions'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    role_id = Column(String(255), ForeignKey("roles.id"))
    sub_module_id = Column(String(36), ForeignKey("sub_modules.id"))
    allowed_roles = Column(JSON, nullable=True)
    is_read = Column(Boolean, default=True)
    is_write = Column(Boolean, default=False)
    is_delete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    # Relations/associations
    sub_module = relationship('SubModules', back_populates='role_permissions')
    role = relationship('Roles', back_populates='role_sub_modules')


    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "role_id": self.role_id,
            "sub_module_id": self.sub_module_id,
            "allowed_roles": self.allowed_roles,
            "is_read": self.is_read,
            "is_write": self.is_write,
            "is_delete": self.is_delete,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }