from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ScheduleDataRequest(BaseModel):
    id: Optional[str] = Field(None, description="ID")
    name: str
    value: str
    adon_field_id: str
    adon_field_option_id: Optional[str] = Field(None, description="Adon Field Option ID")
    is_adon_field: bool 

class ScheduleDataBulkRequest(BaseModel):
    schedule_id: str
    component: str
    fields: list[ScheduleDataRequest]

class PriceDataSchema(BaseModel):
    unit: str
    price: float


class changeOrderScheduleDataSaveSchema(BaseModel):
    id: Optional[str] = Field(None, description="ID")
    manufacturerCode: Optional[str] = Field(None, description="Manufacture code of selected catalog")
    brandCode: Optional[str] = Field(None, description="Brand code of selected catalog")
    seriesCode: Optional[str] = Field(None, description="Selected Series code")
    featureCode: Optional[str] = Field(None, description="Selected Feature code")
    adonFeatureCode: Optional[str] = Field(None, description="Selected Adon Feature code")
    optionCode: Optional[str] = Field(None, description="Selected Option code")
    name: str
    value: str
    desc: str
    adon_field_id: Optional[str] = Field(None, description="Adon Field ID")
    adon_field_option_id: Optional[str] = Field(None, description="Adon Field Option ID")
    is_adon_field: bool 
    is_manual: bool
    has_price_dependancy: bool

class changeOrderScheduleDataBulkSaveSchema(BaseModel):
    schedule_id: str
    component: str
    part_number: Optional[int] = None
    fields: Dict[str, changeOrderScheduleDataSaveSchema] = Field(..., description="field name will be the key")


class ScheduleDataSaveSchema(BaseModel):
    id: Optional[str] = Field(None, description="ID")
    manufacturerCode: Optional[str] = Field(None, description="Manufacture code of selected catalog")
    brandCode: Optional[str] = Field(None, description="Brand code of selected catalog")
    seriesCode: Optional[str] = Field(None, description="Selected Series code")
    featureCode: Optional[str] = Field(None, description="Selected Feature code")
    adonFeatureCode: Optional[str] = Field(None, description="Selected Adon Feature code")
    optionCode: Optional[str] = Field(None, description="Selected Option code")
    name: str
    value: str
    desc: str
    adon_field_id: Optional[str] = Field(None, description="Adon Field ID")
    adon_field_option_id: Optional[str] = Field(None, description="Adon Field Option ID")
    is_adon_field: bool 
    is_manual: bool
    has_price_dependancy: bool
 
class ScheduleDataBulkSaveSchema(BaseModel):
    schedule_id: str
    component: str
    part_number: Optional[int] = None
    fields: Dict[str, ScheduleDataSaveSchema] = Field(..., description="field name will be the key")

# class SchedulePriceDataRequest(BaseModel):
#     id: str
#     name: str
#     desc: Optional[str]
#     rule: Optional[Dict[str, Any]]
#     adon_opening_field_id: str

class ScheduleData(BaseModel):
    id: str
    name: str
    desc: Optional[str]
    value: Optional[str]
    component: str
    part_number: Optional[int]
    feature_code: Optional[str]
    option_code: Optional[str]
    feature_data: Optional[Union[Dict, List[Dict]]]
    price_data: Optional[Union[Dict, List[Dict]]]
    additional_data: Optional[Union[Dict, List[Dict]]]
    total_amount: float
    total_sell_amount: float
    total_base_amount: float
    total_extended_sell_amount: float
    quantity: float
    final_amount: float
    final_sell_amount: float
    final_base_amount: float
    final_extended_sell_amount: float
    margin: Optional[float] = 0
    markup: Optional[float] = 0
    discount: Optional[float] = 0
    discount_type: Optional[str] = None
    surcharge: Optional[float] = 0
    surcharge_type: Optional[str] = None
    quantity: Optional[float] = 1
 
    is_table_data: Optional[bool] = False
    is_basic_discount: Optional[bool] = False  
    surcharge: float
    surcharge_type: Optional[str]
    adon_field_id: Optional[str]
    adon_field_option_id: Optional[str]
    schedule_id: str
    is_manual: bool
    is_table_data: bool
    is_adon_field: bool
    has_price_dependancy: bool

class ScheduleDataResponse(BaseModel):
    data: List[ScheduleData]
    message: str
    component: str
    part_number: Optional[int]