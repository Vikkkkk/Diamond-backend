"""
This module Represents the table structure/Schema of Project Members Table
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

class ProjectMembers(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Project Members Table
    """
    __tablename__ = 'project_members'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    member_role_id = Column(String(36), ForeignKey("member_role.id"))
    project_id = Column(String(36), ForeignKey("projects.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    
    # Relations/associations
    project_member_roles = relationship('MemberRole', back_populates='project_members')
    project = relationship('Projects', back_populates="project_members")

    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """
        return {
            "id": str(self.id),
            "is_active": self.is_active,
            "member_role_id": self.member_role_id,
            "project_id": str(self.project_id) if self.project_id else self.project_id,
            # "is_active": self.is_active,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
        }