"""
This module containes all schemas those are related to Client add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class Client(BaseModel):
    """**Summary:**
    This class contains the schema of each Client
    """
    id: Optional[str] = Field(None, description="Client ID")
    name: str = Field(None, description="Name of the Client", max_length = "100")
    contact_name: str = Field(None, description="Contact name", max_length = "100")
    email: str = Field(None, description="Email", max_length = "100")
    phone: Optional[str] = Field(None, description="Phone", max_length = "20")
    fax: Optional[str] = Field(None, description="Fax", max_length = "20")
    website: Optional[str] = Field(None, description="Website", max_length = "100")
    street_address: str = Field(None, description="Street Address", max_length = "255")
    province: str = Field(None, description="Province", max_length = "100")
    country: str = Field(None, description="Country", max_length = "100")
    postal_code: str = Field(None, description="Postal Code", max_length = "20")
    note: Optional[str] = Field(None, description="Note")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Client creation time")
    created_by: Optional[str] = Field(None, description="Client created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Client updation time")
    updated_by: Optional[str] = Field(None, description="Client updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Client deletion time")
    deleted_by: Optional[str] = Field(None, description="Client deleted by")

class ClientResponseItem(BaseModel):
    """**Summary:**
    This class contains the schema of each Client
    """
    id: Optional[str] = Field(None, description="Client ID")
    name: str = Field(None, description="Name of the Client", max_length = "100")
    contact_name: str = Field(None, description="Contact name", max_length = "100")
    email: str = Field(None, description="Email", max_length = "100")
    phone: Optional[str] = Field(None, description="Phone", max_length = "20")
    fax: Optional[str] = Field(None, description="Fax", max_length = "20")
    website: Optional[str] = Field(None, description="Website", max_length = "100")
    street_address: str = Field(None, description="Street Address", max_length = "255")
    province: str = Field(None, description="Province", max_length = "100")
    country: str = Field(None, description="Country", max_length = "100")
    postal_code: str = Field(None, description="Postal Code", max_length = "20")
    note: Optional[str] = Field(None, description="Note")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Client creation time")
    created_by: Optional[str] = Field(None, description="Client created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Client updation time")
    updated_by: Optional[str] = Field(None, description="Client updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Client deletion time")
    deleted_by: Optional[str] = Field(None, description="Client deleted by")
    total_project_count: Optional[int] = Field(0, description="Total project count")



class ClientsResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of multiple Client fetch request.
    """
    data: List[ClientResponseItem]
    page_count: Optional[int] = Field(None, description="Total number of pages Required")
    item_count: Optional[int] = Field(None, description="Total number of Item is there")
    status: str