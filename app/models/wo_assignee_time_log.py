from sqlalchemy import (
    Column, String, DateTime, Float, ForeignKey, func
)
from sqlalchemy.orm import relationship
from models import Base
from utils.common import generate_uuid



class WoAssigneeTimeLog(Base):
    __tablename__ = 'wo_assignee_time_log'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    wo_assignee_id = Column(String(36), ForeignKey('wo_assignee.id'),default=None)
    duration = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(36))

    wo_assignee = relationship("WoAssignee", back_populates="wo_assignee_time_logs")


    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the work order assignee time log.
        """
        return {
            "id": str(self.id),
            "wo_assignee_id": self.wo_assignee_id,
            "duration": self.duration,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }