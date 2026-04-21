"""
This module Represents the table structure/Schema of RawMaterials Table
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
    # JSON,
    Enum,
    # Numeric
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import pytz
import os
import enum
from dotenv import load_dotenv
load_dotenv()


class RawMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of RawMaterials Table
    """
    __tablename__ = 'raw_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    item_number = Column(String(36))
    code = Column(String(20))
    name = Column(String(255), default=None)
    desc = Column(String(255))
    sort_order = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Define relationships
    project_raw_materials = relationship("ProjectRawMaterials", back_populates="raw_material")
    project_materials = relationship("ProjectMaterials", back_populates="raw_material")
    raw_material_catalogs = relationship("RawMaterialCatalogMapping", back_populates="catalog_raw_material")
    raw_material_sections = relationship("SectionRawMaterials", back_populates="raw_material")
    door_frame_raw_material_sections = relationship("DoorFrameRawMaterialSections", back_populates="raw_material")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "item_number": self.item_number,
            "code": self.code,
            "name": self.name,
            "desc": self.desc,
            "sort_order": self.sort_order,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }
