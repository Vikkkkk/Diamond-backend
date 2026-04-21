"""
This module containes all schemas those are related to Brands add/update/read/delete requests.
"""
from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field
from datetime import datetime



class BrandRequest(BaseModel):
    """
    Data model representing a Brandl.
    """
    id: Optional[str] = Field(None, description="Brand ID")
    code: Optional[str] = Field(None, description="code of the Brand", max_length = "100")
    name: Optional[str] = Field(None, description="Name of the Brand", max_length = "100")
    desc: Optional[str] = Field(None, description="Description of the Brand")
    manufacturer_id: Optional[str] = Field(None, description="Manufacturer ID", max_length = "36")
    discount_percentage: Optional[float] = Field(None, description="discount_percentage")
    is_frame_provided: Optional[bool] = Field(False, description="Provide frame or not")
    is_door_provided: Optional[bool] = Field(False, description="Provide door or not")
    is_hardware_provided: Optional[bool] = Field(False, description="Provide hardware or not")
    is_active: Optional[bool] = Field(True, description="Is active")
    is_deleted: Optional[bool] = Field(False, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Brand creation time")
    created_by: Optional[str] = Field(None, description="Brand created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Brand updation time")
    updated_by: Optional[str] = Field(None, description="Brand updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Brand deletion time")
    deleted_by: Optional[str] = Field(None, description="Brand deleted by")
