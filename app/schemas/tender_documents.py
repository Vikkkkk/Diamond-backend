"""
This module containes all schemas those are related to Tender Documents read requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class TenderDocument(BaseModel):
    """**Summary:**
    This class contains the schema of each Tender documents
    """
    id: Optional[str] = Field(None, description="ID")
    file_path: Optional[str] = Field(None, description="File path")
    file_name: Optional[str] = Field(None, description="Name of the file", max_length = "100")
    is_active: Optional[bool] = Field(None, description="Is active")
    created_at: Optional[Union[str, datetime]] = Field(None, description="tender document creation time")
    created_by: Optional[str] = Field(None, description="tender document created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="tender document updation time")
    updated_by: Optional[str] = Field(None, description="tender document updated by")
    project_id: Optional[str] = Field(None, description="Project ID")
