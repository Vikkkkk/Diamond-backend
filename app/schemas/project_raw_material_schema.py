"""
This module containes all schemas those are related to project raw material add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ProjectRawMaterial(BaseModel):
    """**Summary:**
    This class contains the schema of each ProjectRawMaterial
    """
    id: Optional[UUID] = Field(None, description="Member ID")
    name: Optional[str] = Field(None, description="Item Number")
    project_id: Optional[bool] = Field(None,description="Code")
    has_installation: Optional[bool] = Field(None, description="Name")
    raw_material_id: Optional[bool] = Field(None, description="Has Installation")
    raw_material_type_id: Optional[bool] = Field(None, description="Sort Order")