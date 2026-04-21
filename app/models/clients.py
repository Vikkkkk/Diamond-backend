"""
This module Represents the table structure/Schema of Clients Table
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    # Float,
    String,
    DateTime,
    Text,
    ForeignKey,
    # PrimaryKeyConstraint,
    # JSON,
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import pytz
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class Clients(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Clients Table
    """
    __tablename__ = 'clients'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    name = Column(String(100))
    contact_name = Column(String(100))
    email = Column(String(100), unique=True)
    phone = Column(String(20), unique=True)
    fax = Column(String(20), unique=True)
    website = Column(String(100))
    street_address = Column(String(255))
    province = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    note = Column(Text)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Relations/associations
    client_projects = relationship("ClientProjects", back_populates="client")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "fax": self.fax,
            "website": self.website,
            "street_address": self.street_address,
            "province": self.province,
            "country": self.country,
            "postal_code": self.postal_code,
            "note": self.note,
            # "is_active": self.is_active,
            # "is_deleted": self.is_deleted,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            # "deleted_at": self.deleted_at if self.deleted_at is None else self.deleted_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "deleted_by": str(self.deleted_by) if self.deleted_by else None,
        }