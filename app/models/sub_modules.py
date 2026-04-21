"""
This module Represents the table structure/Schema of Sub Modules Table
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

class SubModules(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Sub Modules Table
    """
    __tablename__ = 'sub_modules'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    module_id = Column(String(36), ForeignKey("modules.id"))
    name = Column(String(255))
    label = Column(String(255))
    sort_order = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    
    # Relations/associations
    module = relationship('Modules', back_populates='sub_modules')
    role_permissions = relationship('RolePermissions', back_populates='sub_module')

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "module_id": str(self.module_id) if self.module_id else self.module_id,
            "name": self.name,
            "label": self.label,
            "sort_order": self.sort_order,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None
        }