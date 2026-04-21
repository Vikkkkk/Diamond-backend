"""
This module containes all schemas those are related to hardware gropu add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class HardwareGroup(BaseModel):
    """**Summary:**
    This class contains the schema of each Hardware Group 
    """
    name: str = Field(None, description="Name of the group", max_length=100)
    project_id: str = Field(description="Project ID", max_length=36)


class AssignToOpenings(BaseModel):
    project_take_off_sheet_section_area_item_id: List[str] = Field(description="List of Area Item IDs")