"""
This module Represents the table structure/Schema of ProjectTakeOffSheetSectionAreaItems Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    Float,
    String,
    DateTime,
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
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class ProjectTakeOffSheetSectionAreaItems(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectTakeOffSheetSectionAreaItems Table
    """
    __tablename__ = 'project_take_off_sheet_section_area_items'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    location_1 = Column(String(250))
    location_2 = Column(String(250))
    from_to = Column(String(250))
    opening_number = Column(String(100))
    desc = Column(String(255))
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    quantity = Column(Float)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    door_width = Column(String(100))
    door_height = Column(String(100))
    door_raw_material_type = Column(String(36))
    frame_raw_material_type = Column(String(36))
    adon_fields = Column(JSON, default={})
    project_take_off_sheet_section_area_id = Column(String(36), ForeignKey("project_take_off_sheet_section_areas.id"))
    project_take_off_sheet_section_id = Column(String(36), default=None)
    project_take_off_sheet_id = Column(String(36), default=None)
    installation_charge = Column(Float, default=None)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    take_off_sheet_section_area = relationship("ProjectTakeOffSheetSectionAreas", back_populates="take_off_sheet_section_area_items")
    opening_schedule_items = relationship("OpeningSchedules", back_populates="opening")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "location_1": self.location_1,
            "location_2": self.location_2,
            "from_to": self.from_to,
            "opening_number": self.opening_number,
            "desc": self.desc,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "quantity": self.quantity,
            "door_width": self.door_width,
            "door_height": self.door_height,
            "door_raw_material_type": self.door_raw_material_type,
            "frame_raw_material_type": self.frame_raw_material_type,
            "adon_fields": self.adon_fields,
            "project_take_off_sheet_section_area_id": str(self.project_take_off_sheet_section_area_id) if self.project_take_off_sheet_section_area_id else None,
            "project_take_off_sheet_section_id": str(self.project_take_off_sheet_section_id) if self.project_take_off_sheet_section_id else None,
            "project_take_off_sheet_id": str(self.project_take_off_sheet_id) if self.project_take_off_sheet_id else None,
            "installation_charge": self.installation_charge
            # "is_active": self.is_active,
            # "is_deleted": self.is_deleted,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            # "deleted_at": self.deleted_at if self.deleted_at is None else self.deleted_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "deleted_by": str(self.deleted_by) if self.deleted_by else None,
        }