"""
This module Represents the table structure/Schema of ProjectMaterials Table
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


class COMPONENTS(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'

class OpeningSchedules(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of OpeningSchedules Table
    """
    __tablename__ = 'opening_schedules'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    desc = Column(Text, default=None)
    component = Column(Enum(COMPONENTS))
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    quantity = Column(Float)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    raw_material_id = Column(String(36), default=None)
    project_take_off_sheet_section_area_item_id = Column(String(36), ForeignKey("project_take_off_sheet_section_area_items.id"))
    project_material_id = Column(String(36), ForeignKey("project_materials.id"))
    hardware_group_id = Column(String(36), ForeignKey("hardware_groups.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    opening = relationship("ProjectTakeOffSheetSectionAreaItems", back_populates="opening_schedule_items")
    opening_material = relationship("ProjectMaterials", back_populates="opening_schedule")
    opening_hardware_group = relationship("HardwareGroups", back_populates="opening_schedule")
    project = relationship("Projects", back_populates="project_opening_schedules")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "desc": self.desc,
            "component": self.component,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "raw_material_id": self.raw_material_id,
            "project_take_off_sheet_section_area_item_id": str(self.project_take_off_sheet_section_area_item_id) if self.project_take_off_sheet_section_area_item_id else None,
            "project_material_id": str(self.project_material_id) if self.project_material_id else None,
            "hardware_group_id": str(self.hardware_group_id) if self.hardware_group_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }