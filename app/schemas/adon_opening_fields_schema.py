from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class AddonOpeningFieldTypeEnum(str, Enum):
    NUMBER = 'NUMBER'
    TEXT = 'TEXT'
    DROPDOWN = 'DROPDOWN'
    FILE_UPLOAD = 'FILE_UPLOAD'


class AdonOpeningFieldOptionSchema(BaseModel):
    id: str
    name: str
    desc: Optional[str]
    rule: Optional[Dict[str, Any]]
    adon_opening_field_id: str


class AdonOpeningFieldSchema(BaseModel):
    id: str
    name: str
    desc: Optional[str]
    has_price_dependancy: bool
    field_type: Optional[AddonOpeningFieldTypeEnum]
    field_category: Optional[str]
    rule: Optional[Dict[str, Any]]
    is_adon_field: bool
    field_options: Optional[List[AdonOpeningFieldOptionSchema]]


class AdonOpeningFieldResponseSchema(BaseModel):
    data: List[AdonOpeningFieldSchema]
    component: str
    status: str

class AdonFieldOptionSchema(BaseModel):
    optionCode: str
    optionDesc: str
    availabilityCriteria: List[Dict]
    featureCode: str
    featureDesc: str
    seriesCode: str
    category: str
    manufacturerCode: str
    brandCode: str
    seriesDesc: str

class AdonOpeningFieldOpeningResponseSchema(BaseModel):
    data: List[AdonFieldOptionSchema]
    status: str


class OpeningFieldOptionSchema(BaseModel):
    optionCode: str
    optionDesc: str
    availabilityCriteria: List[Dict]
    featureCode: str
    featureDesc: str
    seriesCode: str
    category: str
    manufacturerCode: str
    brandCode: str
    seriesDesc: str

class OpeningFieldOpeningResponseSchema(BaseModel):
    data: List[Union[OpeningFieldOptionSchema, AdonFieldOptionSchema]]
    status: str
