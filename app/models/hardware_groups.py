"""
This module Represents the table structure/Schema of HardwareGroups Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    Float,
    String,
    DateTime,
    Enum,
    Text,
    ForeignKey,
    # PrimaryKeyConstraint,
    JSON,
    # Numeric
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import pytz
import os
import enum
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class HardwareGroups(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of HardwareGroups Table
    """
    __tablename__ = 'hardware_groups'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    desc = Column(String(255))
    item_count = Column(Float)
    quantity = Column(Float)
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    project_id = Column(String(36), ForeignKey("projects.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    opening_schedule = relationship("OpeningSchedules", back_populates="opening_hardware_group")
    project = relationship("Projects", back_populates="project_hardware_groups")
    hardware_group_materials = relationship("HardwareGroupMaterials", back_populates="hardware_group")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "item_count": self.item_count,
            "quantity": self.quantity,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "project_id": str(self.project_id) if self.project_id else None,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }