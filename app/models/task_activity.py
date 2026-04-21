"""
This module Represents the table structure/Schema of task_activity Table
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


class TaskActivity(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of task_activity Table
    """
    __tablename__ = 'task_activity'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    task_id = Column(String(36))
    activity = Column(Text)
    is_new = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))


    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "task_id": self.task_id,
            "activity": self.activity,
            "is_new": self.is_new,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "created_by": str(self.created_by) if self.created_by else None
        }