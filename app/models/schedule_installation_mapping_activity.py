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




class ScheduleInstallationMappingActivity(Base):
    
    __tablename__ = 'schedule_installation_mapping_activity'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    schedule_installation_mapping_id = Column(String(36), ForeignKey('schedule_installation_mapping.id',ondelete="CASCADE"))
    activity = Column(Text)
    is_new = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))

    schedule_installation_mapping = relationship("ScheduleInstallationMapping", back_populates="schedule_installation_mapping_activities")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the installation mapping activity.
        """
        return {
            "id": str(self.id),
            "schedule_installation_mapping_id": self.schedule_installation_mapping_id,
            "activity": self.activity,
            "is_new": self.is_new,
            "created_by": self.created_by,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }