"""
This module Represents the table structure/Schema of QuotationRevision Table
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

class QuotationRevision(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of QuotationRevision Table
    """
    __tablename__ = 'quotation_revision'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(100))
    file_path = Column(String(100))
    revision_number = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))


    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        def format_datetime(value):
            return value.strftime("%Y-%m-%dT%H:%M:%S") if value else None
        
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "file_path": self.file_path,
            "revision_number": self.revision_number,
            "created_at": format_datetime(self.created_at),
            # "created_by": str(self.created_by) if self.created_by else None
        }