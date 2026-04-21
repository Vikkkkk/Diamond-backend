"""
This module Represents the table structure/Schema of Schedules Table
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
    Enum,
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
import enum
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class SCHEDULE_TYPE(enum.Enum):
    HARDWARE = 'HARDWARE'
    OPENING = 'OPENING'

class Schedules(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Schedules Table
    """
    __tablename__ = 'schedules'


    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    opening_number = Column(String(100))
    area = Column(String(250))
    location_1 = Column(String(250))
    from_to = Column(String(250))
    location_2 = Column(String(250))
    door_qty = Column(Float)
    frame_qty = Column(Float)
    door_material_id = Column(String(100))
    door_material_code = Column(String(100))
    frame_material_id = Column(String(100))
    frame_material_code = Column(String(100))
    extra_attributes = Column(JSON, default=None)
    door_type = Column(String(250))
    swing = Column(String(250))
    name = Column(String(100))
    desc = Column(Text, default=None)
    frame_section_file_path = Column(Text, default=None)
    frame_section_file_type = Column(String(100), default=None)
    type = Column(Enum(SCHEDULE_TYPE), default=SCHEDULE_TYPE.OPENING.value)
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    quantity = Column(Float, default=1)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    installation_amount = Column(Float, default=0)
    # markup = Column(Float, default=0)
    # discount = Column(Float, default=0)
    # discount_type = Column(Float, default=0)

    has_door_requested = Column(Boolean, default=False)
    has_frame_requested = Column(Boolean, default=False)
    has_hw_requested = Column(Boolean, default=False)

    has_door_ordered = Column(Boolean, default=False)
    has_frame_ordered = Column(Boolean, default=False)
    has_hw_ordered = Column(Boolean, default=False)

    has_door_shipped = Column(Boolean, default=False)
    has_frame_shipped = Column(Boolean, default=False)
    has_hw_shipped = Column(Boolean, default=False)

    take_off_area_item_id = Column(String(36), default=None)
    section_id = Column(String(36), default=None)
    project_id = Column(String(36), default=None)
    take_off_data = Column(JSON, default=None)
    take_off_hardware_data = Column(JSON, default=None)
    is_active = Column(Boolean, default=True)
    is_freezed = Column(Boolean, default=False)
    is_in_change_order = Column(Boolean, default=False)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    schedule_data = relationship("ScheduleData", back_populates="schedule")
    schedule_hardware_materials = relationship("ScheduleOpeningHardwareMaterials", back_populates="hardware_material_schedule")
    schedule_door_frame_materials = relationship("ScheduleOpeningDoorFrameMaterials", back_populates="door_frame_material_schedule")
    installation_schedule_mappings = relationship("ScheduleInstallationMapping", back_populates="installation_schedule")
    co_change_stats = relationship("CoChangeStats", back_populates="schedule")
    co_schedules = relationship("CoSchedules", back_populates="schedule")
    
    

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "opening_number": self.opening_number,
            "area": self.area,
            "location_1": self.location_1,
            "location_2": self.location_2,
            "from_to": self.from_to,
            "door_qty": self.door_qty,
            "frame_qty": self.frame_qty,
            "door_material_id": self.door_material_id,
            "door_material_code": self.door_material_code,
            "frame_material_code": self.frame_material_code,
            "frame_material_id": self.frame_material_id,
            "extra_attributes": self.extra_attributes,
            "door_type": self.door_type,
            "swing": self.swing,
            "name": self.name,
            "desc": self.desc,
            "frame_section_file_path": self.frame_section_file_path,
            "frame_section_file_type": self.frame_section_file_type,
            "type": self.type.value if self.type else None,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "take_off_area_item_id": self.take_off_area_item_id,
            "section_id": self.section_id,
            "project_id": self.project_id,
            "has_door_ordered": self.has_door_ordered,
            "has_frame_ordered": self.has_frame_ordered,
            "has_hw_ordered": self.has_hw_ordered,
            "has_door_shipped": self.has_door_shipped,
            "has_frame_shipped": self.has_frame_shipped,
            "has_hw_shipped": self.has_hw_shipped,
            # "take_off_data": self.take_off_data,
            # "take_off_hardware_data": self.take_off_hardware_data,
            "installation_amount": self.installation_amount,
            "is_freezed": self.is_freezed,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
        }