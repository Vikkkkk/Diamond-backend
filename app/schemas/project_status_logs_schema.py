"""
This module containes all schemas those are related to Notes add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class ProjectStatusLogs(BaseModel):
    """**Summary:**
    This class contains the schema of Project Status Logs
    """
    status_id: str =  Field(description="Status ID")
    status_type: str = Field(description="PROJECT_STATUS/BID_STATUS")

   