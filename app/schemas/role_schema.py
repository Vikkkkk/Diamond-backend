"""
This module containes all schemas those are related to Brands add/update/read/delete requests.
"""
from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field
from datetime import datetime



class RoleSchema(BaseModel):
    id: str = Field(...,description="Role ID")
    name: str = Field(..., description="name of the role", max_length=100)
    is_active: Optional[bool] = Field(None,description="Role is active or not")