"""
This module Represents the table structure/Schema of Projects Table
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

class ClientProjects(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of client_projects Table
    """
    __tablename__ = 'client_projects'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    bid_success = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    client_id = Column(String(36), ForeignKey("clients.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))

    # Relations/associations
    client = relationship("Clients", back_populates="client_projects")
    project = relationship("Projects", back_populates="project_clients")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "bid_success": self.bid_success,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            "client_id": str(self.client_id) if self.client_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
        }