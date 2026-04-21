"""
This module containes all schemas those are related to raw material type add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class RawMaterialType(BaseModel):
    """**Summary:**
    This class contains the schema of each RawMaterialType
    """
    id: Optional[UUID] = Field(None, description="Member ID")
    item_number: Optional[str] = Field(None, description="Item Number")
    code: Optional[bool] = Field(None,description="Code")
    name: Optional[bool] = Field(None, description="Name")
    has_installation: Optional[bool] = Field(None, description="Has Installation")
    sort_order: Optional[bool] = Field(None, description="Sort Order")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Raw material type creation time")
    created_by: Optional[str] = Field(None, description="Raw material type created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Raw material type updation time")
    updated_by: Optional[str] = Field(None, description="Raw material type updated by")


