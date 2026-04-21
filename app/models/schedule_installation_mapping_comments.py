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





class ScheduleInstallationMappingComments(Base):
    """**Summary:**
    Represents comments on a schedule installation mapping.
    """
    __tablename__ = 'schedule_installation_mapping_comments'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(36))
    schedule_installation_mapping_id = Column(String(36), ForeignKey('schedule_installation_mapping.id',ondelete="CASCADE"))
    comment = Column(Text)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    schedule_installation_mapping = relationship("ScheduleInstallationMapping", back_populates="schedule_installation_comments")
    schedule_installation_mapping_attachments = relationship("ScheduleInstallationMappingAttachment", back_populates="schedule_installation_comment")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the installation mapping comment.
        """
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "schedule_installation_mapping_id": self.schedule_installation_mapping_id,
            "comment": self.comment,
            # "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }