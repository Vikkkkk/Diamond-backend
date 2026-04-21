"""
This module Represents the table structure/Schema of Manufacturers Table
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
    func,
    Float
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

class Manufacturers(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Manufacturers Table
    """
    __tablename__ = 'manufacturers'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    code = Column(String(100))
    name = Column(String(100))
    desc = Column(Text)
    expected_delivery_days = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Relationships
    brands = relationship("Brands", back_populates="manufacturer")
    manufacturer_materials = relationship("ProjectMaterials", back_populates="material_manufacturer")
    manufacturer_catalogs = relationship("RawMaterialCatalogMapping", back_populates="catalog_manufacturer")
    manufacturer_opening_hardwares = relationship("OpeningHardwareMaterials", back_populates="opening_hardware_manufacturer")
    manufacturer_opening_door_frames = relationship("OpeningDoorFrameMaterials", back_populates="opening_door_frame_manufacturer")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "desc": self.desc,
            # "is_active": self.is_active,
            # "is_deleted": self.is_deleted,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            # "deleted_at": self.deleted_at if self.deleted_at is None else self.deleted_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "deleted_by": str(self.deleted_by) if self.deleted_by else None,
        }