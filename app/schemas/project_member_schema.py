"""
This module containes all schemas those are related to permissions add/update/read/delete requests.
"""
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from schemas.project_schemas import Project
from schemas.module_schema import Module

class ProjectMembers(BaseModel):
    """**Summary:**
    This class contains schema of a module along with its associated submodules.
    """
    id: Optional[UUID] = Field(None, description="project member ID")
    module_id: str = Field(None, description="Module ID")
    member_id: str = Field(None, description="Member ID")
    project_id: str = Field(None, description="Project ID")
    is_active: Optional[bool] = Field(None,description="member project is active or not")
    is_deleted: Optional[bool] = Field(None, description="Is delete")
    created_at: Optional[Union[str, datetime]] = Field(None, description="project association creation time")
    created_by: Optional[str] = Field(None, description="project association created by")
    updated_at: Optional[Union[str, datetime]] = Field(None, description="project association updation time")
    updated_by: Optional[str] = Field(None, description="project association updated by")
    deleted_at: Optional[Union[str, datetime]] = Field(None, description="project association deletion time")
    deleted_by: Optional[str] = Field(None, description="project association deleted by")


class MemberProjectDetail(ProjectMembers):
    """**Summary:**
    This class contains schema of a member having access to a particular project.
    """
    project: Optional[Project]
    module: Optional[Module] = Field(None,description="Module Details")


class MemberProjects(ProjectMembers):
    """**Summary:**
    This class contains schema of a member having access to a particular project.
    """
    project: Optional[Project]
    module: Optional[Module] = Field(None,description="Module Details")