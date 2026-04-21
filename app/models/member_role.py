"""
This module Represents the table structure/Schema of MemberRole Table
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

class MemberRole(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of MemberRole Table
    """
    __tablename__ = 'member_role'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    role_id = Column(String(36), ForeignKey("roles.id"))
    member_id = Column(String(36), ForeignKey("members.id"))
    active_role = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))

    # Relations/associations
    role = relationship('Roles', back_populates='member_roles')
    member = relationship('Members', back_populates='member_roles')
    project_members = relationship('ProjectMembers', back_populates='project_member_roles')

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "role_id": self.role_id,
            "member_id": self.member_id,
            "active_role": self.active_role,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }