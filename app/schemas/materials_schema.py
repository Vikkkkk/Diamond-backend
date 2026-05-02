"""
This module containes all schemas those are related to TakeOffSheets add/update/read/delete requests.
"""
from enum import Enum
from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field, model_validator
from uuid import UUID
from datetime import datetime


class MaterialType(str, Enum):
    """**Summary:**
    This class contains the schema of ProjectMaterial's material types
    """
    HARDWARE = 'HARDWARE'
    FRAME = 'FRAME'
    DOOR = 'DOOR'
    OTHER = 'OTHER'

class SelectedUnit(str, Enum):
    """**Summary:**
    This class contains the schema of ProjectMaterial's selected unit
    """
    MM = 'MM'
    INCH = 'INCH'


class HardwareProductCategory(BaseModel):
    """
    Request model for assigining a Project Material Item.
    """
    id: Optional[str] = Field(None, description="Product category ID")
    name: str = Field(...,description="Product category name")


class HardwareProductCategoryData(BaseModel):
    """
    Request model for assigining a Project Material Item.
    """
    category: Optional[HardwareProductCategory] = Field(None, description="Product category details")




class ProjectMaterial(BaseModel):
    """
    Data model representing a Project Material.
    """
    id: Optional[str] = Field(None, description="ProjectMaterial ID")
    name: str = Field(None, description="Name of the ProjectMaterial", max_length = "100")
    short_code: Optional[str] = Field(None, description="Project Material short code")
    desc: Optional[str] = Field(None, description="Project Material description")
    series: Optional[str] = Field(None, description="Project Material series")
    material_type: Optional[MaterialType] = Field(None, description="Project Material type")
    raw_material_id: Optional[str] = Field(None, description="Project Material raw material id (applicable for DOOR/FRAME types)")
    product_category: Optional[HardwareProductCategoryData] = Field(None, description="Hardware Product category")
    selected_unit: Optional[SelectedUnit] = Field(None, description="User selected unit")
    has_pricebook: Optional[bool] = Field(True, description="has any pricebook or not")
    base_feature: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material base_feature")
    base_price: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material base_price")
    adon_feature: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material adon_feature")
    adon_price: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material adon_price")
    total_amount: Optional[float] = Field(None, description="total ammount (base + adon)")
    manufacturer_id: Optional[str] = Field(None, description="Manufacturer ID", max_length = "36")
    brand_id: Optional[str] = Field(None, description="Brand ID", max_length = "36")
    project_id: Optional[str] = Field(None, description="Project ID", max_length = "36")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Project Material creation time")
    created_by: Optional[str] = Field(None, description="Project Material created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Project Material updation time")
    updated_by: Optional[str] = Field(None, description="Project Material updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Project Material deletion time")
    deleted_by: Optional[str] = Field(None, description="Project Material deleted by")



class ProjectMaterialRequest(ProjectMaterial):
    """
    Request model for creating a Project Material Item.
    """
    quantity: float = Field(description="Material Quantity")




class ProjectMaterialAssignRequest(BaseModel):
    """
    Request model for assigining a Project Material Item.
    """
    quantity: float = Field(description="Material Quantity")
    project_material_id: str = Field(description="Project Material id")


class BatchProjectMaterialAssignRequest(BaseModel):
    """
    Request model for batch assigining a Project Material Item.
    """
    project_take_off_sheet_section_area_items_ids: List[str] = Field(description="Project Take Off Sheet Section Area Item ids")
    quantity: float = Field(description="Material Quantity")

class ProjectMaterialRequest(ProjectMaterial):
    """
    Request model for creating a Project Material Item.
    """
    quantity: float = Field(description="Material Quantity")

class CreateOpeningProjectMaterialRequest(ProjectMaterial):
    """
    Request model for creating a Opening Project Material Item.
    """
    opening_schedule_id: str = Field(description="Opening Schedule ID")
    quantity: float = Field(description="Material Quantity")


class OpeningHardwareMaterialCloneRequest(BaseModel):
    """
    Request model for cloning Opening Hardware Material Item.
    """
    # quantity: float = Field(description="Material Quantity")
    project_id: float = Field(description="Project Id")
    short_code: float = Field(description="Short Code of the Material")

class HardwareProductSubCategory(BaseModel):
    """
    Request model for assigining a Project Material Item.
    """
    id: Optional[str] = Field(None, description="Product sub-category ID")
    name: str = Field(...,description="Product sub-catgory name")



class OpeningHardwareMaterial(BaseModel):
    """
    Data model representing a Opening hardware Material.
    """
    id: Optional[str] = Field(None, description="ProjectMaterial ID")
    name: str = Field(None, description="Name of the ProjectMaterial", max_length = "100")
    short_code: Optional[str] = Field(None, description="Project Material short code")
    desc: Optional[str] = Field(None, description="Project Material description")
    series: Optional[str] = Field(None, description="Project Material series")
    base_feature: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material base_feature")
    base_price: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material base_price")
    adon_feature: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material adon_feature")
    adon_price: Optional[Union[Dict,List[Dict]]] = Field(None, description="Project Material adon_price")
    total_amount: Optional[float] = Field(None, description="total ammount (base + adon)")
    quantity: float = Field(None, description="Material Quantity")
    manufacturer_id: Optional[str] = Field(None, description="Manufacturer ID", max_length = "36")
    brand_id: Optional[str] = Field(None, description="Brand ID", max_length = "36")
    project_id: Optional[str] = Field(None, description="Project ID", max_length = "36")
    product_category: Optional[HardwareProductCategoryData] = Field(None, description="Hardware Product category")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Project Material creation time")
    created_by: Optional[str] = Field(None, description="Project Material created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Project Material updation time")
    updated_by: Optional[str] = Field(None, description="Project Material updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Project Material deletion time")
    deleted_by: Optional[str] = Field(None, description="Project Material deleted by")



class OpeningDoorFrameMaterial(BaseModel):
    """
    Data model representing an Opening Door/Frame Material.
    """
    id: Optional[str] = Field(None, description="Door/Frame Material ID")
    name: str = Field(None, description="Name of the Door/Frame Material", max_length = "100")
    short_code: Optional[str] = Field(None, description="Door/Frame Material short code")
    desc: Optional[str] = Field(None, description="Door/Frame Material description")
    series: Optional[str] = Field(None, description="Door/Frame Material series")
    raw_material_code: Optional[str] = Field(None, description="Raw material code (DOOR or FRAME)")
    material_type: Optional[str] = Field(None, description="Material type (DOOR or FRAME)")
    base_feature: Optional[Union[Dict,List[Dict]]] = Field(None, description="Door/Frame Material base_feature")
    base_price: Optional[Union[Dict,List[Dict]]] = Field(None, description="Door/Frame Material base_price")
    adon_feature: Optional[Union[Dict,List[Dict]]] = Field(None, description="Door/Frame Material adon_feature")
    adon_price: Optional[Union[Dict,List[Dict]]] = Field(None, description="Door/Frame Material adon_price")
    total_amount: Optional[float] = Field(None, description="total amount (base + adon)")
    quantity: float = Field(None, description="Material Quantity")
    manufacturer_id: Optional[str] = Field(None, description="Manufacturer ID", max_length = "36")
    brand_id: Optional[str] = Field(None, description="Brand ID", max_length = "36")
    project_id: Optional[str] = Field(None, description="Project ID", max_length = "36")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is deleted")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Door/Frame Material creation time")
    created_by: Optional[str] = Field(None, description="Door/Frame Material created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Door/Frame Material updation time")
    updated_by: Optional[str] = Field(None, description="Door/Frame Material updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Door/Frame Material deletion time")
    deleted_by: Optional[str] = Field(None, description="Door/Frame Material deleted by")



class RawMaterialMapping(BaseModel):
    """
    Represents a single mapping between raw material and its default discount.
    """
    raw_material_id: str = Field(..., description="Unique identifier for the raw material")
    default_discount: float = Field(..., description="Default discount for the raw material")
    has_data: bool = Field(False, description="Indicates whether this raw material has associated data")



class RawMaterialMappingRequest(BaseModel):
    """
    Request model for mapping raw materials with default discounts.
    """
    mapping_data: List[RawMaterialMapping] = Field(..., description="List of raw material discount mappings")


class UpdateMaterialDescriptionRequest(BaseModel):
    """
    Request model for updating a project material description.
    """
    description: str = Field(..., description="Material description", max_length = "1000")


class UpdateDoorFrameMaterialSectionRequest(BaseModel):
    """
    Request model for bulk create/update of door frame raw material sections.
    All listed raw materials share one material_type. Rows are keyed by
    (project_id, raw_material_id): insert if missing, else update material_type.
    """

    raw_material_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Raw material IDs",
    )
    material_type: str = Field(
        ...,
        description="Material type for every raw material (DOOR, FRAME, etc.)",
    )

    @model_validator(mode="after")
    def raw_ids_unique(self) -> "UpdateDoorFrameMaterialSectionRequest":
        if len(set(self.raw_material_ids)) != len(self.raw_material_ids):
            raise ValueError("raw_material_ids must not contain duplicates")
        return self
