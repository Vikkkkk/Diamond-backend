from typing import Optional, List, Dict
from pydantic import BaseModel, Field, root_validator
from datetime import datetime




class ProjectTaskCreateRequest(BaseModel):
    project_id: str = Field(..., description="Project ID to which the task belongs")
    task_status_id: str = Field(..., description="Task Status ID")
    task_title: str = Field(..., description="Title of the task")
    task_description: Optional[str] = Field(None, description="Description of the task")
    start_date: Optional[datetime] = Field(None, description="Task start date")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    assigned_members: Optional[str] = Field(None, description="List of project member IDs to be added to the task")
    is_estimation: bool = Field(None, description="Is Estimation")


class TaskMemberResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the task member")
    member_id: str = Field(..., description="Member ID")
    project_member_id: str = Field(..., description="Project Member ID")
    created_at: datetime = Field(..., description="Task member creation timestamp")
    created_by: str = Field(..., description="Member ID of the task member creator")

class TaskAttachmentResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the attachment")
    file_name: str = Field(..., description="Name of the file")
    file_path: str = Field(..., description="Path where the file is stored")
    file_type: str = Field(..., description="Type of the file")
    created_at: datetime = Field(..., description="Attachment creation timestamp")
    created_by: str = Field(..., description="Member ID of the attachment creator")

class ProjectTaskResponse(BaseModel):
    id: str = Field(..., description="Unique identifier of the task")
    project_id: Optional[str] = Field(None, description="Project ID to which the task belongs")
    task_status_id: Optional[str] = Field(None, description="Task Status ID")
    task_title: str = Field(..., description="Title of the task")
    task_description: Optional[str] = Field(None, description="Description of the task")
    start_date: Optional[datetime] = Field(None, description="Task start date")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    created_at: datetime = Field(..., description="Task creation timestamp")
    created_by: str = Field(..., description="Member ID of the task creator")
    assigned_members: List[TaskMemberResponse] = Field(default_factory=list, description="List of assigned members")
    # attachments: List[TaskAttachmentResponse] = Field(default_factory=list, description="List of task attachments")


class TaskUpdateRequest(BaseModel):
    project_id: Optional[str] = Field(None, description="Project ID to which the task belongs")
    task_title: Optional[str] = Field(None, description="Title of the task")
    task_description: Optional[str] = Field(None, description="Description of the task")
    start_date: Optional[datetime] = Field(None, description="Task start date")
    due_date: Optional[datetime] = Field(None, description="Task due date")

class ProjectUpdateTaskResponse(ProjectTaskResponse):
    updated_at: Optional[datetime] = Field(None, description="Task update date")
    updated_by: Optional[str] = Field(None, description="Member ID of the person updating the task")


class RoleResponse(BaseModel):
    id: str = Field(..., description="The unique identifier for the role.")
    role_name: str = Field(..., description="The name of the role.")

class MemberResponse(BaseModel):
    member_id: str = Field(..., description="The unique identifier for the member.")
    member_name: str = Field(..., description="The full name of the member.")
    roles: List[RoleResponse] = Field(
        default_factory=list,
        description="A list of roles assigned to the member."
    )

class AttachmentResponse(BaseModel):
    id: str = Field(..., description="The unique identifier for the attachment.")
    task_comment_id: str|None = Field(None, description="The comment id for the attachment.")

    file_name: str = Field(..., description="The name of the file.")
    file_path: str = Field(..., description="The path where the file is stored.")
    file_type: str = Field(..., description="The type of the file (e.g., MIME type).")


class TaskInfo(BaseModel):
    id: str = Field(..., description="The unique identifier for the task.")
    project_id: Optional[str] = Field(None, description="The ID of the associated project.")
    task_status_id: Optional[str] = Field(None, description="The ID representing the task status.")
    task_status: Optional[str] = Field(None, description="Task status.")
    task_title: str = Field(..., description="The title of the task.")
    task_description: Optional[str] = Field(None, description="A brief description of the task.")
    start_date: Optional[str] = Field(None, description="The start date of the task, formatted as 'Jan 25, 2021'.")
    due_date: Optional[str] = Field(None, description="The due date of the task, formatted as 'Jan 25, 2021'.")
    task_activity_count: Optional[int] = Field(None, description="The number of activities associated with the task.")
    past_due: Optional[bool] = Field(None, description="Indicates if the task is past its due date.")
    assigned_members: List["MemberResponse"] = Field(
        default_factory=list,
        description="A list of members assigned to the task."
    )

    task_completion_status_info: dict = Field(..., description="Task Completion status for the task.")

    @root_validator(pre=True)
    def format_dates(cls, values):
        """Format the start_date and due_date as 'Jan 25, 2021'."""
        date_format = "%b %d, %Y"
        if isinstance(values.get('start_date'), datetime):
            values['start_date'] = values['start_date'].strftime(date_format)
        if isinstance(values.get('due_date'), datetime):
            values['due_date'] = values['due_date'].strftime(date_format)
        return values


class TaskResponse(BaseModel):
    page_count: int|None
    item_count: int|None
    status: str
    data: List[TaskInfo]
    
class TaskCommentInfo(BaseModel):
    id: str
    task_id: str
    comment: str|None
    created_by_name: str
    member_id: str
    created_at: str = Field(..., description="comment creation timestamp")
    comment_attachments: List[AttachmentResponse] = Field(
        default_factory=list, 
        description="A list of attachments related to the comments."
    )

class TaskCommentResponse(BaseModel):
    data: TaskCommentInfo
    status: str

class TaskCommentByTaskId(BaseModel):
    data:List[TaskCommentInfo]
    page_count: int|None
    item_count: int|None
    status: str


class TaskById(BaseModel):
    id: str = Field(..., description="The unique identifier for the task.")
    project_id: Optional[str] = Field(None, description="The ID of the associated project.")
    task_status_id: Optional[str] = Field(None, description="The ID representing the task status.")
    task_title: str = Field(..., description="The title of the task.")
    task_description: Optional[str] = Field(None, description="A brief description of the task.")
    start_date: Optional[datetime] = Field(None, description="The start date and time of the task.")
    due_date: Optional[datetime] = Field(None, description="The due date and time for task completion.")
    task_activity_count: Optional[int] = Field(None, description="Task activity count.")
    past_due: Optional[bool] = Field(None, description="Past due.")
    assigned_members: List[MemberResponse] = Field(
        default_factory=list,
        description="A list of members assigned to the task."
    )
    # attachments: List[AttachmentResponse] = Field(
    #     default_factory=list, 
    #     description="A list of attachments related to the task."
    # )
    # comments:List[TaskCommentInfo] = Field(
    #     default_factory=list, 
    #     description="A list of comments."
    # )


class TaskByIdResponse(BaseModel):
    data: TaskById
    status: str

class TaskStatus(BaseModel):
    """Represents the response schema for a task status."""
    id: str
    status: str
    created_at: datetime
    created_by: Optional[str] = None

class TaskStatusResponse(BaseModel):
    data: List[TaskStatus]
    status: str

class TaskCommentCreateRequest(BaseModel):
    task_id: str = Field(..., description="ID of the task to which the comment belongs")
    comment: str = Field(..., description="The comment text")
    created_by: str = Field(..., description="Member ID of the creator")



class TaskActivityInfo(BaseModel):
    id: str = Field(
        ..., 
        description="A unique identifier for each task activity record, typically a UUID."
    )
    task_id: str = Field(
        ..., 
        description="The identifier of the task to which this activity belongs, linking back to the ProjectTask table."
    )
    activity: str = Field(
        ..., 
        description="A description of the activity that occurred, detailing what changes or actions were made."
    )
    created_at: str = Field(
        ..., 
        description="The date and time when the activity was created, recording the exact timestamp of the occurrence."
    )
    created_by: Optional[str] = Field(
        None, 
        description="Member Id who created the activity, indicating who performed the action. It may be None if the creator is not specified."
    )
    is_new: Optional[bool] = Field(
        1, 
        description="Is new"
    )
    member_name: Optional[str] = Field(
        None, 
        description="Member name who created the activity, indicating who performed the action. It may be None if the creator is not specified."
    )
    

class TaskActivityResponse(BaseModel):
    data: List[TaskActivityInfo]
    page_count: int|None
    item_count: int|None
    status: str


class TaskAttachments(BaseModel):
    id: str = Field(..., description="The unique identifier for the attachment.")
    task_id: str|None = Field(..., description="The unique identifier for the attachment.")
    task_comment_id: str|None = Field(None, description="The comment id for the attachment.")

    file_name: str|None = Field(..., description="The name of the file.")
    file_path: str|None = Field(..., description="The path where the file is stored.")
    file_type: str|None = Field(..., description="The type of the file (e.g., MIME type).")


class PaginatedTaskAttachmentResponse(BaseModel):
    data: List[TaskAttachments]
    page_count: int|None
    item_count: int|None
    status: str