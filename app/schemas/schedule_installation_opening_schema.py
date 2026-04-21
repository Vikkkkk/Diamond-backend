from typing import Optional, Union, Dict
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from enum import Enum

class STATUS(str, Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    FAILED = 'FAILED'
    SUCCESS = 'SUCCESS'


class ScheduleInstallationMappingSchema(BaseModel):
    """**Summary:**
    Schema for Schedule Installation Mapping.
    """
    schedule_id: Optional[str] = Field(..., description="Schedule ID (foreign key)")
    schedule_installation_plan_doc_id: Optional[str] = Field(None, description="Installation Plan Document ID (foreign key)")
    coordinate_data: Optional[Dict] = Field(..., description="Coordinate Data as JSON")
    # status: Optional[STATUS] = Field(default=STATUS.PENDING, description="Status of the mapping")



class ScheduleInstallationCommentBase(BaseModel):
    schedule_installation_mapping_id: str = Field(..., description="Schedule Installation Mapping ID")
    comment: str = Field(..., description="Comment text")