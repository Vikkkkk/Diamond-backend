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
from utils.common import generate_uuid, get_aws_full_path
import pytz
import enum
import os
from dotenv import load_dotenv
load_dotenv()


class ProjectInstallationPlanDocs(Base):
    """**Summary:**
    Represents the installation plan documents for a project.
    """
    __tablename__ = 'project_installation_plan_docs'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    area = Column(String(250))
    project_id = Column(String(36))
    file_name = Column(String(250),default=None)
    content_type = Column(String(250),default=None)
    file_path = Column(Text,default=None)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    schedule_installation_mappings = relationship("ScheduleInstallationMapping", back_populates="installation_doc")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the installation plan document.
        """
        return {
            "id": str(self.id),
            "area": self.area,
            "project_id": self.project_id,
            "file_name": self.file_name,
            "content_type": self.content_type,
            "file_path": get_aws_full_path(self.file_path) if self.file_path else None,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else None,
        }
