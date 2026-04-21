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


class COMPONENTS(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'

class SHIPPING_STATUS(enum.Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    AWAIT_SHIPPING = 'AWAIT_SHIPPING'
    DONE = 'DONE'

class OrderedItems(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectMaterials Table
    """
    __tablename__ = 'ordered_items'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    active_po_id = Column(String(36), ForeignKey("active_po.id"), nullable=True)
    manufacturer_id = Column(String(36), ForeignKey("manufacturers.id"))
    manufacturer_name = Column(String(100))
    brand_id = Column(String(36), ForeignKey("brands.id"))
    brand_name = Column(String(100))
    project_id = Column(String(36), ForeignKey("projects.id"))
    project_name = Column(String(100))
    project_number = Column(String(100))
    schedule_id =  Column(String(36))
    opening_number =  Column(String(100))
    door_type =  Column(String(100))
    hand =  Column(String(100))
    door_mat =  Column(String(100))
    frame_mat =  Column(String(100))
    ordered_metadata = Column(JSON, default={})
    is_received = Column(Boolean, default=False)
    is_missing = Column(Boolean, default=False)
    is_damaged = Column(Boolean, default=False)
    total_price = Column(Float)
    total_base_price = Column(Float)
    quantity = Column(Float)
    final_price = Column(Float)
    final_base_price = Column(Float)
    component_type = Column(Enum(COMPONENTS))
    part_number = Column(Integer)
    crate_number = Column(Integer)
    required_by_date = Column(Date)
    estimated_delivery_date = Column(Date)
    shipping_initiate_date = Column(Date)
    shipment_date = Column(Date)
    shipped_date = Column(Date)
    estimated_fulfillment_date = Column(Date)
    generated_shipping_label_path = Column(String(255))
    label_file_name = Column(String(255))
    label_file_path = Column(String(255))
    label_content_type = Column(String(50))
    shipment_id = Column(String(50))
    packing_info = Column(String(50))
    shipping_status = Column(Enum(SHIPPING_STATUS))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    active_po = relationship("ActivePo", back_populates="order_items")
    # order_item_docs = relationship("OrderedItemDocs", back_populates="order_item")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "active_po_id": str(self.active_po_id),
            "manufacturer_id": self.manufacturer_id,
            "manufacturer_name": self.manufacturer_name,
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_number": self.project_number,
            "opening_number": self.opening_number,
            "door_type": self.door_type,
            "hand": self.hand,
            "door_mat": self.door_mat,
            "frame_mat": self.frame_mat,
            "ordered_metadata": self.ordered_metadata,
            "total_price": self.total_price,
            "total_base_price": self.total_base_price,
            "quantity": self.quantity,
            "final_price": self.final_price,
            "final_base_price": self.final_base_price,
            "component_type": self.component_type.value,
            "label_file_path": self.label_file_path,
            "label_file_name": self.label_file_name,
            "label_content_type": self.label_content_type,
            "crate_number": self.crate_number,
            "required_by_date": self.required_by_date.strftime("%d/%m/%Y"),
            "estimated_delivery_date": self.estimated_delivery_date.strftime("%d/%m/%Y"),
            "shipping_initiate_date": self.shipping_initiate_date.strftime("%d/%m/%Y"),
            "shipment_date": self.shipment_date.strftime("%d/%m/%Y"),
            "shipped_date": self.shipped_date.strftime("%d/%m/%Y"),
            "estimated_fulfillment_date": self.estimated_fulfillment_date.strftime("%d/%m/%Y"),
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }