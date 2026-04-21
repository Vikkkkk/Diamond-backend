"""
This module Represents the table structure/Schema of ProjectRawMaterialManufacturerQuotes Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Date,
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
    Enum,
    Float
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


class ProjectRawMaterialManufacturerQuotes(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectRawMaterialManufacturerQuotes Table
    """
    __tablename__ = 'project_raw_material_manufacturer_quotes'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(36))
    raw_materials_catalog_mapping_id = Column(String(36), ForeignKey("raw_material_catalog_mapping.id"))
    discount_type = Column(Enum(DISCOUNT_TYPE))
    discount = Column(Float)
    file_path = Column(String(256))
    quote_text = Column(String(256))
    expiry_date = Column(Date)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    # Define relationships
    quote_catalog = relationship("RawMaterialCatalogMapping", back_populates="catalog_quotes")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "raw_materials_catalog_mapping_id": str(self.raw_materials_catalog_mapping_id) if self.raw_materials_catalog_mapping_id else None,
            "discount_type": self.discount_type,
            "discount": self.discount,
            "file_path": self.file_path,
            "file_name": os.path.basename(self.file_path) if self.file_path else None,
            "quote_text": self.quote_text,
            "expiry_date": self.expiry_date,
            # "expiry_date": self.expiry_date if self.expiry_date is None else self.expiry_date.strftime("%Y-%m-%dT%H:%M:%S"),
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }