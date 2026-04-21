from typing import List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class Manufacturer(BaseModel):
    id: Optional[str] = Field(None, description="Manufacturer id")
    code: str = Field(None, description="Manufacturer code")
    name: str = Field(None, description="Name of the manufacturer")
    desc: Optional[str] = Field(None, description="Description of the manufacturer")
    discount_percentage: Optional[float] = Field(None, description="Discount Percentage Provided")
    is_door_provided: Optional[bool] = Field(False, description="Whether DOOR provided")
    is_frame_provided: Optional[bool] = Field(False, description="Whether FRAME provided")
    is_hardware_provided: Optional[bool] = Field(False, description="Whether HARDWARE provided")
    is_active: Optional[bool] = Field(True, description="Whether the manufacturer is active")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Manufacturer creation time")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Manufacturer updation time")