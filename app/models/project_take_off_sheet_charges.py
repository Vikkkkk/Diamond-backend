"""
This module Represents the table structure/Schema of ProjectTakeOffSheetCharges Table
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
    # PrimaryKeyConstraint,
    # JSON,
    Enum,
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


class MULTIPLIER_TYPE(enum.Enum):
    PERCENTAGE = 'PERCENTAGE'
    FLAT = 'FLAT'
    MULTIPLIER = 'MULTIPLIER'


class ProjectTakeOffSheetCharges(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of ProjectTakeOffSheetCharges Table
    """
    __tablename__ = 'project_take_off_sheet_charges'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(255))
    desc = Column(String(255))
    project_take_off_sheet_id = Column(String(36), default=None)
    charge_type = Column(String(36))
    amount = Column(Float)
    multiplier_type = Column(Enum(MULTIPLIER_TYPE))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "desc": self.desc,
            "project_take_off_sheet_id": str(self.project_take_off_sheet_id) if self.project_take_off_sheet_id else None,
            "charge_type": self.charge_type,
            "amount": self.amount,
            "multiplier_type": self.multiplier_type,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }