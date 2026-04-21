"""
This module Represents the table structure/Schema of OpeningDoorFrameMaterials Table
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
    JSON,
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
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'

class DISCOUNT_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class SURCHARGE_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class OpeningDoorFrameMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of OpeningDoorFrameMaterials Table
    """
    __tablename__ = 'opening_door_frame_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    short_code = Column(String(100))
    desc = Column(Text, default=None)
    series = Column(String(255))
    raw_material_code = Column(String(20), default=None)
    
    # Classification & Status
    material_type = Column(Enum(MATERIAL_TYPE), default=None)
    is_active = Column(Boolean, default=True)
    
    # Feature & Pricing Data
    base_feature = Column(JSON, default={})
    base_price = Column(JSON, default={})
    adon_feature = Column(JSON, default={})
    adon_price = Column(JSON, default={})
    
    # Identification/FKs
    manufacturer_id = Column(String(36), ForeignKey("manufacturers.id"))
    brand_id = Column(String(36), ForeignKey("brands.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))
    
    # File Details
    content_file_path = Column(Text, default=None)
    content_file_name = Column(Text, default=None)
    content_file_type = Column(String(36), default=None)
    
    # Adjustments
    markup = Column(Float, default=0)
    margin = Column(Float, default=0)
    is_basic_discount = Column(Boolean, default=True)
    discount = Column(Float, default=0)
    discount_type = Column(Enum(DISCOUNT_TYPE), default=DISCOUNT_TYPE.PERCENTAGE.value)
    surcharge = Column(Float, default=0)
    surcharge_type = Column(Enum(SURCHARGE_TYPE), default=SURCHARGE_TYPE.PERCENTAGE.value)
    
    # Base Calculations
    total_amount = Column(Float)
    total_sell_amount = Column(Float)
    total_base_amount = Column(Float)
    total_extended_sell_amount = Column(Float)
    
    # Final Schedule Calculations
    quantity = Column(Float, default=1)
    final_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_base_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    schedule_master_data = Column(JSON, default={})
    
    # Audit Trail
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Define relationships
    project = relationship("Projects", back_populates="project_opening_door_frame_materials")
    opening_door_frame_brand = relationship("Brands", back_populates="brand_opening_door_frames")
    opening_door_frame_manufacturer = relationship("Manufacturers", back_populates="manufacturer_opening_door_frames")
    opening_door_frame_material_schedules = relationship("ScheduleOpeningDoorFrameMaterials", back_populates="opening_door_frame_material")

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
            "raw_material_code": self.raw_material_code,
            "material_type": self.material_type.value if self.material_type else None,
            "is_active": self.is_active,
            "base_feature": self.base_feature,
            "base_price": self.base_price,
            "adon_feature": self.adon_feature,
            "adon_price": self.adon_price,
            "manufacturer_id": str(self.manufacturer_id) if self.manufacturer_id else None,
            "brand_id": str(self.brand_id) if self.brand_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
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
        }
