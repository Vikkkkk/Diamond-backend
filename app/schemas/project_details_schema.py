"""
This module containes all schemas those are related to Project add/update/read/delete requests.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from schemas.member_schema import Member
from schemas.client_schemas import Client
from schemas.tender_documents import TenderDocument
from schemas.project_member_schema import ProjectMembers
from schemas.module_schema import Module
from schemas.project_schemas import Project
from schemas.sub_module_schema import SubModule
from schemas.member_schema import Member
from schemas.role_schema import RoleSchema



class PermissionSubModuls(Module):
    """**Summary:**
    This class contains schema of a module along with its associated submodules.
    """
    sub_modules: Optional[List[SubModule]]

class RoleDetails(RoleSchema):
    """**Summary:**
    This class contains schema of the reposne body of multiple Member fetch details along with its accessible modules and its submodules.
    It Also includes the projects that the member is asigned to.
    """
    permissions: Optional[List[PermissionSubModuls]]

class MembersDetails(Member):
    """**Summary:**
    This class contains schema of the reposne body of multiple Member fetch details along with its accessible modules and its submodules.
    It Also includes the projects that the member is asigned to.
    """
    roles: Optional[List[RoleSchema]]

class ProjectClientDetails(Project):
    """**Summary:**
    This class contains schema of the reposne body of a Project client detail.
    """
    clients: Optional[List[Client]]
    
class ProjectsResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of multiple Project fetch request.
    """
    data: List[ProjectClientDetails]
    page_count: Optional[int] = Field(None, description="Total number of pages Required")
    item_count: Optional[int] = Field(None, description="Total number of Item is there")
    status: str


class ProjectDetails(Project):
    """**Summary:**
    This class contains schema of the reposne body of a Project detail.
    """
    clients: Optional[List[Client]]
    tender_documents: Optional[List[TenderDocument]]
    project_members: Optional[List[MembersDetails]]
    


class ProjectResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of a Project detail fetch request.
    """
    data: ProjectDetails
    status: str


class ProjectModuleMemberDetails(Project):
    """**Summary:**
    This class contains schema of the reposne body of a Project member details of a module.
    """
    project_members: Optional[List[MembersDetails]]
    


class ProjectModuleMemberResponse(BaseModel):
    """**Summary:**
    This class contains schema of the reposne body of a Project member details of a module fetch request.
    """
    data: Optional[List[MembersDetails]]
    status: str