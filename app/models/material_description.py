"""
This module represents the table structure/schema of MaterialDescription table
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, func
from models import Base
from utils.common import generate_uuid


class MaterialDescription(Base):
    """Stores generated descriptions for a material combination."""

    __tablename__ = "material_description"

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    material_type = Column(String(36), nullable=False)
    raw_material_type = Column(String(100), nullable=False)
    series = Column(String(255), nullable=True)
    base_feature = Column(JSON, nullable=True)
    adon_feature = Column(JSON, nullable=True)
    adon_fields = Column(JSON, nullable=True)
    combination_key = Column(String(64), nullable=False, unique=True, index=True)
    desc = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
