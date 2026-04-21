"""
This module containes all schemas those are related to shipping add/update/read/delete requests.
"""
from typing import List, Optional, Dict, Union, Any
from enum import Enum
from pydantic import BaseModel, Field, Json, root_validator
from uuid import UUID
from datetime import datetime, date


class GenerateLabelRequest(BaseModel):
    data: Dict[UUID, int] = Field(
        ...,
        description="A dictionary mapping Order Item Id(UUIDs) to crate Number (integer) values."
    )
