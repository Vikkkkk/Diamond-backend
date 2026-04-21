"""
This module Represents the table structure/Schema of Brands Table
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

class Brands(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Brands Table
    """
    __tablename__ = 'brands'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    code = Column(String(100))
    name = Column(String(100))
    desc = Column(Text)
    manufacturer_id = Column(String(36), ForeignKey("manufacturers.id"))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Relationships
    manufacturer = relationship("Manufacturers", back_populates="brands")
    brand_materials = relationship("ProjectMaterials", back_populates="material_brand")
    brand_catalogs = relationship("RawMaterialCatalogMapping", back_populates="catalog_brand")
    brand_opening_hardwares = relationship("OpeningHardwareMaterials", back_populates="opening_hardware_brand")
    brand_opening_door_frames = relationship("OpeningDoorFrameMaterials", back_populates="opening_door_frame_brand")

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
            "manufacturer_id": str(self.manufacturer_id) if self.manufacturer_id else None,
            # "is_active": self.is_active,
            # "is_deleted": self.is_deleted,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            # "deleted_at": self.deleted_at if self.deleted_at is None else self.deleted_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "deleted_by": str(self.deleted_by) if self.deleted_by else None,
        }