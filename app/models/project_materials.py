"""
This module Represents the table structure/Schema of ProjectMaterials Table
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


class MATERIAL_TYPE(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'

class DISCOUNT_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class SURCHARGE_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class ProjectMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectMaterials Table
    """
    __tablename__ = 'project_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    short_code = Column(String(100))
    desc = Column(Text, default=None)
    series = Column(String(255))
    material_type = Column(Enum(MATERIAL_TYPE))
    base_feature = Column(JSON)
    base_price = Column(JSON)
    adon_feature = Column(JSON)
    adon_price = Column(JSON)
    total_amount = Column(Float)
    selected_unit = Column(String(36), default=None)
    manufacturer_id = Column(String(36), ForeignKey("manufacturers.id"))
    brand_id = Column(String(36), ForeignKey("brands.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))
    raw_material_id = Column(String(36), ForeignKey("raw_materials.id"))
    hardware_product_category_id = Column(String(36), ForeignKey("hardware_product_category.id"))
    discount_is_basic = Column(Boolean, default=True)
    content_file_path = Column(Text, default=None)
    content_file_name = Column(Text, default=None)
    content_file_type = Column(String(36), default=None)
    markup = Column(Float)
    margin = Column(Float)
    has_pricebook = Column(Boolean, default=True)
    discount = Column(Float)
    discount_type = Column(Enum(DISCOUNT_TYPE))
    surcharge = Column(Float)
    surcharge_type = Column(Enum(SURCHARGE_TYPE))
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    aggregation_rule = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Define relationships
    opening_schedule = relationship("OpeningSchedules", back_populates="opening_material")
    project = relationship("Projects", back_populates="project_materials")
    material_brand = relationship("Brands", back_populates="brand_materials")
    material_manufacturer = relationship("Manufacturers", back_populates="manufacturer_materials")
    material_groups = relationship("HardwareGroupMaterials", back_populates="hardware_group_material")
    raw_material = relationship("RawMaterials", back_populates="project_materials")
    take_off_hardware_product_category = relationship("HardwareProductCategory", back_populates="take_off_hardware_product_catagory_materials")

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
            "material_type": self.material_type,
            "base_feature": self.base_feature,
            "base_price": self.base_price,
            "adon_feature": self.adon_feature,
            "adon_price": self.adon_price,
            "total_amount": self.total_amount,
            "selected_unit": self.selected_unit,
            "manufacturer_id": str(self.manufacturer_id) if self.manufacturer_id else None,
            "brand_id": str(self.brand_id) if self.brand_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "raw_material_id": str(self.raw_material_id) if self.raw_material_id else None,
            "hardware_product_category_id": self.hardware_product_category_id if self.hardware_product_category_id else None,
            "discount_is_basic": self.discount_is_basic,
            "content_file_path": self.content_file_path,
            "content_file_name": self.content_file_name,
            "content_file_type": self.content_file_type,
            "markup": self.markup,
            "margin": self.margin,
            "has_pricebook": self.has_pricebook,
            "discount": self.discount,
            "discount_type": self.discount_type,
            "surcharge": self.surcharge,
            "surcharge_type": self.surcharge_type,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "aggregation_rule": self.aggregation_rule,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }
