"""
This module Represents the table structure/Schema of ProjectTakeOffSheetSectionAreaItems Table
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
    Enum,
    Enum,
    Enum,
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
import enum
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))


class ADDON_OPENING_FIELD_TYPE(enum.Enum):
    NUMBER = 'NUMBER'
    TEXT = 'TEXT'
    DROPDOWN = 'DROPDOWN'
    FILE_UPLOAD = 'FILE_UPLOAD'



class ADDON_OPENING_FIELD_TYPE(enum.Enum):
    NUMBER = 'NUMBER'
    TEXT = 'TEXT'
    DROPDOWN = 'DROPDOWN'
    FILE_UPLOAD = 'FILE_UPLOAD'


class AdonOpeningFields(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectTakeOffSheetSectionAreaItems Table
    """
    __tablename__ = 'adon_opening_fields'


    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    desc = Column(String(255))
    has_price_dependancy = Column(Boolean, default=True)
    field_type = Column(Enum(ADDON_OPENING_FIELD_TYPE), default=None)
    field_category = Column(Text, default=None, info=" This can be any one of the options or any cobination of 'TAKE_OFF_SHEET', 'OPENING_SCHEDULE', 'HARDWARE_SCHEDULE' with comma seperated string")
    search_keywords = Column(Text, default=None)
    rule = Column(JSON, default={})
    is_adon_field = Column(Boolean, default=False)
    is_door_data = Column(Boolean, default=False)
    is_frame_data = Column(Boolean, default=False)
    is_hw_data = Column(Boolean, default=False)
    is_opening_data = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order =  Column(Integer, default=9999)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    adon_field_options = relationship("AdonOpeningFieldOptions", back_populates="adon_field")
    schedule_data = relationship("ScheduleData", back_populates="adon_field")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "has_price_dependancy": self.has_price_dependancy,
            "field_type": self.field_type.value if self.field_type is not None else None,
            "field_category": self.field_category,
            "search_keywords": self.search_keywords,
            "rule": self.rule,
            "is_adon_field": self.is_adon_field,
            "is_door_data": self.is_door_data,
            "is_frame_data": self.is_frame_data,
            "is_hw_data": self.is_hw_data,
            "is_opening_data": self.is_opening_data,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
        }