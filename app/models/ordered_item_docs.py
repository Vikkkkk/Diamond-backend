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
    Date,
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


class OrderedItemDocs(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectMaterials Table
    """
    __tablename__ = 'ordered_item_docs'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    order_item_id = Column(String(36), ForeignKey("ordered_items.id"), nullable=False)
    file_name = Column(String(255))
    file_path = Column(String(255))
    content_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    # order_item = relationship("OrderedItems", back_populates="order_item_docs")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "order_item_id": str(self.order_item_id),
            "file_name": self.file_name,
            "file_path": self.file_path,
            "content_type": self.content_type
        }