
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Boolean, Text, Enum, Integer, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import Base
from utils.common import generate_uuid
import enum



class CoChangeStatsComponentEnum(enum.Enum):
    MULTIPLIER = 'MULTIPLIER'
    PERCENTAGE = 'PERCENTAGE'

class ProjectMaterialsDiscountTypeEnum(enum.Enum):
    MULTIPLIER = 'MULTIPLIER'
    PERCENTAGE = 'PERCENTAGE'

class ProjectMaterialsSurchargeTypeEnum(enum.Enum):
    MULTIPLIER = 'MULTIPLIER'
    PERCENTAGE = 'PERCENTAGE'


class CoChangeStats(Base):
    __tablename__ = 'co_change_stats'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36),default=None)
    schedule_id = Column(String(36), ForeignKey('schedules.id'))
    opening_number = Column(String(100))
    component = Column(Enum(CoChangeStatsComponentEnum))
    short_code = Column(String(100))
    field_name = Column(String(100))
    curr_schedule_feature_code = Column(String(255),default=None)
    co_schedule_feature_code = Column(String(255),default=None)
    curr_schedule_option_code = Column(String(255),default=None)
    co_schedule_option_code = Column(String(255),default=None)
    curr_schedule_value = Column(String(255),default=None)
    co_schedule_value = Column(String(255),default=None)
    curr_schedule_total_amount = Column(Float,default=None)
    curr_schedule_total_base_amount = Column(Float,default=None)
    curr_schedule_total_sell_amount = Column(Float,default=None)
    curr_schedule_total_extended_sell_amount = Column(Float,default=None)
    curr_schedule_quantity = Column(Float,default=None)
    curr_schedule_final_amount = Column(Float,default=None)
    curr_schedule_final_base_amount = Column(Float,default=None)
    curr_schedule_final_sell_amount = Column(Float,default=None)
    curr_schedule_final_extended_sell_amount = Column(Float,default=None)
    curr_schedule_discount = Column(Float, default=0)
    curr_schedule_discount_type = Column(Enum(ProjectMaterialsDiscountTypeEnum),default=None)
    curr_schedule_surcharge = Column(Float, default=0)
    curr_schedule_surcharge_type = Column(Enum(ProjectMaterialsSurchargeTypeEnum),default=None)
    curr_schedule_margin = Column(Float, default=0)
    curr_schedule_markup = Column(Float, default=0)
    co_schedule_total_amount = Column(Float,default=None)
    co_schedule_total_base_amount = Column(Float,default=None)
    co_schedule_total_sell_amount = Column(Float,default=None)
    co_schedule_total_extended_sell_amount = Column(Float,default=None)
    co_schedule_quantity = Column(Float,default=None)
    co_schedule_final_amount = Column(Float,default=None)
    co_schedule_final_base_amount = Column(Float,default=None)
    co_schedule_final_sell_amount = Column(Float,default=None)
    co_schedule_final_extended_sell_amount = Column(Float,default=None)
    co_schedule_discount = Column(Float, default=0)
    co_schedule_discount_type = Column(Enum(ProjectMaterialsDiscountTypeEnum),default=None)
    co_schedule_surcharge = Column(Float, default=0)
    co_schedule_surcharge_type = Column(Enum(ProjectMaterialsSurchargeTypeEnum))
    co_schedule_margin = Column(Float, default=0)
    co_schedule_markup = Column(Float, default=0)
    is_manual = Column(Boolean, default=False)
    is_adon_field = Column(Boolean, default=False)
    has_price_dependancy = Column(Boolean, default=False)
    part_number = Column(Integer,default=None)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    schedule = relationship("Schedules", back_populates="co_change_stats")


    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the CO change stats.
        """
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "schedule_id": self.schedule_id,
            "opening_number": self.opening_number,
            "component": self.component.name if self.component else None,
            "short_code": self.short_code,
            "field_name": self.field_name,
            "curr_schedule_feature_code": self.curr_schedule_feature_code,
            "co_schedule_feature_code": self.co_schedule_feature_code,
            "curr_schedule_option_code": self.curr_schedule_option_code,
            "co_schedule_option_code": self.co_schedule_option_code,
            "curr_schedule_value": self.curr_schedule_value,
            "co_schedule_value": self.co_schedule_value,
            "curr_schedule_total_amount": self.curr_schedule_total_amount,
            "curr_schedule_total_base_amount": self.curr_schedule_total_base_amount,
            "curr_schedule_total_sell_amount": self.curr_schedule_total_sell_amount,
            "curr_schedule_total_extended_sell_amount": self.curr_schedule_total_extended_sell_amount,
            "curr_schedule_quantity": self.curr_schedule_quantity,
            "curr_schedule_final_amount": self.curr_schedule_final_amount,
            "curr_schedule_final_base_amount": self.curr_schedule_final_base_amount,
            "curr_schedule_final_sell_amount": self.curr_schedule_final_sell_amount,
            "curr_schedule_final_extended_sell_amount": self.curr_schedule_final_extended_sell_amount,
            "curr_schedule_discount": self.curr_schedule_discount,
            "curr_schedule_discount_type": self.curr_schedule_discount_type.name if self.curr_schedule_discount_type else None,
            "curr_schedule_surcharge": self.curr_schedule_surcharge,
            "curr_schedule_surcharge_type": self.curr_schedule_surcharge_type.name if self.curr_schedule_surcharge_type else None,
            "curr_schedule_margin": self.curr_schedule_margin,
            "curr_schedule_markup": self.curr_schedule_markup,
            "co_schedule_total_amount": self.co_schedule_total_amount,
            "co_schedule_total_base_amount": self.co_schedule_total_base_amount,
            "co_schedule_total_sell_amount": self.co_schedule_total_sell_amount,
            "co_schedule_total_extended_sell_amount": self.co_schedule_total_extended_sell_amount,
            "co_schedule_quantity": self.co_schedule_quantity,
            "co_schedule_final_amount": self.co_schedule_final_amount,
            "co_schedule_final_base_amount": self.co_schedule_final_base_amount,
            "co_schedule_final_sell_amount": self.co_schedule_final_sell_amount,
            "co_schedule_final_extended_sell_amount": self.co_schedule_final_extended_sell_amount,
            "co_schedule_discount": self.co_schedule_discount,
            "co_schedule_discount_type": self.co_schedule_discount_type.name if self.co_schedule_discount_type else None,
            "co_schedule_surcharge": self.co_schedule_surcharge,
            "co_schedule_surcharge_type": self.co_schedule_surcharge_type.name if self.co_schedule_surcharge_type else None,
            "co_schedule_margin": self.co_schedule_margin,
            "co_schedule_markup": self.co_schedule_markup,
            "is_manual": self.is_manual,
            "is_adon_field": self.is_adon_field,
            "has_price_dependancy": self.has_price_dependancy,
            "part_number": self.part_number,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "updated_by": self.updated_by,
        }
