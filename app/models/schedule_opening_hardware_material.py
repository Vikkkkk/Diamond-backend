"""
This module Represents the table structure/Schema of ScheduleOpeningHardwareMaterials Table
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

class ScheduleOpeningHardwareMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ScheduleOpeningHardwareMaterials Table
    """
    __tablename__ = 'schedule_opening_hardware_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    desc = Column(String(255))
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    quantity = Column(Float)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    latest_data = Column(Boolean, default=True)
    has_ordered = Column(Boolean, default=False)
    has_shipped = Column(Boolean, default=False)
    version = Column(String(250), default='v0')
    final_extended_sell_amount = Column(Float)
    opening_hardware_material_id = Column(String(36), ForeignKey("opening_hardware_materials.id"))
    schedule_id = Column(String(36), ForeignKey("schedules.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))

    opening_hardware_material = relationship("OpeningHardwareMaterials", back_populates="opening_hardware_material_schedules")
    hardware_material_schedule = relationship("Schedules", back_populates="schedule_hardware_materials")
    schedule_component_data = relationship("ScheduleInstallationMappingComponentData", back_populates="schedule_opening_hardwares")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "desc": self.desc,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "opening_hardware_material_id": str(self.opening_hardware_material_id) if self.opening_hardware_material_id else None,
            "schedule_id": str(self.schedule_id) if self.schedule_id else None,
            "latest_data": self.latest_data,
            "has_ordered": self.has_ordered,
            "has_shipped": self.has_shipped,
            "version": self.version,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
        }