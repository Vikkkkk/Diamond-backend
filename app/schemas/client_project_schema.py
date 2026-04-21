"""
This module containes all schemas those are related to Client add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ClientProjects(BaseModel):
    """**Summary:**
    This class contains the schema of each Client Projects
    """
    id: Optional[str] = Field(None, description="Client Project ID")
    client_id: Optional[str] = Field(None, description="Client ID")
    project_id: Optional[str] = Field(None, description="Project ID")
    is_active: Optional[bool] = Field(None, description="Is active")
    bid_success: Optional[bool] = Field(None, description="Is bid success")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Client creation time")
    created_by: Optional[str] = Field(None, description="Client created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Client updation time")
    updated_by: Optional[str] = Field(None, description="Client updated by")