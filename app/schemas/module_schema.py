"""
This module containes all schemas those are related to modules add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class Module(BaseModel):
    """**Summary:**
    This class contains the schema of each Module
    """
    id: Optional[str] = Field(None, description="Module ID")
    name: str = Field(None, description="Module Name")
    label: str = Field(None, description="Module Label")
    sort_order: int = Field(None, description="Sort Order")
    # is_active: Optional[bool] = Field(None,description="Module is active or not")
    # is_deleted: Optional[bool] = Field(None, description="Is delete")
    # created_at: Optional[Union[str, datetime]] = Field(None, description="Module creation time")
    # created_by: Optional[str] = Field(None, description="Module created by")
    # updated_at: Optional[Union[str, datetime]] = Field(None, description="Module updation time")
    # updated_by: Optional[str] = Field(None, description="Module updated by")
    # deleted_at: Optional[Union[str, datetime]] = Field(None, description="Module deletion time")
    # deleted_by: Optional[str] = Field(None, description="Module deleted by")

class ModulesResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of multiple Module fetch request.
    """
    data: List[Module]
    status: str

