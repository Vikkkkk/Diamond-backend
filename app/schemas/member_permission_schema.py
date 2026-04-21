"""
This module containes all schemas those are related to permissions add/update/read/delete requests.
"""
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class MemberPermission(BaseModel):
    """**Summary:**
    This class contains the schema of each Member Permission
    """
    id: Optional[UUID] = Field(None, description="Member ID")
    module_id: str = Field(None, description="Module ID")
    member_id: str = Field(None, description="Member ID")
    sub_module_id: str = Field(None, description="Sub-Module ID")
    is_active: Optional[bool] = Field(None,description="Permission is active or not")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Permission creation time")
    created_by: Optional[str] = Field(None, description="Permission created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Permission updation time")
    updated_by: Optional[str] = Field(None, description="Permission updated by")

