"""
This module containes all schemas those are related to hardware group material add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ScheduleHardwarMaterialRequest(BaseModel):
    """**Summary:**
    This class contains the schema of each Hardware Group 
    """

    hardware_materials: dict[str, int] = Field(
            description="Mapping of Opening Hardware Material ID to Quantity"
        )

class ScheduleHardwareMaterial(BaseModel):
    """
    Data model representing a Opening hardware Material.
    """
    id: Optional[str] = Field(None, description="ProjectMaterial ID")
    schedule_opening_hardware_material_id: Optional[str] = Field(None, description="Schedule Opening Hardware material ID")
    name: Optional[str] = Field(None, description="Name of the ProjectMaterial", max_length = "100")
    short_code: Optional[str] = Field(None, description="Project Material short code")
    desc: Optional[str] = Field(None, description="Project Material description")
    series: Optional[str] = Field(None, description="Project Material series")
    total_amount: Optional[float] = Field(None, description="total ammount")
    total_base_amount: Optional[float] = Field(None, description="total base ammount")
    total_sell_amount: Optional[float] = Field(None, description="total extended sell ammount")
    total_extended_sell_amount: Optional[float] = Field(None, description="total sell ammount")
    quantity: Optional[float] = Field(None, description="Material Quantity")
    final_amount: Optional[float] = Field(None, description="final ammount")
    final_base_amount: Optional[float] = Field(None, description="final base ammount")
    final_sell_amount: Optional[float] = Field(None, description="final extended sell ammount")
    final_extended_sell_amount: Optional[float] = Field(None, description="final sell ammount")
    manufacturer_id: Optional[str] = Field(None, description="Manufacturer ID", max_length = "36")
    manufacturer_code: Optional[str] = Field(None, description="Manufacturer Code")
    brand_id: Optional[str] = Field(None, description="Brand ID", max_length = "36")
    brand_code: Optional[str] = Field(None, description="Brand Code")
    project_id: Optional[str] = Field(None, description="Project ID", max_length = "36")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Project Material creation time")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Project Material updation time")


class ScheduleHardwareMaterialReponse(BaseModel):
    """**Summary:**
    This class contains the schema of each Hardware Group 
    """
    status: str
    data: Optional[List[ScheduleHardwareMaterial]] = Field([],description="Schedule Hardware Materials")