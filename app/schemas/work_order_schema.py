"""
This module containes all schemas those are related to TakeOffSheets add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
import json

class StartORStopWorkOrder(BaseModel):
    """
    Data model representing a TakeOffSheet.
    """
    location_details: Optional[str] = Field(json.dumps({"location_details": {"lat": 0, "lng": 0}, "distance_in_meter": 1000}), description="Location details with latitude and longitude")
