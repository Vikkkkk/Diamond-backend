from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
from models.adon_opening_fields import ADDON_OPENING_FIELD_TYPE

class ScheduleStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    ORDERED = "ORDERED"
    SHIPPED = "SHIPPED"

class Schedule(BaseModel):
    id: Optional[str] = Field(None, description="ID")
    opening_number: Optional[str]
    area: Optional[str]
    location_1: Optional[str]
    location_2: Optional[str]
    from_to: Optional[Literal["From", "To"]]
    door_qty: Optional[float]
    frame_qty: Optional[float]
    project_id: Optional[str]
    frame_section_file_path: Optional[str]
    frame_section_file_type: Optional[str]
    door_material_code: Optional[str]
    frame_material_code: Optional[str]
    door_type: Optional[str]
    swing: Optional[str]
    is_freezed: Optional[bool] = False
    is_in_change_order: Optional[bool] = False
    has_requested: Optional[bool] = False
    has_ordered: Optional[bool] = False
    has_shipped: Optional[bool] = False
    status: Optional[ScheduleStatus] = None

class ScheduleResponse(BaseModel):
    data: list[Schedule]
    status: str


class ScheduleRequest(BaseModel):
    id: Optional[str] = Field(None, description="schedule ID")
    opening_number: str
    area: str
    location_1: str
    location_2: str
    from_to: str
    door_qty: float
    frame_qty: float
    door_type: str
    swing: str
    door_material_code: str
    frame_material_code: str
    door_type: str
    swing: str


class AdonOpeningFieldCreateSchema(BaseModel):
    name: str
    field_type: Literal["NUMBER", "TEXT", "FILE_UPLOAD"]