"""
This module Represents the table structure/Schema of OpeningHardwareMaterials Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    Float,
    String,
    DateTime,
    Enum,
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
import enum
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class DISCOUNT_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class SURCHARGE_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class OpeningHardwareMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of OpeningHardwareMaterials Table
    """
    __tablename__ = 'opening_hardware_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    short_code = Column(String(100))
    desc = Column(Text, default=None)
    series = Column(String(255))
    base_feature = Column(JSON, default={})
    base_price = Column(JSON, default={})
    adon_feature = Column(JSON, default={})
    adon_price = Column(JSON, default={})
    manufacturer_id = Column(String(36), ForeignKey("manufacturers.id"))
    brand_id = Column(String(36), ForeignKey("brands.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))
    hardware_product_category_id = Column(String(36), ForeignKey("hardware_product_category.id"))
    content_file_path = Column(Text, default=None)
    content_file_name = Column(Text, default=None)
    content_file_type = Column(String(36), default=None)
    markup = Column(Float, default=0)
    margin = Column(Float, default=0)
    is_basic_discount = Column(Boolean, default=True)
    discount = Column(Float, default=0)
    discount_type = Column(Enum(DISCOUNT_TYPE), default=DISCOUNT_TYPE.PERCENTAGE.value)
    surcharge = Column(Float, default=0)
    surcharge_type = Column(Enum(SURCHARGE_TYPE), default=SURCHARGE_TYPE.PERCENTAGE.value)
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    quantity = Column(Float)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Define relationships
    project = relationship("Projects", back_populates="project_opening_hardware_materials")
    opening_hardware_brand = relationship("Brands", back_populates="brand_opening_hardwares")
    opening_hardware_manufacturer = relationship("Manufacturers", back_populates="manufacturer_opening_hardwares")
    opening_hardware_material_schedules = relationship("ScheduleOpeningHardwareMaterials", back_populates="opening_hardware_material")
    opening_hardware_product_category = relationship("HardwareProductCategory", back_populates="hardware_product_catagory_materials")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "short_code": self.short_code,
            "desc": self.desc,
            "series": self.series,
            "base_feature": self.base_feature,
            "base_price": self.base_price,
            "adon_feature": self.adon_feature,
            "adon_price": self.adon_price,
            "manufacturer_id": str(self.manufacturer_id) if self.manufacturer_id else None,
            "brand_id": str(self.brand_id) if self.brand_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "hardware_product_category_id": str(self.hardware_product_category_id) if self.hardware_product_category_id else None,
            "content_file_path": self.content_file_path,
            "content_file_name": self.content_file_name,
            "content_file_type": self.content_file_type,
            "markup": self.markup,
            "margin": self.margin,
            "is_basic_discount": self.is_basic_discount,
            "discount": self.discount,
            "discount_type": self.discount_type.value if self.discount_type else None,
            "surcharge": self.surcharge,
            "surcharge_type": self.surcharge_type.value if self.surcharge_type else None,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }
