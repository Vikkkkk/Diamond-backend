"""
This module containes all schemas those are related to members add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from schemas.module_schema import Module
from schemas.sub_module_schema import SubModule
from schemas.member_permission_schema import MemberPermission
from schemas.project_schemas import Project
from schemas.role_schema import RoleSchema
class Member(BaseModel):
    """**Summary:**
    This class contains the schema of each Member 
    """
    id: Optional[str] = Field(None,description="Member ID")
    first_name: str = Field(None, description="First name of the member", max_length=100)
    last_name: str = Field(None, description="Last name of the member", max_length=100)
    email: str = Field(None, description="Email", max_length=255)
    phone: str = Field(None, description="Phone", max_length=20)
    password: str = Field(None,description="password", max_length=100)
    token: Optional[str] = Field(None,description="token")
    is_super_admin: Optional[bool] = Field(None,description="Member is super admin or not")
    is_active: Optional[bool] = Field(None,description="Member is active or not")
    last_login: Optional[Union[str, datetime]] = Field(None,description="Member last login time")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="Member creation time")
    created_by: Optional[str] = Field(None, description="Member created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="Member updation time")
    updated_by: Optional[str] = Field(None, description="Member updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="Member deletion time")
    deleted_by: Optional[str] = Field(None, description="Member deleted by")


class ChangePasswordRequest(BaseModel):
    password: str
    confirm_password: str
    
class MemberPermissionList(Member):
    """**Summary:**
    This class contains schema of a member having access to a particular module.
    """
    permissions: List[MemberPermission]

    name: str = Field(None, description="Sub-Module Name")

class PermissionSubModulDetails(SubModule):
    """**Summary:**
    This class contains schema of a module along with its associated submodules.
    """
    childs: Optional[List[SubModule]]

class PermissionSubModuls(Module):
    """**Summary:**
    This class contains schema of a module along with its associated submodules.
    """
    sub_modules: Optional[List[SubModule]]


class MemberDetails(Member):
    """**Summary:**
    This class contains schema of a member along with its accessible modules and its submodules.
    It Also includes the projects that the member is asigned to. 
    """
    # permissions: Optional[List[PermissionSubModuls]]
    projects: Optional[List[Project]]
    roles: Optional[List]
    tax: Optional[str]
    tax_type: Optional[str]
    margin_threshold: Optional[str]


class RoleAssign(BaseModel):
    """**Summary:**
    This class contains schema of a member along with its accessible modules and its submodules.
    It Also includes the projects that the member is asigned to. 
    """
    roleIds: List[str]


class MembersDetails(Member):
    """**Summary:**
    This class contains schema of the reposne body of multiple Member fetch details along with its accessible modules and its submodules.
    It Also includes the projects that the member is asigned to.
    """
    # permissions: Optional[List[MemberPermission]]
    permissions: Optional[List[PermissionSubModuls]]
    # projects: Optional[List[Project]]

class MembersResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of multiple Member fetch request.
    """
    data: List[MembersDetails]
    page_count: Optional[int] = Field(None, description="Total number of pages Required")
    item_count: Optional[int] = Field(None, description="Total number of Item is there")
    status: str


class MemberResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of a particular Member's details fetch request.
    """
    data: Optional[List[MemberDetails]]
    status: str

class ProfileSwitchRequest(BaseModel):
    role_id: str = Field(description = "Member ID")