"""
This module containes all schemas those are related to TakeOffSheets add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class TakeOffSheets:
    """
    Data model representing a TakeOffSheet.
    """
    id: Optional[str] = Field(None, description="TakeOffSheets ID")
    name: str = Field(None, description="Name of the TakeOffSheets", max_length = "100")
    project_id: str = Field(None, description="Project ID", max_length = "100")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    has_quotation: Optional[bool] = Field(None, description="Has quotation")
    quotation_path: Optional[str] = Field(None, description="Quotation path", max_length = "100")
    created_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheets creation time")
    created_by: Optional[str] = Field(None, description="TakeOffSheets created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheets updation time")
    updated_by: Optional[str] = Field(None, description="TakeOffSheets updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheets deletion time")
    deleted_by: Optional[str] = Field(None, description="TakeOffSheets deleted by")


class TakeOffSheetRequest(BaseModel):
    """
    Request model for creating or updating a TakeOffSheet.
    """
    project_id: str = Field(description="ID of the Project", max_length = "36")
    section_ids: List[str] = Field(description="Section IDs")


class TakeOffSheetSectionAreaRequest(BaseModel):
    """
    Response model for creating or updating a TakeOffSheet.
    """
    project_take_off_sheet_section_id: str = Field(description="Section ID", max_length = "36")
    name: str = Field(description="Name of the Section", max_length = "100")



    

