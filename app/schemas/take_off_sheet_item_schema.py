"""
This module containes all schemas those are related to TakeOffSheets add/update/read/delete requests.
"""
from typing import List, Optional, Union, Dict, Literal
from pydantic import BaseModel, Field, model_validator
from uuid import UUID
from datetime import datetime


class TakeOffSheetItem(BaseModel):
    """
    Data model representing a TakeOffSheetItems.
    """
    id: Optional[str] = Field(None, description="TakeOffSheetItems ID")
    location_1: str = Field(None, description="location_1 of the TakeOffSheetItem", max_length = "100")
    location_2: str = Field(None, description="location_2 of the TakeOffSheetItem", max_length = "100")
    from_to: Optional[Literal["From", "To"]] = Field("To", description="from_to of the TakeOffSheetItem")
    opening_number: Optional[str] = Field(None, description="TakeOffSheet item opening number")
    desc: Optional[str] = Field(None, description="TakeOffSheet item description")
    total_amount: Optional[float] = Field(None, description="total ammount")
    quantity: Optional[float] = Field(None, description="quantity")
    door_width: Optional[str] = Field(None, description="door_width")
    door_height: Optional[str] = Field(None, description="door_height")
    door_raw_material_type: Optional[str] = Field(None, description="door_raw_material_type")
    frame_raw_material_type: Optional[str] = Field(None, description="frame_raw_material_type")
    adon_fields: Optional[Union[Dict,List[Dict]]] = Field(None, description="adon_fields")
    final_amount: Optional[float] = Field(None, description="final ammount (total * quantity)")
    project_take_off_sheet_id: Optional[str] = Field(None, description="project take off sheet ID", max_length = "36")
    project_take_off_sheet_section_id: Optional[str] = Field(None, description="project take off sheet section ID", max_length = "36")
    project_take_off_sheet_section_area_id: Optional[str] = Field(None, description="project take off sheet section area ID", max_length = "36")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheets creation time")
    created_by: Optional[str] = Field(None, description="TakeOffSheets created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheets updation time")
    updated_by: Optional[str] = Field(None, description="TakeOffSheets updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheets deletion time")
    deleted_by: Optional[str] = Field(None, description="TakeOffSheets deleted by")
    is_batch_insert: Optional[bool] = Field(None, description="Is batch insert")
    batch_insert_quantity: Optional[int] = Field(None, description="Batch insert quantity")


    @model_validator(mode='after')
    def validate_batch_insert_fields(self):
        if self.is_batch_insert and self.batch_insert_quantity is None:
            raise ValueError("Batch quantity is required when is_batch_insert is True")
        if self.is_batch_insert and self.batch_insert_quantity <= 0:
            raise ValueError("Batch quantity must be greater than 0")
        if self.is_batch_insert and self.batch_insert_quantity > 50:
            raise ValueError("Batch quantity must be less than or equal to 50")
        
        return self



class TakeOffSheetCloneRequest(BaseModel):
    opening_number: str = Field(description="TakeOffSheet item opening number")
    project_take_off_sheet_section_id: Optional[str] = Field(None, description="project take off sheet section ID", max_length = "36")
    project_take_off_sheet_section_area_id: Optional[str] = Field(None, description="project take off sheet section area ID", max_length = "36")


class TakeOffSheetItemResponse(BaseModel):
    """
    Request model for fetching a TakeOffSheet Item.
    """
    data: List[TakeOffSheetItem]
    status: str





    

