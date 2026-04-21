"""
This module containes all schemas those are related to permissions add/update/read/delete requests.
"""
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from schemas.member_schema import MemberPermissionList, Member
from schemas.sub_module_schema import SubModule
from schemas.module_schema import Module
from schemas.role_schema import RoleSchema

class Permission(BaseModel):
    sub_module_id: str = Field(None, description="Sub Module ID")
    is_read: bool = Field(None, description="Is Read")
    is_write: bool = Field(None, description="Is Write")
    is_delete: bool = Field(None, description="Is Delete")

class RolePermissions(BaseModel):
    role_id: str
    permission: List[Permission]


class PermissionSubModuls(Module):
    """**Summary:**
    This class contains schema of a module along with its associated submodules.
    """
    sub_modules: Optional[List[SubModule]]



class MemberPermissionDetails(BaseModel):
    """**Summary:**
    This class contains schema of a member along with its accessible modules and its submodules.
    It Also includes the projects that the member is asigned to. 
    """
    permissions: Optional[List[PermissionSubModuls]] = []
    roles: Optional[List[RoleSchema]] = []


class PermissionsRequest(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of multiple Member Permission fetch request.
    """
    moduleList: Optional[List[str]] = Field(None, description="Modules to be added as member permission")
    subModuleList: Optional[List[str]] = Field(None, description="submodules to be added as member permission")


class MemberPermissionResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of a particular Member's permission details fetch request.
    """
    data: Optional[MemberPermissionDetails]
    status: str

class ModuleMemberResponse(BaseModel):
    """**Summary:**
    This class contains schema of list members those have access to a particular module.
    """
    data: List[MemberPermissionList]
    status: str
