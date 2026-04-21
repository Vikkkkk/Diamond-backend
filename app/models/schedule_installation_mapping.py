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


class STATUS(enum.Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'

class ScheduleInstallationMapping(Base):
    """**Summary:**
    Represents the mapping between schedules and installation plans.
    """
    __tablename__ = 'schedule_installation_mapping'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    schedule_id = Column(String(36), ForeignKey('schedules.id'))
    wo_schedule_id = Column(String(36), ForeignKey('wo_schedules.id'))
    schedule_installation_plan_doc_id = Column(String(36), ForeignKey('project_installation_plan_docs.id'))
    coordinate_data = Column(JSON)
    status = Column(Enum(STATUS), default=STATUS.PENDING.value)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    installation_schedule = relationship("Schedules", back_populates="installation_schedule_mappings")
    installation_doc = relationship("ProjectInstallationPlanDocs", back_populates="schedule_installation_mappings")
    schedule_installation_preps = relationship("ScheduleInstallationMappingComponentData", back_populates="schedule_installation_mapping")
    schedule_installation_comments = relationship("ScheduleInstallationMappingComments", back_populates="schedule_installation_mapping",order_by="ScheduleInstallationMappingComments.created_at.asc()")
    schedule_installation_mapping_activities = relationship("ScheduleInstallationMappingActivity", back_populates="schedule_installation_mapping")
    schedule_installation_mapping_attachments = relationship("ScheduleInstallationMappingAttachment", back_populates="schedule_installation_mapping")
    wo_schedule = relationship("WoSchedules", back_populates="schedule_mappings")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the schedule-installation mapping.
        """
        return {
            "id": str(self.id),
            "schedule_id": self.schedule_id,
            "wo_schedule_id": self.wo_schedule_id,
            "schedule_installation_plan_doc_id": self.schedule_installation_plan_doc_id,
            "coordinate_data": self.coordinate_data,
            "status": self.status.value if self.status else None,
            "is_active": self.is_active,
            "prep_data": [prep.to_dict for prep in self.schedule_installation_preps] if self.schedule_installation_preps else [],
            "comments": [comment.to_dict for comment in self.schedule_installation_comments] if self.schedule_installation_comments else [],
            "opening_number": self.installation_schedule.opening_number,
            "wo_id": self.wo_schedule.wo_id if self.wo_schedule else None 
            # "created_by": self.created_by,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else None,
            # "updated_at": self.updated_at.strftime("%d/%m/%Y %H:%M:%S") if self.updated_at else None,
        }

