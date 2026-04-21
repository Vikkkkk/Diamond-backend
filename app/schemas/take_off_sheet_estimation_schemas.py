from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Optional
from uuid import UUID
from models.project_materials import SURCHARGE_TYPE

class TabType(Enum):
    MARGIN = "MARGIN"
    MARKUP = "MARKUP"


class EstimationBreakdown(BaseModel):
    tab_type: TabType = Field(None, description="Tab Type")
    data: Dict[str, float] = Field(None, description="Key-value pairs, where the key represents the raw_material.code and values represent percentages")

class EstimationDiscount(BaseModel):
    raw_material_id: Optional[UUID] = Field(None, description="Raw Material ID")
    manufacturer_id: Optional[UUID] = Field(None, description="Manufacturer ID")
    brand_id: Optional[UUID] = Field(None, description="Brand ID")
    project_id: Optional[UUID] = Field(None, description="Project ID")


class SurchargeData(BaseModel):
    surcharge_type: SURCHARGE_TYPE = Field(None, description="Surcharge Type")
    surcharge: float = Field(None, description="Surcharge Amount")
class EstimationSurcharge(BaseModel):
    data: Dict[str, SurchargeData] = Field(None, description="Key-value pairs, where the key represents the raw_material.code and values represent percentages")


