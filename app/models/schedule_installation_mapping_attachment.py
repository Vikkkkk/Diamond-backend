from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    # Float,
    String,
    DateTime,
    Text,
    ForeignKey,
    # PrimaryKeyConstraint,
    # JSON,
    Enum,
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import enum
import pytz
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))


class ScheduleInstallationMappingAttachment(Base):
    __tablename__ = 'schedule_installation_mapping_attachment'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    schedule_installation_mapping_id = Column(String(36), ForeignKey('schedule_installation_mapping.id',ondelete="CASCADE"))
    schedule_installation_mapping_comment_id = Column(String(36), ForeignKey('schedule_installation_mapping_comments.id',ondelete="CASCADE"))
    file_name = Column(String(255))
    file_path = Column(String(255))
    file_type = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))

    # Relations/associations
    schedule_installation_mapping = relationship("ScheduleInstallationMapping", back_populates="schedule_installation_mapping_attachments")
    schedule_installation_comment = relationship("ScheduleInstallationMappingComments", back_populates="schedule_installation_mapping_attachments")


    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the attachment data.
        """
        return {
            "id": str(self.id),
            "schedule_installation_mapping_id": self.schedule_installation_mapping_id,
            "schedule_installation_mapping_comment_id": self.schedule_installation_mapping_comment_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            # "created_by": self.created_by,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else None,
        }