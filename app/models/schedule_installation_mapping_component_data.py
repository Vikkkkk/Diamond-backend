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


class STATUS(enum.Enum):
    PENDING = 'PENDING'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'


class COMPONENT(enum.Enum):
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'



class ScheduleInstallationMappingComponentData(Base):
    """**Summary:**
    Represents the preparation data for installation mappings.
    """
    __tablename__ = 'schedule_installation_mapping_component_data'

    id = Column(String(36), default=generate_uuid, primary_key=True, unique=True)
    project_id = Column(String(36))
    schedule_id = Column(String(36))
    base_feature = Column(JSON, default={})
    adon_feature = Column(JSON, default={})
    schedule_installation_mapping_id = Column(String(36), ForeignKey('schedule_installation_mapping.id',ondelete="CASCADE"))
    schedule_opening_hardware_material_id = Column(String(36), ForeignKey('schedule_opening_hardware_materials.id'))
    status = Column(Enum(STATUS), default=STATUS.PENDING.value)
    component = Column(Enum(COMPONENT), default=None)
    name = Column(String(100))
    desc = Column(Text)
    part_number = Column(Integer, default=None)
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    schedule_installation_mapping = relationship("ScheduleInstallationMapping", back_populates="schedule_installation_preps")
    schedule_opening_hardwares = relationship("ScheduleOpeningHardwareMaterials", back_populates="schedule_component_data")

    @property
    def to_dict(self):
        """**Summary:**
        Returns a dictionary representation of the installation prep data.
        """
        return {
            "id": str(self.id),
            "project_id": self.project_id,
            "schedule_id": self.schedule_id,
            "base_feature": self.base_feature,
            "adon_feature": self.adon_feature,
            "name": self.name,
            "desc": self.desc,
            "part_number": self.part_number,
            "schedule_installation_mapping_id": self.schedule_installation_mapping_id,
            "schedule_opening_hardware_material_id": self.schedule_opening_hardware_material_id,
            "status": self.status.value if self.status else None,
            "component": self.component.value if self.component else None,
            # "created_by": self.created_by,
            # "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S") if self.created_at else None,
            # "updated_at": self.updated_at.strftime("%d/%m/%Y %H:%M:%S") if self.updated_at else None,
        }

