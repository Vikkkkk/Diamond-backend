"""
This module Represents the table structure/Schema of ProjectRawMaterials Table
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

class CATEGORY(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'


class ProjectRawMaterials(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectMaterials Table
    """
    __tablename__ = 'project_raw_materials'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    project_id = Column(String(36), ForeignKey("projects.id"))
    raw_material_id = Column(String(36), ForeignKey("raw_materials.id"))
    section_id = Column(String(36), ForeignKey("sections.id"))
    final_amount = Column(Float)
    final_base_amount = Column(Float)
    final_sell_amount = Column(Float)
    final_extended_sell_amount = Column(Float)
    quantity = Column(Float)
    markup = Column(Float)
    margin = Column(Float)
    discount = Column(Float, default=0)
    surcharge = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    surcharge_amount = Column(Float, default=0)
    category = Column(Enum(CATEGORY))
    discount_type = Column(Enum(DISCOUNT_TYPE))
    surcharge_type = Column(Enum(SURCHARGE_TYPE))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))

    # Define relationships
    # material_type = relationship("RawMaterialType", back_populates="project_raw_materials")
    section = relationship("Sections", back_populates="project_raw_materials")
    project = relationship("Projects", back_populates="project_raw_materials")
    raw_material = relationship("RawMaterials", back_populates="project_raw_materials")
    take_off_sheet_notes = relationship("ProjectTakeOffSheetNotes", back_populates="project_raw_material")
    section = relationship("Sections", back_populates = "project_raw_materials")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "raw_material_id": str(self.raw_material_id) if self.raw_material_id else None,
            "section_id": str(self.section_id) if self.section_id else None,
            "final_amount": self.final_amount,
            "final_base_amount": self.final_base_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "quantity": self.quantity,
            "markup": self.markup,
            "margin": self.margin,
            "discount": self.discount,
            "surcharge": self.surcharge,
            "category": self.category,
            "discount_amount": self.discount_amount,
            "surcharge_amount": self.surcharge_amount,
            "discount_type": self.discount_type,
            "surcharge_type": self.surcharge_type,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None
        }
