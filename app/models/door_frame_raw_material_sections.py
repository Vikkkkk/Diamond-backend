"""
This module Represents the table structure/Schema of SectionRawMaterials Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    func,    Enum,

)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models.project_materials import MATERIAL_TYPE
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
from dotenv import load_dotenv
load_dotenv()

class DoorFrameRawMaterialSections(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of DoorFrameRawMaterialSections Table
    """
    __tablename__ = 'door_frame_raw_material_sections'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(36), ForeignKey("projects.id"))
    material_type = Column(String(36) , Enum(MATERIAL_TYPE), nullable=False)
    raw_material_id = Column(String(36), ForeignKey("raw_materials.id"))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    raw_material = relationship("RawMaterials", back_populates="door_frame_raw_material_sections")
    project = relationship("Projects", back_populates="door_frame_raw_material_sections")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "raw_material_id": str(self.raw_material_id),
            "material_type": self.material_type,
            "project_id": str(self.project_id),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }