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


class ActivePo(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectMaterials Table
    """
    __tablename__ = 'active_po'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    po_number = Column(String(255), unique=True)
    company_address = Column(Text)
    sold_to = Column(Text)
    ship_to = Column(Text)
    order_contact = Column(String(255))
    required_by_date = Column(Date)
    order_contact_email = Column(String(255))
    delivery_contact_phone = Column(String(50))
    ordered_date = Column(Date)
    material = Column(String(255))
    quote = Column(String(255))
    scheduled_ship_date = Column(Date)
    customer = Column(String(255))
    description = Column(Text)
    po_acknowledgement = Column(String(255))
    ship_via = Column(String(255))
    ship_instructions = Column(Text)
    order_type = Column(String(255))
    order_type_description = Column(Text)
    carrier = Column(String(255))
    service_center = Column(String(255))
    transfer_point_ship_via = Column(String(255))
    transfer_point_carrier = Column(String(255))
    bundling_code = Column(String(50))
    prepaid_collect_code_id = Column(String(255))
    is_job_site = Column(Boolean, default=False)
    ordered_item_quantity = Column(Integer)
    final_price = Column(Float)
    is_received = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    order_items = relationship("OrderedItems", back_populates="active_po")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "po_number": self.po_number,
            "company_address": self.company_address,
            "sold_to": self.sold_to,
            "ship_to": self.ship_to,
            "order_contact": self.order_contact,
            "required_by_date": self.required_by_date.strftime("%d/%m/%Y"),
            "order_contact_email": self.order_contact_email,
            "delivery_contact_phone": self.delivery_contact_phone,
            "ordered_date": self.ordered_date.strftime("%d/%m/%Y"),
            "material": self.material,
            "quote": self.quote,
            "scheduled_ship_date":self.scheduled_ship_date.strftime("%d/%m/%Y"),
            "customer": self.customer,
            "description": self.description,
            "po_acknowledgement": self.po_acknowledgement,
            "ship_via": self.ship_via,
            "ship_instructions": self.ship_instructions,
            "order_type": self.order_type,
            "order_type_description": self.order_type_description,
            "carrier": self.carrier,
            "service_center": self.service_center,
            "transfer_point_ship_via": self.transfer_point_ship_via,
            "transfer_point_carrier": self.transfer_point_carrier,
            "bundling_code": self.bundling_code,
            "prepaid_collect_code_id": self.prepaid_collect_code_id,
            "is_job_site": self.is_job_site,
            "ordered_item_quantity": self.ordered_item_quantity,
            "final_price": str(self.final_price),
            "is_received": self.is_received,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }
