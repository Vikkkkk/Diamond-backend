"""
This module Represents the table structure/Schema of status Table
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


class StatusCategory(enum.Enum):
    BID_STATUS = 'BID_STATUS'
    PROJECT_STATUS = 'PROJECT_STATUS'

class Status(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of status Table
    """
    __tablename__ = 'status'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    type = Column(String(100))
    category = Column(Enum(StatusCategory))
    sort_order = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations/associations
    status_logs = relationship("ProjectStatusLogs", back_populates="status")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "type": self.type,
            "category": self.category,
            "sort_order": self.sort_order,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
        }