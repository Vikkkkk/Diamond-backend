"""
This module Represents the table structure/Schema of RawMaterialCatalogMapping Table
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

class RawMaterialCatalogMapping(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of RawMaterialCatalogMapping Table
    """
    __tablename__ = 'raw_material_catalog_mapping'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    manufacturer_id = Column(String(36), ForeignKey("manufacturers.id"))
    brand_id = Column(String(36), ForeignKey("brands.id"))
    raw_material_id = Column(String(36), ForeignKey("raw_materials.id"))
    discount_percentage = Column(Float)
    accepted_types = Column(String(255))
    sort_order =  Column(Integer)
    has_data = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    
    catalog_quotes = relationship("ProjectRawMaterialManufacturerQuotes", back_populates="quote_catalog")
    catalog_brand = relationship("Brands", back_populates="brand_catalogs")
    catalog_manufacturer = relationship("Manufacturers", back_populates="manufacturer_catalogs")
    catalog_raw_material = relationship("RawMaterials", back_populates="raw_material_catalogs")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "manufacturer_id": self.manufacturer_id,
            "brand_id": self.brand_id,
            "raw_material_id": self.raw_material_id,
            "discount_percentage": self.discount_percentage,
            "accepted_types": self.accepted_types,
            "sort_order": self.sort_order,
            "has_data": self.has_data,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }