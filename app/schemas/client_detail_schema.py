"""
This module containes all schemas those are related to Client details read requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from schemas.project_schemas import Project
from schemas.client_schemas import Client

class ClientResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of a Client detail fetch request.
    """
    data: Client
    status: str