"""
This module Represents the table structure/Schema of Projects Table
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
    Enum,
    # PrimaryKeyConstraint,
    # JSON,
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from models import engine, sessionLocal, Base
from utils.common import generate_uuid
import enum
import pytz
import os
from dotenv import load_dotenv
load_dotenv()
# timezone = pytz.timezone(os.getenv("APP_TIMEZONE"))

class Priority(enum.Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1

class Projects(Base):
    """**Summary:**
    This model class Represents the table structure/Schema of Projects Table
    """
    __tablename__ = 'projects'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_code = Column(String(100))
    name = Column(String(100))
    quotation_due_date = Column(DateTime(timezone=True))
    start_date = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    quotation_number = Column(String(100))
    has_quotation = Column(Boolean, default=False)
    street_address = Column(String(255))
    province = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    priority = Column(Integer, default=Priority.LOW.value)
    note = Column(Text)
    current_project_status = Column(String(20))
    current_bid_status = Column(String(20))
    is_estimation = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_by = Column(String(36))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(36))
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(36))

    # Relations/associations
    project_clients = relationship("ClientProjects", back_populates="project")
    tender_documents = relationship("TenderDocuments", back_populates="project")
    project_members = relationship("ProjectMembers", back_populates="project")
    project_logs = relationship("ProjectStatusLogs", back_populates="project")
    take_off_sheet = relationship('ProjectTakeOffSheets', back_populates='project')
    project_opening_schedules = relationship("OpeningSchedules", back_populates="project")
    project_materials = relationship("ProjectMaterials", back_populates="project")
    project_hardware_groups = relationship("HardwareGroups", back_populates="project")
    project_raw_materials = relationship("ProjectRawMaterials", back_populates="project")
    tasks = relationship("ProjectTask", back_populates="project")
    project_opening_hardware_materials = relationship("OpeningHardwareMaterials", back_populates="project")
    project_opening_door_frame_materials = relationship("OpeningDoorFrameMaterials", back_populates="project")
    door_frame_raw_material_sections = relationship("DoorFrameRawMaterialSections", back_populates="project")


    @property
    def to_dict(self):
        """**Summary:**
        This method returns table record as a dictionary
        """

        def format_datetime(value):
            return value.strftime("%Y-%m-%dT%H:%M:%S") if value else None
        
        return {
            "id": str(self.id),
            "project_code": self.project_code,
            "name": self.name,
            "quotation_due_date": format_datetime(self.quotation_due_date),
            "start_date": format_datetime(self.start_date),
            "due_date": format_datetime(self.due_date),
            "quotation_number": self.quotation_number,
            "has_quotation": self.has_quotation,
            "street_address": self.street_address,
            "province": self.province,
            "country": self.country,
            "postal_code": self.postal_code,
            "priority": Priority(self.priority).name if self.priority else None,
            "note": self.note,
            "current_project_status": self.current_project_status,
            "current_bid_status": self.current_bid_status,
            "is_estimation": self.is_estimation
            # "is_active": self.is_active,
            # "is_deleted": self.is_deleted,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "created_by": str(self.created_by) if self.created_by else None,
            # "updated_at": self.updated_at if self.updated_at is None else self.updated_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "updated_by": str(self.updated_by) if self.updated_by else None,
            # "deleted_at": self.deleted_at if self.deleted_at is None else self.deleted_at.strftime("%d/%m/%Y %H:%M:%S"),
            # "deleted_by": str(self.deleted_by) if self.deleted_by else None,
        }