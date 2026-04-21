from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, Text, Enum, Integer, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import Base
from utils.common import generate_uuid
import enum



class CoSchedules(Base):
    __tablename__ = 'co_schedules'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    co_id = Column(String(36), ForeignKey('change_order.id'), default=None)
    schedule_id = Column(String(36), ForeignKey('schedules.id'), default=None)
    current_version = Column(String(255), default=None)

    frame_section_file_path = Column(Text, default=None)
    frame_section_file_type = Column(String(100), default=None)

    total_amount = Column(Float, default=None)
    total_sell_amount = Column(Float, default=None)
    total_base_amount = Column(Float, default=None)
    total_extended_sell_amount = Column(Float, default=None)
    quantity = Column(Float, default=None)
    final_amount = Column(Float, default=None)
    final_sell_amount = Column(Float, default=None)
    final_base_amount = Column(Float, default=None)
    final_extended_sell_amount = Column(Float, default=None)
    installation_amount = Column(Float, default=0)
    opening_number = Column(String(100),default=None)
    area = Column(String(250), default=None)
    location_1 = Column(String(250), default=None)
    from_to = Column(String(250), default=None)
    location_2 = Column(String(250), default=None)
    door_qty = Column(Float, default=None)
    frame_qty = Column(Float, default=None)
    door_material_id = Column(String(36), default=None)
    door_material_code = Column(String(100), default=None)
    frame_material_id = Column(String(36), default=None)
    frame_material_code = Column(String(100), default=None)
    extra_attributes = Column(JSON, default=None)
    door_type = Column(String(100), default=None)
    swing = Column(String(100), default=None)
    schedule_data = Column(JSON, default=None)
    schedule_hardware_data = Column(JSON, default=None)

    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    change_order = relationship("ChangeOrder", back_populates="co_schedules")
    schedule = relationship("Schedules", back_populates="co_schedules")

    @property
    def to_dict(self):
        """Returns a dictionary representation of the CoSchedule instance."""
        return {
            "id": str(self.id),
            "co_id": self.co_id,
            "schedule_id": self.schedule_id,
            "current_version": self.current_version,

            "frame_section_file_path": self.frame_section_file_path,
            "frame_section_file_type": self.frame_section_file_type,

            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "installation_amount": self.installation_amount,
            "opening_number": self.opening_number,
            "area": self.area,
            "location_1": self.location_1,
            "from_to": self.from_to,
            "location_2": self.location_2,
            "door_qty": self.door_qty,
            "frame_qty": self.frame_qty,
            "door_material_id": self.door_material_id,
            "door_material_code": self.door_material_code,
            "frame_material_id": self.frame_material_id,
            "frame_material_code": self.frame_material_code,
            "extra_attributes": self.extra_attributes,
            "door_type": self.door_type,
            "swing": self.swing,
            # "schedule_data": self.schedule_data,
            # "schedule_hardware_data": self.schedule_hardware_data,

            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
