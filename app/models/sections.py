"""
This module Represents the table structure/Schema of Sections Table
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

class Sections(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Sections Table
    """
    __tablename__ = 'sections'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    item_number = Column(String(36))
    name = Column(String(100))
    sort_order =  Column(Integer)
    
    code = Column(String(100))
    is_door_frame = Column(Boolean, default=False)
    is_hwd = Column(Boolean, default=False)
    is_installation = Column(Boolean, default=False)
    default_section = Column(Boolean, default=False)
    has_pricebook = Column(Boolean, default=True) 
    
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    take_off_sheet_sections = relationship("ProjectTakeOffSheetSections", back_populates = "section")
    project_raw_materials = relationship("ProjectRawMaterials", back_populates = "section")
    section_raw_materials = relationship("SectionRawMaterials", back_populates = "section")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "item_number": self.item_number,
            "name": self.name,
            "sort_order": self.sort_order,

            "code": self.code,
            "is_door_frame": self.is_door_frame,
            "is_hwd": self.is_hwd,
            "is_installation": self.is_installation,
            "default_section": self.default_section,
            "has_pricebook": self.has_pricebook,

            "is_deleted": self.is_deleted

            # "created_at": self.created_at if self.created_at is None else self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }