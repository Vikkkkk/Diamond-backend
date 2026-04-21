"""
This module containes all schemas those are related to Notes add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class NoteTemplates(BaseModel):
    """**Summary:**
    This class contains the schema of Note Templates
    """
    id: Optional[str] = Field(None, description="Note Templates ID")
    name: str = Field(None, description="Name of the Note Templates", max_length = "100")
    desc: Optional[str] = Field(None, description="Note Templates description")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="note template creation time")
    created_by: Optional[str] = Field(None, description="note template created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="note template updation time")
    updated_by: Optional[str] = Field(None, description="note template updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="note template deletion time")
    deleted_by: Optional[str] = Field(None, description="note template deleted by")
    
class NoteTemplatesResponse(BaseModel):
    """
    Response model for fetching a NoteTemplates.
    """
    data: List[NoteTemplates]
    status: str

class ProjectTakeOffSheetNotes(BaseModel):
    """**Summary:**
    This class contains the schema of Notes for Project take off sheets
    """
    id: Optional[str] = Field(None, description="ProjectTakeOffSheetNotes ID")
    name: str = Field(None, description="Name of the Note", max_length = "100")
    desc: Optional[str] = Field(None, description="Note description")
    project_take_off_sheet_id: Optional[str] = Field(None, description="project_take_off_sheet ID")
    project_raw_material_id: Optional[str] = Field(None, description="project_raw_material_id ID")
    note_template_id: Optional[str] = Field(None, description="note template ID")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheetCharge creation time")
    created_by: Optional[str] = Field(None, description="TakeOffSheetCharge created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheetCharge updation time")
    updated_by: Optional[str] = Field(None, description="TakeOffSheetCharge updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheetCharge deletion time")
    deleted_by: Optional[str] = Field(None, description="TakeOffSheetCharge deleted by")
    
class ProjectTakeOffSheetNotesResponse(BaseModel):
    """
    Response model for fetching a TakeOffSheet Note.
    """
    data: List[ProjectTakeOffSheetNotes]
    status: str


class ProjectTakeOffSheetNotesDeleteRequest(BaseModel):
    """
    Response model for deleting a list of TakeOffSheet Notes.
    """
    take_off_sheet_note_ids: List[str]

