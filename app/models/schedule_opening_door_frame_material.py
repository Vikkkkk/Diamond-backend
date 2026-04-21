"""
This module Represents the table structure/Schema of ScheduleOpeningDoorFrameMaterials Table
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
    JSON,
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

class MATERIAL_TYPE(enum.Enum):
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'

class ScheduleOpeningDoorFrameMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ScheduleOpeningDoorFrameMaterials Table
    
    This junction table links schedules to door/frame materials, tracking quantities and pricing
    information specific to each schedule-material combination.
    """
    __tablename__ = 'schedule_opening_door_frame_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    desc = Column(String(255))
    material_type = Column(Enum(MATERIAL_TYPE), default=None)
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    quantity = Column(Float)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    latest_data = Column(Boolean, default=True)
    has_ordered = Column(Boolean, default=False)
    has_shipped = Column(Boolean, default=False)
    version = Column(String(250), default='v0')
    opening_door_frame_material_id = Column(String(36), ForeignKey("opening_door_frame_materials.id"))
    schedule_id = Column(String(36), ForeignKey("schedules.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    part_number = Column(String(255))

    # Define relationships
    opening_door_frame_material = relationship("OpeningDoorFrameMaterials", back_populates="opening_door_frame_material_schedules")
    door_frame_material_schedule = relationship("Schedules", back_populates="schedule_door_frame_materials")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "desc": self.desc,
            "material_type": self.material_type.value if self.material_type else None,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "opening_door_frame_material_id": str(self.opening_door_frame_material_id) if self.opening_door_frame_material_id else None,
            "schedule_id": str(self.schedule_id) if self.schedule_id else None,
            "latest_data": self.latest_data,
            "has_ordered": self.has_ordered,
            "has_shipped": self.has_shipped,
            "version": self.version,
        }
