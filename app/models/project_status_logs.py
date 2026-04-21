"""
This module Represents the table structure/Schema of Project Status Logs Table
"""
from datetime import datetime
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
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import pytz
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class ProjectStatusLogs(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Project Status Logs Table
    """
    __tablename__ = 'project_status_logs'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    status_id = Column(String(36), ForeignKey("status.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))

    # Relations/associations
    project = relationship("Projects", back_populates="project_logs")
    status = relationship("Status", back_populates="status_logs")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            "project_id": str(self.project_id) if self.project_id else self.project_id,
            "status_id": str(self.status_id) if self.status_id else self.status_id,
        }