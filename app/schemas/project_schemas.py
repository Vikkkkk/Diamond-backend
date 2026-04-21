"""
This module containes all schemas those are related to Project add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from fastapi import Form
from models.projects import Priority
import enum

class Priority(enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Project(BaseModel):
    """**Summary:**
    This class contains the schema of each Project
    """
    id: Optional[str] = Field(None, description="ID")
    project_code: Optional[str] = Field(None, description="Project Code")
    name: str = Field(None, description="Name of the Project", max_length = "100")
    quotation_due_date: Union[str, datetime] = Field(None, description="Due date")
    street_address: str = Field(None, description="Street Address", max_length = "255")
    province: str = Field(None, description="Province", max_length = "100")
    country: str = Field(None, description="Country", max_length = "100")
    postal_code: str = Field(None, description="Postal Code", max_length = "20")
    priority: Priority = Field(None, description="Priority")
    note: Optional[str] = Field(None, description="Note")
    start_date: Optional[Union[str, datetime]] = Field(None, description="Project Start Date")
    due_date: Optional[Union[str, datetime]] = Field(None, description="Project Due Date")
    current_project_status: Optional[str] = Field(None, description="Current Project Status", max_length = "20")
    current_bid_status: Optional[str] = Field(None, description="Current Bid Status", max_length = "20")
    is_estimation: Optional[bool] = Field(None, description="is_estimation")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Project creation time")
    created_by: Optional[str] = Field(None, description="Project created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Project updation time")
    updated_by: Optional[str] = Field(None, description="Project updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Project deletion time")
    deleted_by: Optional[str] = Field(None, description="Project deleted by")
    client_ids: Optional[str] = Field(None, description="List of Client ID")
    member_ids: Optional[List[UUID]] = Field(None, description="List of Member ID")  # List of UUIDs



# class ProjectRequest(BaseModel):
#     """**Summary:**
#     This class contains the schema of each Project
#     """
#     project_id: Optional[str] = Field(None, description="Project ID")
#     name: Optional[str] = Field(None, description="Name of the Project", max_length = "100")
#     due_date: Optional[Union[str, datetime]] = Field(None, description="Due date")
#     street_address: Optional[str] = Field(None, description="Street Address", max_length = "255")
#     province: Optional[str] = Field(None, description="Province", max_length = "100")
#     country: Optional[str] = Field(None, description="Country", max_length = "100")
#     postal_code: Optional[str] = Field(None, description="Postal Code", max_length = "20")
#     note: Optional[str] = Field(None, description="Note")
#     client_id: Optional[str] = Field(None, description="cilent id of the project")
#     member_ids: Optional[str] = Field(None, description="Members(Estimators) of the project")


class ProjectResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of a particular Member's details fetch request.
    """
    data: List[Project]
    status: str


class ProjectList(BaseModel):
    id: str
    name: Optional[str]


class ProjectListResponse(BaseModel):
    page_count: int|None
    item_count: int|None
    status: str
    data: List[ProjectList]


class MemberInfo(BaseModel):
    id: str = Field(..., description="The unique identifier for the member.")
    name: str = Field(..., description="Member Name.")

class MembersResponse(BaseModel):
    data: List[MemberInfo]
    status: str

    



class Role(BaseModel):
    role_id: str = Field(..., description="The unique identifier of the role")
    role_name: str = Field(..., description="The name of the role")

class ProjectAssignResponse(BaseModel):
    id: str = Field(..., description="The unique identifier for the project.")
    name: Optional[str] = Field(None, description="The name of the project.")
    start_date: str = Field(None, description="The start date and time of the project.")
    due_date: str = Field(None, description="The due date and time for project completion.")
    project_status: Optional[str] = Field(None, description="The status of the project.")
    assigned_members:List[MembersResponse]
    roles:List[Role]



class RoleInfo(BaseModel):
    id: str = Field(..., description="The unique identifier of the role")
    role_name: str = Field(..., description="The name of the role")
    member_role_id: str = Field(..., description="The unique identifier of the member-role relationship")


class ProjectMemberInfo(BaseModel):
    member_id: str = Field(..., description="The unique identifier of the member")
    member_name: str = Field(..., description="The full name of the member, concatenated from first and last names")
    roles: List[RoleInfo] = Field(
        default_factory=list, 
        description="A list of roles associated with the member."
    )

class ProjectMemberRoleResponse(BaseModel):
    data: List[ProjectMemberInfo]
    page_count: int|None
    item_count: int|None
    status: str