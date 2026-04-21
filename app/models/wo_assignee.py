from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, Text, Enum, Integer, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import Base
from utils.common import generate_uuid
import enum



class WoAssignee(Base):
    __tablename__ = 'wo_assignee'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    wo_id = Column(String(36), ForeignKey('work_order.id'),default=None)
    member_id = Column(String(36),default=None)
    has_started_working = Column(Boolean, default=False)
    location_details = Column(JSON, default=None)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    work_order = relationship("WorkOrder", back_populates="wo_assignees")
    wo_assignee_time_logs = relationship("WoAssigneeTimeLog", back_populates="wo_assignee")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the work order assignee.
        """
        return {
            "id": str(self.id),
            "wo_id": self.wo_id,
            "member_id": self.member_id,
            "has_started_working": self.has_started_working,
            "location_details": self.location_details,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }