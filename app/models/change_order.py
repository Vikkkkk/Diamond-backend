from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, Text, Enum, Integer, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import Base
from utils.common import generate_uuid
import enum




class ChangeOrderStatusEnum(enum.Enum):
    PENDING = 'PENDING'
    IN_REVIEW = 'IN_REVIEW'
    APPROVED = 'APPROVED'
    COMPLETED = 'COMPLETED'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'

# Table: change_order
class ChangeOrder(Base):
    __tablename__ = 'change_order'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36),default=None)
    co_number = Column(String(255),default=None)
    description = Column(String(255),default=None)
    priority = Column(Integer, default=1)
    current_status = Column(Enum(ChangeOrderStatusEnum), default=ChangeOrderStatusEnum.PENDING)
    has_applied = Column(Boolean, default=False)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())


    co_schedules = relationship("CoSchedules", back_populates="change_order")
    change_order_status_logs = relationship("ChangeOrderStatusLogs", back_populates="change_order")
    change_order_docs = relationship("ChangeOrderDocs", back_populates="change_order")
    


    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the change order.
        """
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "co_number": self.co_number,
            "description": self.description,
            "priority": self.priority,
            "current_status": self.current_status.name if self.current_status else None,
            "has_applied": self.has_applied if self.has_applied else False,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }