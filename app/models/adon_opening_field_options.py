"""
This module Represents the table structure/Schema of AdonOpeningFieldOptions Table
"""
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
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class AdonOpeningFieldOptions(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of AdonOpeningFieldOptions Table
    """
    __tablename__ = 'adon_opening_field_options'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    desc = Column(String(255))
    search_keywords = Column(Text, default=None)
    rule = Column(JSON, default={})
    adon_opening_field_id = Column(String(36), ForeignKey("adon_opening_fields.id"))
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    adon_field = relationship("AdonOpeningFields", back_populates="adon_field_options")
    schedule_data = relationship("ScheduleData", back_populates="adon_field_option")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "search_keywords": self.search_keywords,
            "rule": self.rule,
            "is_default": self.is_default,
            "adon_opening_field_id": str(self.adon_opening_field_id) if self.adon_opening_field_id else None,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
        }