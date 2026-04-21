"""
This module Represents the table structure/Schema of HardwareProductCategory Table
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

class HardwareProductCategory(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of HardwareProductCategory Table
    """
    __tablename__ = 'hardware_product_category'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    search_keywords = Column(Text, default=None)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hardware_product_catagory_materials = relationship("OpeningHardwareMaterials", back_populates="opening_hardware_product_category")
    take_off_hardware_product_catagory_materials = relationship("ProjectMaterials", back_populates="take_off_hardware_product_category")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "search_keywords": self.search_keywords,
            "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
        }