"""
This module containes all schemas those are related to charges add/update/read/delete requests.
"""
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from fastapi import status as fast_api_status
from fastapi.responses import JSONResponse
from fastapi import Form
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

class MULTIPLIER_TYPE(str, Enum):
    """**Summary:**
    This class contains the schema of MULTIPLIER_TYPE
    """
    PERCENTAGE = 'PERCENTAGE'
    FLAT = 'FLAT'
    MULTIPLIER = 'MULTIPLIER'


class ProjectTakeOffSheetCharges(BaseModel):
    """**Summary:**
    This class contains the schema of Charges for Project take off sheets
    """
    id: Optional[str] = Field(None, description="ProjectTakeOffSheetCharge ID")
    name: str = Field(None, description="Name of the Charges", max_length = "100")
    desc: Optional[str] = Field(None, description="Charges description")
    project_take_off_sheet_id: Optional[str] = Field(None, description="project_take_off_sheet ID")
    charge_type: Optional[str] = Field(None, description="Charges Type")
    amount: Optional[float] = Field(None, description="amount")
    multiplier_type: Optional[MULTIPLIER_TYPE] = Field(None, description="Is flat charge or some percentage or multiplier")
    is_active: Optional[bool] = Field(None, description="Is active")
    created_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheetCharge creation time")
    created_by: Optional[str] = Field(None, description="TakeOffSheetCharge created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="TakeOffSheetCharge updation time")
    updated_by: Optional[str] = Field(None, description="TakeOffSheetCharge updated by")


class ProjectTakeOffSheetChargesResponse(BaseModel):
    """
    Response model for fetching a TakeOffSheet Charge.
    """
    data: List[ProjectTakeOffSheetCharges]
    status: str



