"""
This module Represents the table structure/Schema of ScheduleData Table
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
    Enum,
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
import enum
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))


class ADDON_OPENING_FIELD_TYPE(enum.Enum):
    NUMBER = 'NUMBER'
    TEXT = 'TEXT'
    DROPDOWN = 'DROPDOWN'


class DISCOUNT_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class SURCHARGE_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'


class COMPONENT_TYPE(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'
    OPENING = 'OPENING'


class ScheduleData(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ScheduleData Table
    """
    __tablename__ = 'schedule_data'


    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    version = Column(String(250), default='v0')
    desc = Column(Text, default=None)
    value = Column(Text, default=None)
    component = Column(Enum(COMPONENT_TYPE), default=COMPONENT_TYPE.OTHER.value)
    part_number = Column(Integer, default=None)
    feature_code = Column(String(250))
    option_code = Column(String(250))
    feature_data = Column(JSON, default=None)
    price_data = Column(JSON, default=None)
    additional_data = Column(JSON, default=None)
    total_amount = Column(Float, default=0)
    total_sell_amount = Column(Float, default=0)
    total_base_amount = Column(Float, default=0)
    total_extended_sell_amount = Column(Float, default=0)
    quantity = Column(Float, default=1)
    final_amount = Column(Float, default=0)
    final_sell_amount = Column(Float, default=0)
    final_base_amount = Column(Float, default=0)
    final_extended_sell_amount = Column(Float, default=0)
    markup = Column(Float, default=0)
    margin = Column(Float, default=0)
    is_basic_discount = Column(Boolean, default=True)
    discount = Column(Float, default=0)
    discount_type = Column(Enum(DISCOUNT_TYPE), default=DISCOUNT_TYPE.PERCENTAGE.value)
    surcharge = Column(Float, default=0)
    surcharge_type = Column(Enum(SURCHARGE_TYPE), default=SURCHARGE_TYPE.PERCENTAGE.value)
    adon_field_id = Column(String(36), ForeignKey("adon_opening_fields.id"))
    adon_field_option_id = Column(String(36), ForeignKey("adon_opening_field_options.id"))
    schedule_id = Column(String(36), ForeignKey("schedules.id"))
    latest_data = Column(Boolean, default=True)
    has_ordered = Column(Boolean, default=False)
    has_shipped = Column(Boolean, default=False)
    is_manual = Column(Boolean, default=False)
    is_table_data = Column(Boolean, default=False)
    is_adon_field = Column(Boolean, default=False)
    has_price_dependancy = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    adon_field_option = relationship("AdonOpeningFieldOptions", back_populates="schedule_data")
    adon_field = relationship("AdonOpeningFields", back_populates="schedule_data")
    schedule = relationship("Schedules", back_populates="schedule_data")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "version": self.version,
            "desc": self.desc,
            "value": self.value,
            "component": self.component if self.component and isinstance(self.component, str) else self.component.value if self.component else None,
            "part_number": self.part_number,
            "feature_code": self.feature_code,
            "option_code": self.option_code,
            "feature_data": self.feature_data,
            "price_data": self.price_data,
            "additional_data": self.additional_data,
            "total_amount": self.total_amount,
            "total_sell_amount": self.total_sell_amount,
            "total_base_amount": self.total_base_amount,
            "total_extended_sell_amount": self.total_extended_sell_amount,
            "quantity": self.quantity,
            "final_amount": self.final_amount,
            "final_sell_amount": self.final_sell_amount,
            "final_base_amount": self.final_base_amount,
            "final_extended_sell_amount": self.final_extended_sell_amount,
            "markup": self.markup,
            "margin": self.margin,
            "is_basic_discount": self.is_basic_discount,
            "discount": self.discount,
            "surcharge": self.surcharge,
            "discount_type": self.discount_type.value if hasattr(self.discount_type, 'value') else self.discount_type,
            "surcharge_type": self.surcharge_type.value if hasattr(self.surcharge_type, 'value') else self.surcharge_type,
            "adon_field_id": self.adon_field_id,
            "adon_field_option_id": self.adon_field_option_id,
            "schedule_id": self.schedule_id,
            "is_manual": self.is_manual,
            "has_ordered": self.has_ordered,
            "has_shipped": self.has_shipped,
            "latest_data": self.latest_data,
            "is_table_data": self.is_table_data,
            "is_adon_field": self.is_adon_field,
            "has_price_dependancy": self.has_price_dependancy,
            
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
        }