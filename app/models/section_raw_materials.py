"""
This module Represents the table structure/Schema of SectionRawMaterials Table
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

class SectionRawMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of SectionRawMaterials Table
    """
    __tablename__ = 'section_raw_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    section_id = Column(String(36), ForeignKey("sections.id"))
    raw_material_id = Column(String(36), ForeignKey("raw_materials.id"))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    section = relationship("Sections", back_populates="section_raw_materials")
    raw_material = relationship("RawMaterials", back_populates="raw_material_sections")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "section_id": self.section_id,
            "raw_material_id": self.raw_material_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }