"""
This module Represents the table structure/Schema of ProjectTakeOffSheets Table
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
    func,
    Float
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

class ProjectTakeOffSheets(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectTakeOffSheets Table
    """
    __tablename__ = 'project_take_off_sheets'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    desc = Column(String(255))
    project_id = Column(String(36), ForeignKey("projects.id"))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    total_sell_amount = Column(Float)
    total_base_amount  = Column(Float)
    total_extended_sell_amount = Column(Float)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    project = relationship('Projects', back_populates='take_off_sheet')
   
    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "project_id": str(self.project_id) if self.project_id else None,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            # "deleted_at": self.deleted_at if self.deleted_at is None else self.deleted_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "deleted_by": str(self.deleted_by) if self.deleted_by else None,
        }