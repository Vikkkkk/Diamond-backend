"""
This module containes all routes those are related to task.
"""
from typing import List, Optional
import os
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from starlette import status
from models import get_db
from controller import task_controller
from loguru import logger
from schemas.task_schema import ProjectTaskCreateRequest, TaskUpdateRequest, TaskResponse, TaskStatusResponse, TaskByIdResponse, TaskActivityResponse, TaskCommentResponse, TaskCommentByTaskId, PaginatedTaskAttachmentResponse
from utils.auth import verify_token
from schemas.auth_schemas import invalid_credential_resp
from utils.auth import verify_token, get_current_member
from models.members import Members
from utils.common import generate_uuid,convert_to_timezone
from models.task_attachments import TaskAttachments
import json
from datetime import datetime
from models.task_members import TaskMembers
from models.project_members import ProjectMembers
from models.project_task import ProjectTask
from models.task_comments import TaskComments
import traceback
from repositories.task_repositories import validate_attachments

router = APIRouter(prefix="/task", tags=["Task APIs"])

@router.post("/project/{project_id}/create_task", status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: str,
    task_status_id: str = Form(...),
    task_title: str = Form(...),
    task_description: str = Form(None),
    start_date: datetime = Form(None),
    due_date: datetime = Form(None),
    assigned_members: str = Form(None),  
    is_estimation: bool = Form(None),
    attachments: List[UploadFile] = File(None),
    current_member: Members = Depends(get_current_member), 
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Create a new task for a project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `task_status_id` (str): The status ID of the task.
    - `task_title` (str): The title of the task.
    - `task_description` (Optional[str]): The description of the task.
    - `start_date` (Optional[datetime]): The start date of the task.
    - `due_date` (Optional[datetime]): The due date of the task.
    - `assigned_members` (Optional[str]): JSON string of member IDs.
    - `attachments` (Optional[List[UploadFile]]): List of files to be uploaded as attachments.
    - `current_member` (Members): The current logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `dict`: The details of the created task.
      Status code 201 if successful, 500 if an exception occurs.
    """
    try:

        

        # Validate start_date and due_date
        if start_date and due_date:
            if start_date > due_date:
                return JSONResponse(status_code=400, content={"message": "Start date cannot be greater than due date."})
            if due_date < start_date:
                return JSONResponse(status_code=400, content={"message": "Due date cannot be less than start date."})

        # Validate attachments if any
        # if attachments:
        #     validation_response = await validate_attachments(attachments)
        #     if validation_response:
        #         return validation_response

        task_data = ProjectTaskCreateRequest(
            project_id = project_id,
            task_status_id = task_status_id,
            task_title = task_title,
            task_description = task_description,
            start_date = start_date,
            due_date = due_date,
            assigned_members = assigned_members,
            is_estimation = is_estimation
        )

        # file_content = await attachments[0].read()
        # print("file_content 1 ---->>>>> ", file_content)
        # attachments[0].seek(0)

        new_task = await task_controller.add_task(db, task_data, attachments, current_member)

        return new_task

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/project/{project_id}/delete_task/{task_id}", response_model=dict)
async def remove_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token),
    current_member_id: str = Depends(get_current_member)
):
    """
    **Summary:**
    Delete a task from a project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `task_id` (str): The ID of the task to delete.
    - `db` (Session): The database session.
    - `verified_token` (bool): Dependency to verify the authentication token.
    - `current_member_id` (str): The ID of the member making the request.

    **Returns:**
    - `dict`: A message indicating the result of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        
        return await task_controller.delete_task(db, task_id, current_member_id)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)

    

@router.post("/project/{project_id}/add_attachments/{task_id}", status_code=status.HTTP_201_CREATED)
async def add_attachment_for_task(
    project_id:str,
    task_id: str,
    attachments: List[UploadFile] = File(...),
    task_comment_id: Optional[str] = None,
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Add attachments to a specific task within a project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `task_id` (str): The ID of the task to which the attachments are being added.
    - `attachments` (List[UploadFile]): A list of files to be uploaded as attachments.
    - `task_comment_id` (Optional[str]): The ID of the associated task comment, if any.
    - `current_member` (Members): The current logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `dict`: Details of the created attachments.
      Status code 201 if successful, 404 if the task is not found, 500 if an exception occurs.
    """

    try:
        # Validate attachments if any
        if attachments:
            validation_response = await validate_attachments(attachments)
            if validation_response:
                return validation_response

        task_exists = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()

        if not task_exists:
            return JSONResponse(status_code=404, content={"message":f"No task found for task ID: {task_id}"})
        
        return await task_controller.add_attachments(db, attachments, task_id, task_comment_id, current_member)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get(
    "/project/{project_id}/list_tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK
)
async def list_tasks(
    project_id: str,
    member_id: Optional[str] = Query(default=None, description="Comma-separated list of member IDs to filter tasks"),
    module_type: str = Query(default=None),
    verified_token: bool = Depends(verify_token),
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db),
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None)
):
    """
    **Summary:**
    List all tasks for a specific project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `member_id` (Optional[str]): Comma-separated list of member IDs to filter tasks.
    - `verified_token` (bool): Dependency to verify the authentication token.
    - `current_member` (str): The ID of the member making the request.
    - `db` (Session): The database session.
    - `page` (Optional[int]): The page number for pagination.
    - `page_size` (Optional[int]): The number of tasks per page for pagination.

    **Returns:**
    - `TaskResponse`: A list of tasks for the project.
      Status code 200 if successful, 401 if invalid credentials, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        tasks = await task_controller.get_all_tasks(project_id, member_id, module_type, current_member, db, page, page_size)

        return tasks

    except HTTPException as http_exc:
        # Catch HTTP exceptions and return them as they are
        
        raise http_exc

    except Exception as error:
        # Log the error and return a generic response
        logger.exception("Error while listing tasks")
        return JSONResponse(content={"message": "An error occurred while listing tasks"}, status_code=500)



@router.get("/project/{project_id}/get_task/{task_id}", status_code=status.HTTP_200_OK)
async def get_task(task_id: str, project_id:str, verified_token: bool = Depends(verify_token), db: Session = Depends(get_db)):
    """
    **Summary:**
    Retrieve a specific task by its ID.

    **Args:**
    - `task_id` (str): The ID of the task to retrieve.
    - `project_id` (str): The ID of the project associated with the task.
    - `verified_token` (bool): Dependency to verify the authentication token.
    - `db` (Session): The database session.

    **Returns:**
    - `TaskByIdResponse`: The details of the task.
      Status code 200 if successful, 404 if the task is not found, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        
        task_exists = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()

        if not task_exists:
            return JSONResponse(status_code=404, content={"message":f"No task found for task ID: {task_id}"})

        task = await task_controller.get_task_by_id(db, task_id)
        return task
    
    except ValueError as ve:
        return JSONResponse(content={"message": str(ve)}, status_code=500)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.patch("/project/{project_id}/update_task/{task_id}", status_code=status.HTTP_200_OK)
async def update_task_route(
    task_id: str,
    project_id: Optional[str],
    task_title: Optional[str] = Form(None),
    task_description: Optional[str] = Form(None),
    start_date: Optional[datetime] = Form(None),
    due_date: Optional[datetime] = Form(None),
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Update an existing task.

    **Args:**
    - `task_id` (str): The ID of the task to update.
    - `project_id` (Optional[str]): The new project ID, if updating the task's associated project.
    - `task_title` (Optional[str]): The new title of the task.
    - `task_description` (Optional[str]): The new description of the task.
    - `start_date` (Optional[datetime]): The new start date of the task.
    - `due_date` (Optional[datetime]): The new due date of the task.
    - `current_member` (Members): The current logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `dict`: The updated task details.
      Status code 200 if successful, 404 if the task is not found, 500 if an exception occurs.
    """
    try:
        task_exists = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
    
        if not task_exists:
            return JSONResponse(status_code=404, content={"message":f"No task found for task ID: {task_id}"})
        
        new_start_date = convert_to_timezone(start_date)
        new_due_date = convert_to_timezone(due_date)

        # Validate the start_date and due_date logic
        if new_start_date and new_due_date:
            if new_start_date > new_due_date:
                return JSONResponse(status_code=400, content={"message": "Start date cannot be greater than due date."})
        
        # If only one date is provided, retrieve the other from the task data
        if new_start_date and not new_due_date:
            new_due_date = task_exists.due_date
            new_due_date = convert_to_timezone(new_due_date)
        
        if new_due_date and not new_start_date:
            new_start_date = task_exists.start_date
            new_start_date = convert_to_timezone(new_start_date)
        
        if new_start_date and new_due_date:
            if new_start_date > new_due_date:
                return JSONResponse(status_code=400, content={"message": "Start date cannot be greater than due date."})


        update_data = TaskUpdateRequest(
            project_id=project_id,
            task_title=task_title,
            task_description=task_description,
            start_date=start_date,
            due_date=due_date,
        )

        updated_task = await task_controller.update_task(db, task_id, update_data, current_member)

        return updated_task

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/project/{project_id}/task_status", status_code=status.HTTP_200_OK)
@logger.catch
async def task_status(
    project_id:str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    **Summary:**
    List all task statuses for a specific project.

    **Args:**
    - `project_id` (str): The ID of the project.
    - `db` (Session): The database session.
    - `verified_token` (bool): Dependency to verify the authentication token.

    **Returns:**
    - `TaskStatusResponse`: A list of task statuses.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await task_controller.get_task_status(db)
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/project/{project_id}/change_task_status/{task_id}", status_code=200)
async def change_task_status(
    task_id: str,
    project_id: str,
    task_status_id: str = Query(..., description="The new status to assign to the task"),
    db: Session = Depends(get_db),
    current_member: Members = Depends(get_current_member)
):
    """
    **Summary:**
    Change the status of a specific task.

    **Args:**
    - `task_id` (str): The ID of the task to update.
    - `project_id` (str): The ID of the project associated with the task.
    - `task_status_id` (str): The new status ID to assign to the task.
    - `db` (Session): The database session.
    - `current_member` (Members): The current logged-in member.

    **Returns:**
    - `JSONResponse`: A message indicating the result of the operation.
      Status code 200 if successful, 404 if the task is not found, 500 if an exception occurs.
    """
    try:
        task_exists = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
        if not task_exists:
            return JSONResponse(status_code=404, content={"message":f"No task found for task ID: {task_id}"})

        result = await task_controller.update_task_status(
            db, task_id, task_status_id, current_member
        )

        return result

    except Exception as error:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/project/{project_id}/add_comment", status_code=status.HTTP_201_CREATED)
async def add_comment(
    project_id: str,
    task_id: str = Form(...),
    comment: str = Form(None),
    attachments: List[UploadFile] = File(None),
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Add a comment to a specific task, with optional attachments.

    **Args:**
    - `project_id` (str): The ID of the project associated with the task.
    - `task_id` (str): The ID of the task to which the comment is being added.
    - `comment` (str): The text of the comment.
    - `attachments` (List[UploadFile], optional): List of files to be uploaded with the comment.
    - `current_member` (Members): The current logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `dict`: Details of the created comment and its attachments.
      Status code 201 if successful, 404 if the task is not found, 400 if neither comment nor attachment is provided, 500 if an exception occurs.
    """
    try:
        if not comment and not attachments:
            return JSONResponse(status_code=400, content={"message": "Either comment or attachments must be provided."})
        
        # Validate attachments if any
        if attachments:
            validation_response = await validate_attachments(attachments)
            if validation_response:
                return validation_response

        task_exists = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
        if not task_exists:
            return JSONResponse(status_code=404, content={"message": f"No task found for task ID: {task_id}"})
        
        return await task_controller.create_comment(db, task_id, comment, attachments, current_member)
    
    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/project/{project_id}/get_comment/{comment_id}", response_model=TaskCommentResponse)
async def get_comment_by_id(
    project_id: str,
    comment_id: str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    **Summary:**
    Fetch a comment by its ID.

    **Args:**
    - `project_id` (str): The ID of the project associated with the comment.
    - `comment_id` (str): The ID of the comment to retrieve.
    - `db` (Session): The database session.
    - `verified_token` (bool): Token verification dependency.

    **Returns:**
    - `TaskCommentResponse`: The comment details along with attachments.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        
        return await task_controller.comment_by_id(db, comment_id)

    except Exception as error:
        raise error

        return JSONResponse(content={"message": str(error)}, status_code=500)

    
@router.patch("/project/{project_id}/update_comment/{comment_id}", status_code=status.HTTP_200_OK)
async def update_comment_api(
    project_id:str,
    comment_id: str,
    comment: str = Form(None),
    attachments: List[UploadFile] = File(None),
    deleted_attachment_ids: str = Form(None),
    current_member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Update a comment for a task.

    **Args:**
    - `project_id` (str): The ID of the project associated with the comment.
    - `comment_id` (str): The ID of the comment to update.
    - `new_comment` (str): The new content for the comment.
    - `attachments` (Optional[List[UploadFile]]): List of new files to be attached to the comment.
    - `current_member` (Members): The current logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `dict`: A response indicating the success or failure of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not comment and not attachments:
            return JSONResponse(status_code=400, content={"message": "Either comment or attachments must be provided."})
        
        # Validate attachments if any
        if attachments:
            validation_response = await validate_attachments(attachments)
            if validation_response:
                return validation_response

        return await task_controller.update_comment(db, comment_id, comment, attachments, deleted_attachment_ids, current_member)

    except HTTPException as http_err:
        return JSONResponse(content={"message": http_err.detail}, status_code=http_err.status_code)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.delete("/project/{project_id}/delete_comment/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_comment_api(
    project_id: str,
    comment_id: str,
    current_member = Depends(get_current_member),
    db: Session = Depends(get_db)
):
    """
    **Summary:**
    Delete a comment for a task.

    **Args:**
    - `project_id` (str): The ID of the project associated with the comment.
    - `comment_id` (str): The ID of the comment to delete.
    - `current_member` (Members): The current logged-in member.
    - `db` (Session): The database session.

    **Returns:**
    - `dict`: A response indicating the success or failure of the operation.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        return await task_controller.delete_comment(db, comment_id, current_member)

    except HTTPException as http_err:
        return JSONResponse(content={"message": http_err.detail}, status_code=http_err.status_code)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.put("/project/{project_id}/manage_members/{task_id}", status_code=status.HTTP_200_OK)
async def manage_members(
    task_id: str,
    project_id: str,
    member_id: str = Query(..., description="Comma-separated string of member IDs to manage"),
    action: str = Query(..., description="Action to perform: assign or unassign"),
    db: Session = Depends(get_db),
    current_member = Depends(get_current_member)
):
    """
    **Summary:**
    Manage the assignment of members to a task.

    **Args:**
    - `task_id` (str): The ID of the task to which members are being assigned or unassigned.
    - `project_id` (str): The ID of the project associated with the task.
    - `member_id` (str): Member ID to manage.
    - `action` (str): The action to perform, either 'assign' or 'unassign'.
    - `db` (Session): The database session.
    - `current_member` (Members): The current logged-in member.

    **Returns:**
    - `dict`: A response indicating the result of the operation.
      Status code 200 if successful, 400 if an invalid action is specified, 404 if the task is not found, and 500 if an exception occurs.
    """
    try:
        if action not in {"assign", "unassign"}:
            return JSONResponse(status_code=400, content={"message": "Invalid action. Must be 'assign' or 'unassign'."})

        task_exists = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
        if not task_exists:
            return JSONResponse(status_code=404, content={"message":f"No task found for task ID: {task_id}"})


        return await task_controller.manage_task_members(db, task_id, member_id, action, current_member, project_id)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.delete("/project/{project_id}/delete_attachment/{attachment_id}", response_model=dict)
async def remove_attachment(
    project_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token),
    current_member: str = Depends(get_current_member)
):
    """
    **Summary:**
    Delete a specific attachment from a project.

    **Args:**
    - `project_id` (str): The ID of the project to which the attachment belongs.
    - `attachment_id` (str): The ID of the attachment to delete.
    - `db` (Session): The database session.
    - `verified_token` (bool): Token verification dependency to ensure the request is authenticated.
    - `current_member_id` (str): The ID of the member making the request.

    **Returns:**
    - `dict`: A message indicating the result of the operation, with status code 200 if successful, or 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await task_controller.delete_attachment(db, attachment_id, current_member)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)



@router.get("/project/{project_id}/get_task_activities/{task_id}", response_model=TaskActivityResponse)
async def get_task_activities(
    project_id: str, 
    task_id: str,
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
    ):
    """
    **Summary:**
    Fetch all activities associated with a specific task.

    **Args:**
    - `project_id` (str): The ID of the project to which the task belongs.
    - `task_id` (str): The ID of the task for which activities are being fetched.
    - `db` (Session): The database session.
    - `verified_token` (bool): Token verification dependency to ensure the request is authenticated.

    **Returns:**
    - `TaskActivityResponse`: A list of activities related to the specified task.
      Status code 200 if successful, or 500 if an internal server error occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await task_controller.get_task_activities_by_task_id(db, task_id,page,page_size)

    except Exception as error:
        logger.exception(f"Error fetching task activities: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/project/{project_id}/list_comments/{task_id}", response_model=TaskCommentByTaskId)
async def list_comments_by_task_id(
    project_id: str,
    task_id: str,
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    **Summary:**
    List all comments associated with a specific task ID.

    **Args:**
    - `project_id` (str): The ID of the project associated with the task.
    - `task_id` (str): The ID of the task for which to retrieve comments.
    - `db` (Session): The database session.
    - `verified_token` (bool): Token verification dependency.

    **Returns:**
    - `TaskCommentByTaskId`: A list of comments related to the specified task.
      Status code 200 if successful, 500 if an exception occurs.
    """
    try:
        if not verified_token:
            return invalid_credential_resp
        
        return await task_controller.list_comments_by_task_id(db, task_id,page,page_size)
    

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)


@router.get("/project/{project_id}/list_attachments/{task_id}", response_model=PaginatedTaskAttachmentResponse)
async def get_attachments_by_task_id(
    project_id: str,
    task_id: str,
    page: Optional[int] = Query(default=None),
    page_size: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    List all attachments associated with a specific task ID with pagination.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await task_controller.list_attachments_by_task_id(db, task_id, page, page_size)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)
    

@router.get("/project/{project_id}/attachments/{attachment_id}/download", response_model=PaginatedTaskAttachmentResponse)
async def get_attachments_by_task_id(
    project_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    verified_token: bool = Depends(verify_token)
):
    """
    List all attachments associated with a specific task ID with pagination.
    """
    try:
        if not verified_token:
            return invalid_credential_resp

        return await task_controller.download_attachment(db, project_id, attachment_id)

    except Exception as error:
        return JSONResponse(content={"message": str(error)}, status_code=500)




@router.get(
    "/list_all_tasks",
    status_code=status.HTTP_200_OK
)
async def list_all_tasks(
    member_ids: Optional[str] = Query(default=None, description="Comma-separated list of member IDs to filter tasks"),
    project_id: str = Query(default=None, description="The ID of the project to filter tasks"),
    keyword: Optional[str] = Query(default=None, description="Keyword to filter tasks by title or description"),
    task_status: Optional[str] = Query(default=None, description="Filter tasks by their status"),
    duetype: Optional[str] = Query(
        default=None, 
        description="Filter tasks by their due type. Options are 'Past Due' for past-due tasks and 'Near Due' for tasks near their due date."
    ),
    verified_token: bool = Depends(verify_token),
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db),
    page: Optional[int] = Query(default=1, description="The page number for pagination (default is 1)"),
    page_size: Optional[int] = Query(default=5, description="The number of tasks per page for pagination (default is 5)")
):
    """
    **Summary:**
    List the latest tasks for specified members within a project.

    **Args:**
    - `member_ids` (Optional[str]): A comma-separated list of member IDs to filter tasks.
    - `project_id` (str): The ID of the project to filter tasks.
    - `keyword` (Optional[str]): A keyword to filter tasks by title or description.
    - `task_status` (Optional[str]): The status to filter tasks.
    - `duetype` (Optional[bool]): Filter tasks by their due type. Options are 'Past Due' for past-due tasks and 'Near Due' for tasks near their due date.
    - `verified_token` (bool): Dependency to verify the authentication token.
    - `current_member` (Members): The current member object making the request.
    - `db` (Session): The database session.
    - `page` (Optional[int]): The page number for pagination (default is 1).
    - `page_size` (Optional[int]): The number of tasks per page for pagination (default is 5).

    **Returns:**
    - `List[TaskResponse]`: A list of the latest tasks for the specified members.
      - Status code 200 if successful.
      - Status code 401 if the credentials are invalid.
      - Status code 500 if an exception occurs.
    """
    try:
        if not verified_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        is_past_due, is_near_due_date = None, None
        
        if duetype == "Past Due":
            is_past_due = True
        if duetype == "Near Due":
            is_near_due_date = True

        tasks = await task_controller.all_tasks(member_ids, project_id, keyword, task_status, is_past_due,is_near_due_date,current_member, db, page, page_size)

        return tasks

    except HTTPException as http_exc:
        # Catch HTTP exceptions and return them as they are
        raise http_exc

    except Exception as error:
        # Log the error and return a generic response
        logger.exception("Error while listing tasks")
        return JSONResponse(content={"message": "An error occurred while listing tasks"}, status_code=500)




# @router.get(
#     "/list_self_assigned_tasks",
#     status_code=status.HTTP_200_OK
# )
# async def list_self_assigned_tasks(
#     member_id: str =  Query(default=None),
#     role_id: str =  Query(default=None),
#     verified_token: bool = Depends(verify_token),
#     current_member: Members = Depends(get_current_member),
#     db: Session = Depends(get_db),
#     page: Optional[int] = Query(default=1),
#     page_size: Optional[int] = Query(default=5)
# ):
#     """
#     **Summary:**
#     List the latest tasks for a specific member.

#     **Args:**
#     - `member_id` (str): The ID of the member whose tasks are being requested.
#     - `role_id` (str): The Role ID of the member whose tasks are being requested.
#     - `verified_token` (bool): Dependency to verify the authentication token.
#     - `current_member` (Members): The current member object making the request.
#     - `db` (Session): The database session.
#     - `page` (Optional[int]): The page number for pagination (default is 1).
#     - `page_size` (Optional[int]): The number of tasks per page for pagination (default is 5).

#     **Returns:**
#     - `List[TaskResponse]`: A list of the latest tasks for the specified member.
#       - Status code 200 if successful.
#       - Status code 401 if the credentials are invalid.
#       - Status code 500 if an exception occurs.
#     """
#     try:
#         if not verified_token:
#             raise HTTPException(status_code=401, detail="Invalid credentials")

#         tasks = await task_controller.get_self_assigned_tasks(member_id, role_id, current_member, db, page, page_size)

#         return tasks

#     except HTTPException as http_exc:
#         # Catch HTTP exceptions and return them as they are
#         raise http_exc

#     except Exception as error:
#         # Log the error and return a generic response
#         logger.exception("Error while listing tasks")
#         return JSONResponse(content={"message": "An error occurred while listing tasks"}, status_code=500)


@router.get(
    "/list_self_assigned_tasks",
    status_code=status.HTTP_200_OK
)
async def list_self_assigned_tasks(
    member_id: str =  Query(default=None),
    role_id: str =  Query(default=None),
    module_type: str = Query(default=None),
    verified_token: bool = Depends(verify_token),
    current_member: Members = Depends(get_current_member),
    db: Session = Depends(get_db),
    page: Optional[int] = Query(default=1),
    page_size: Optional[int] = Query(default=5)
):
    """
    **Summary:**
    List the latest tasks for a specific member.

    **Args:**
    - `member_id` (str): The ID of the member whose tasks are being requested.
    - `role_id` (str): The Role ID of the member whose tasks are being requested.
    - `verified_token` (bool): Dependency to verify the authentication token.
    - `current_member` (Members): The current member object making the request.
    - `db` (Session): The database session.
    - `page` (Optional[int]): The page number for pagination (default is 1).
    - `page_size` (Optional[int]): The number of tasks per page for pagination (default is 5).

    **Returns:**
    - `List[TaskResponse]`: A list of the latest tasks for the specified member.
      - Status code 200 if successful.
      - Status code 401 if the credentials are invalid.
      - Status code 500 if an exception occurs.
    """
    try:
        if not verified_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # if module_type not in ["Estimation", "Project Management"]:
        #     raise HTTPException(status_code=401, detail="Invalid module type")

        tasks = await task_controller.get_self_assigned_tasks(member_id, role_id, module_type, current_member, db, page, page_size)

        return tasks

    except HTTPException as http_exc:
        # Catch HTTP exceptions and return them as they are
        raise http_exc

    except Exception as error:
        # Log the error and return a generic response
        logger.exception("Error while listing tasks")
        return JSONResponse(content={"message": "An error occurred while listing tasks"}, status_code=500)