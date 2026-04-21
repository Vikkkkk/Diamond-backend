"""
This module containes all schemas those are related to sub modules add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class SubModule(BaseModel):
    """**Summary:**
    This class contains the schema of each SUb-Module
    """
    id: Optional[UUID] = Field(None, description="Member ID")
    name: str = Field(None, description="Sub-Module Name")
    label: str = Field(None, description="Sub-Module Label")
    module_id: Optional[str] = Field(None, description="Module ID")
    # is_active: Optional[bool] = Field(None,description="sub module is active or not")
    # is_deleted: Optional[bool] = Field(None, description="Is delete")
    sort_order: int = Field(None, description="Sort Order")
    is_read: Optional[bool] = Field(None, description="Is read")
    is_write: Optional[bool] = Field(None, description="Is write")
    is_delete: Optional[bool] = Field(None, description="Is delete")
    allowed_roles: Optional[List[str]] = Field(None, description="Allowed Roles")
    # created_at: Optional[Union[str, datetime]] = Field(None, description="sub module creation time")
    # created_by: Optional[str] = Field(None, description="sub module created by")
    # updated_at: Optional[Union[str, datetime]] = Field(None, description="sub module updation time")
    # updated_by: Optional[str] = Field(None, description="sub module updated by")
    # deleted_at: Optional[Union[str, datetime]] = Field(None, description="sub module deletion time")
    # deleted_by: Optional[str] = Field(None, description="sub module deleted by")


class SubModulesResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of multiple sub module fetch request.
    """
    data: List[SubModule]
    status: str

