"""
This module Represents the table structure/Schema of OpeningChangeStats Table
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
    # JSON,
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


class COMPONENT_TYPE(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'
    OPENING = 'OPENING'


class DISCOUNT_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class SURCHARGE_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    MULTIPLIER = 'MULTIPLIER'

class OpeningChangeStats(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of OpeningChangeStats Table
    """
    __tablename__ = 'opening_change_stats'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(36))
    schedule_id = Column(String(36))
    opening_number = Column(String(100))
    component = Column(Enum(COMPONENT_TYPE), default=COMPONENT_TYPE.OTHER.value)
    short_code = Column(String(250), default=None)
    field_name = Column(String(250))
    take_off_feature_code = Column(String(250))
    schedule_feature_code = Column(String(250))
    take_off_option_code = Column(String(250))
    take_off_value = Column(String(250))
    schedule_option_code = Column(String(250))
    schedule_value = Column(String(250))
    take_off_total_amount = Column(Float, default=0)
    take_off_total_base_amount = Column(Float, default=0)
    take_off_total_sell_amount = Column(Float, default=0)
    take_off_total_extended_sell_amount = Column(Float, default=0)
    take_off_quantity = Column(Float, default=1)
    take_off_final_amount = Column(Float, default=0)
    take_off_final_base_amount = Column(Float, default=0)
    take_off_final_sell_amount = Column(Float, default=0)
    take_off_final_extended_sell_amount = Column(Float, default=0)
    take_off_discount = Column(Float, default=0)
    take_off_discount_type = Column(Enum(DISCOUNT_TYPE))
    take_off_surcharge = Column(Float, default=0)
    take_off_surcharge_type = Column(Enum(SURCHARGE_TYPE))
    take_off_margin = Column(Float, default=0)
    take_off_markup = Column(Float, default=0)
    schedule_total_amount = Column(Float, default=0)
    schedule_total_base_amount = Column(Float, default=0)
    schedule_total_sell_amount = Column(Float, default=0)
    schedule_total_extended_sell_amount = Column(Float, default=0)
    schedule_quantity = Column(Float, default=1)
    schedule_final_amount = Column(Float, default=0)
    schedule_final_base_amount = Column(Float, default=0)
    schedule_final_sell_amount = Column(Float, default=0)
    schedule_final_extended_sell_amount = Column(Float, default=0)
    schedule_discount = Column(Float, default=0)
    schedule_discount_type = Column(Enum(DISCOUNT_TYPE))
    schedule_surcharge = Column(Float, default=0)
    schedule_surcharge_type = Column(Enum(SURCHARGE_TYPE))
    schedule_margin = Column(Float, default=0)
    schedule_markup = Column(Float, default=0)
    is_manual = Column(Boolean, default=False)
    is_adon_field = Column(Boolean, default=False)
    has_price_dependancy = Column(Boolean, default=False)
    part_number = Column(Integer, default=None)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "schedule_id": self.schedule_id,
            "opening_number": self.opening_number,
            "component": self.component,
            "short_code": str(self.short_code),
            "field_name": str(self.field_name),
            "take_off_feature_code": self.take_off_feature_code,
            "schedule_feature_code": self.schedule_feature_code,
            "take_off_option_code": self.take_off_option_code,
            "take_off_value": self.take_off_value,
            "schedule_option_code": self.schedule_option_code,
            "schedule_value": self.schedule_value,
            "take_off_total_amount": self.take_off_total_amount,
            "take_off_total_base_amount": self.take_off_total_base_amount,
            "take_off_total_sell_amount": self.take_off_total_sell_amount,
            "take_off_total_extended_sell_amount": self.take_off_total_extended_sell_amount,
            "take_off_quantity": self.take_off_quantity,
            "take_off_final_amount": self.take_off_final_amount,
            "take_off_final_base_amount": self.take_off_final_base_amount,
            "take_off_final_sell_amount": self.take_off_final_sell_amount,
            "take_off_final_extended_sell_amount": self.take_off_final_extended_sell_amount,
            "take_off_discount": self.take_off_discount,
            "take_off_discount_type": self.take_off_discount_type.value if hasattr(self.take_off_discount_type, 'value') else self.take_off_discount_type,
            "take_off_surcharge": self.take_off_surcharge,
            "take_off_surcharge_type": self.take_off_surcharge_type.value if hasattr(self.take_off_surcharge_type, 'value') else self.take_off_surcharge_type,
            "take_off_margin": self.take_off_margin,
            "take_off_markup": self.take_off_markup,
            "schedule_total_amount": self.schedule_total_amount,
            "schedule_total_base_amount": self.schedule_total_base_amount,
            "schedule_total_sell_amount": self.schedule_total_sell_amount,
            "schedule_total_extended_sell_amount": self.schedule_total_extended_sell_amount,
            "schedule_quantity": self.schedule_quantity,
            "schedule_final_amount": self.schedule_final_amount,
            "schedule_final_base_amount": self.schedule_final_base_amount,
            "schedule_final_sell_amount": self.schedule_final_sell_amount,
            "schedule_final_extended_sell_amount": self.schedule_final_extended_sell_amount,
            "schedule_discount": self.schedule_discount,
            "schedule_discount_type": self.schedule_discount_type.value if hasattr(self.schedule_discount_type, 'value') else self.schedule_discount_type,
            "schedule_surcharge": self.schedule_surcharge,
            "schedule_surcharge_type": self.schedule_surcharge_type.value if hasattr(self.schedule_surcharge_type, 'value') else self.schedule_surcharge_type,
            "schedule_margin": self.schedule_margin,
            "schedule_markup": self.schedule_markup,
            "is_manual": self.is_manual,
            "is_adon_field": self.is_adon_field,
            "has_price_dependancy": self.has_price_dependancy,
            "part_number": self.part_number,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            "updated_by": str(self.updated_by) if self.updated_by else None,
        }