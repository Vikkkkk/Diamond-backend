"""
This module Represents the table structure/Schema of project_task Table
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


class ProjectTask(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of project_task Table
    """
    __tablename__ = 'project_task'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(36), ForeignKey("projects.id"))
    task_status_id = Column(String(36), ForeignKey("task_status.id"))
    task_title = Column(String(255))
    task_description = Column(Text)
    start_date = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))
    is_past_due = Column(Boolean, default=False)
    is_near_due_date = Column(Boolean, default=False)
    is_estimation = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    # Relations/associations
    task_status = relationship("TaskStatus", back_populates="project_task")
    task_attachments = relationship("TaskAttachments", back_populates="project_task")
    task_members = relationship("TaskMembers", back_populates="project_task")
    task_comments = relationship("TaskComments", back_populates="project_task")
    project = relationship("Projects", back_populates="tasks")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "task_status_id": self.task_status_id,
            "task_title": self.task_title,
            "task_description": self.task_description,
            "start_date": self.start_date,
            "due_date": self.due_date,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None
        }