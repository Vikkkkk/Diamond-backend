"""
This module Represents the table structure/Schema of Tender Documents Table
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
from utils.common import get_aws_full_path
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class TenderDocuments(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Tender Documents Table
    """
    __tablename__ = 'tender_documents'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    file_path = Column(Text)
    file_name = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    project_id = Column(String(36), ForeignKey("projects.id"))

    # Relations/associations
    project = relationship("Projects", back_populates="tender_documents")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "file_path": get_aws_full_path(self.file_path) if self.file_path is not None else None,
            "file_name": self.file_name,
            # "is_active": self.is_active,
            "project_id": str(self.project_id) if self.project_id else self.project_id,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }