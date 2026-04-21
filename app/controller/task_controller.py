from typing import List
from loguru import logger
from sqlalchemy.orm import Session
from models import task_status
from datetime import datetime
from models.project_task import ProjectTask
from schemas.task_schema import TaskInfo, MemberResponse, AttachmentResponse, TaskById,  TaskActivityInfo, TaskResponse,TaskCommentInfo
from models.task_members import TaskMembers
from models.task_attachments import TaskAttachments
from fastapi import HTTPException
from models.project_members import ProjectMembers
from models.members import Members
from models.task_comments import TaskComments
from models.member_role import MemberRole
from fastapi.responses import JSONResponse
from models.projects import Projects
from models.roles import Roles
from exceptions.http_exceptions import HTTPStatusException
from utils.common import delete_file, get_aws_full_path
from typing import List, Optional
from models.task_activity import TaskActivity
from sqlalchemy import func
from repositories.task_repositories import log_task_activity, get_task_status_name_by_id
from repositories.member_repositories import get_member_name_by_id
from sqlalchemy import and_, not_, or_
from schemas.task_schema import ProjectTaskCreateRequest, TaskUpdateRequest
from fastapi import UploadFile
import math
from utils.common import upload_to_s3, delete_from_s3, download_from_s3, check_task_completion_status
from fastapi.responses import StreamingResponse
from models.task_status import TaskStatus



async def add_task(
    db: Session, 
    task_data: ProjectTaskCreateRequest, 
    attachments,
    current_member: Members
) -> JSONResponse:
    """**Summary:**
    Add a new task to the database.

    **Args:**
    - `db` (Session): The database session.
    - `task_data` (ProjectTaskCreateRequest): The task data to be added.
    - `current_member`: The current member creating the task.

    **Returns:**
    - dict: The details of the created task.
    """
    try:
        print(">>>>", task_data)
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            # Check if project exists
            project = db.query(Projects).filter(Projects.id == task_data.project_id).first()
            if not project:
                return JSONResponse(status_code=404, content={"message": f"No projects found for project ID: {task_data.project_id}"})

            # Create a new task
            new_task = ProjectTask(
                project_id=task_data.project_id,
                task_status_id=task_data.task_status_id,
                task_title=task_data.task_title,
                task_description=task_data.task_description,
                start_date=task_data.start_date,
                due_date=task_data.due_date,
                is_estimation = task_data.is_estimation,
                created_by=current_member.id,
                created_at=datetime.now()
            )

            db.add(new_task)
            db.flush()

            if attachments is not None:
                for file in attachments:
                    task_attachment = TaskAttachments(
                        task_id=new_task.id,
                        file_name=file.filename,
                        file_type=file.content_type,
                        created_by=current_member.id
                    )
                    db.add(task_attachment)
                    db.flush()

                    # Claaing function "upload_to_s3" to upload the attachment to S3
                    upload_path = f"task_attachments/{new_task.id}/{task_attachment.id}"
                    file_path = await upload_to_s3(file, upload_path)
                    task_attachment.file_path = file_path

            # Add task members with valid roles
            if task_data.assigned_members:
                if task_data.assigned_members is None:
                    raise HTTPStatusException(status_code=404, detail=f"Please assign member to the task.")
                
                for member_id in task_data.assigned_members.split(','):
                    member_roles = db.query(MemberRole).filter(MemberRole.member_id == member_id).all()

                    if not member_roles:
                        raise HTTPStatusException(status_code=404, detail=f"No member roles found for member ID: {member_id}")
                    
                    if member_roles:
                        active_project_member = (
                            db.query(ProjectMembers)
                            .filter(
                                ProjectMembers.member_role_id.in_([role.id for role in member_roles]),
                                ProjectMembers.is_active == True,
                                ProjectMembers.project_id == task_data.project_id
                            )
                            .first()
                        )

                        if not active_project_member:
                            raise HTTPStatusException(status_code=404, detail=f"No roles found for member ID: {member_id} in project ID: {task_data.project_id}")

                        task_member = TaskMembers(
                            task_id=new_task.id,
                            member_id=member_id,
                            created_by=current_member.id
                        )
                        db.add(task_member)

            # Log the creation of a new task in the task_activity table.
            await log_task_activity(db, new_task.id, "Created task", current_member.id, details={"task_title": task_data.task_title})

        return JSONResponse(status_code=200, content={"task_id": new_task.id, "message": "Task Added Successfully", "status": "success"})

    except HTTPStatusException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})
    
    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        raise error

async def delete_task(db: Session, task_id: str, current_member: str):
    """
    Delete a task and its related data from the database.
    
    Args:
        db (Session): The database session.
        task_id (str): The ID of the task to delete.
        current_member (str): The ID of the member requesting the deletion.
    
    Returns:
        dict: A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            # If there is an active transaction, commit it
            db.commit()

        # Begin a transaction
        with db.begin():
            # Fetch the task
            task = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Check if the current member is an Admin or Project Manager
            is_admin_or_pm = (
                db.query(MemberRole)
                .join(Roles, Roles.id == MemberRole.role_id)
                .filter(
                    MemberRole.member_id == current_member.id,
                    MemberRole.active_role == 1,
                    Roles.name.in_(["Admin", "Project Manager"])
                )
                .first()
            )

            # Fetch assigned members for the task
            assigned_members = db.query(TaskMembers).filter(TaskMembers.task_id == task_id).all()

            # If the task has more than one assigned member, and the current member is not Admin or Project Manager, restrict deletion
            if len(assigned_members) > 1 and not is_admin_or_pm:
                raise HTTPException(status_code=403, detail="You cannot delete this task because it is assigned to multiple members")

            # Check if the task has an owner (created_by), and the current_member is not the owner
            if task.created_by != current_member.id and not is_admin_or_pm:
                raise HTTPException(status_code=403, detail="You are not authorized to delete this task")

            # Delete related task comments and their attachments
            comments = db.query(TaskComments).filter(TaskComments.task_id == task_id).all()
            for comment in comments:
                # Fetch and delete attachments associated with each comment
                comment_attachments = db.query(TaskAttachments).filter(TaskAttachments.task_comment_id == comment.id).all()
                for attachment in comment_attachments:
                    await delete_from_s3(attachment.file_path)  # Delete the attachment file from S3
                    db.delete(attachment)

                # Delete the comment itself
                db.delete(comment)

            # Delete related task attachments not associated with comments
            task_attachments = db.query(TaskAttachments).filter(TaskAttachments.task_id == task_id, TaskAttachments.task_comment_id.is_(None)).all()
            for attachment in task_attachments:
                
                # Delete file from S3
                await delete_from_s3(attachment.file_path)
                db.delete(attachment)

            # Delete related task members
            db.query(TaskMembers).filter(TaskMembers.task_id == task_id).delete()

            task_title = task.task_title
            # Log the deletion of a task in the task_activity table.
            await log_task_activity(db, task_id, "Deleted task", current_member.id, details={"task_title": task_title})

            # Finally, delete the task itself
            db.delete(task)

        return JSONResponse(status_code=200, content={"message": "Task and related data deleted successfully", "status": "success"})

    except HTTPException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred while deleting the task: {error}")
        raise error



async def add_attachments(db:Session,attachments:Optional[List[UploadFile]], task_id: str, task_comment_id:str, current_member: Members):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            file_names = []
            for upload_file in attachments:
                
                task_attachment = TaskAttachments(
                    task_id = task_id,
                    task_comment_id = task_comment_id,
                    file_name = upload_file.filename,
                    file_type = upload_file.content_type,
                    created_by = current_member.id
                )
                file_names.append(upload_file.filename)
                db.add(task_attachment)
                db.flush()
                # Upload task attachment to S3
                    
                upload_path = f"task_attachments/{task_id}/{task_attachment.id}"
                file_path = await upload_to_s3(upload_file, upload_path)
                task_attachment.file_path = file_path

            # Log the add attachments of a task in the task_activity table.
            await log_task_activity(db, task_id, "Added attachment", current_member.id, details={"file_name": ', '.join(file_names)})

        
        return JSONResponse(status_code=201, content={"attachment_id": task_attachment.id, "message": "attachements added.", "status": "success"})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def get_all_tasks(
    project_id: str,
    member_id: str,
    module_type: str,
    current_member: Members, 
    db: Session, 
    page: Optional[int] = None, 
    page_size: Optional[int] = None
) -> dict:
    """
    Fetch all tasks with their associated task members, attachments, and activity count.

    Args:
    - project_id (str): The ID of the project to fetch tasks for.
    - member_id (str): Comma-separated list of member IDs to filter tasks by.
    - db (Session): The database session.
    - page (Optional[int]): The page number for pagination.
    - page_size (Optional[int]): The number of items per page for pagination.

    Returns:
    - dict: A dictionary containing the paginated task data and pagination details.
    """
    try:
        # Check if the current member is an Admin or Project Manager
        # is_admin = (
        #     db.query(MemberRole)
        #     .join(Roles, Roles.id == MemberRole.role_id)
        #     .filter(
        #         MemberRole.member_id == current_member.id,
        #         MemberRole.active_role == 1,
        #         Roles.name.in_(["Admin"])
        #     )
        #     .first()
        # )

        # Base query to fetch tasks
        query = (
            db.query(
                ProjectTask,
                func.count(TaskActivity.id).label('task_activity_count')
            )
            .outerjoin(TaskMembers, ProjectTask.id == TaskMembers.task_id)
            .outerjoin(TaskActivity, (ProjectTask.id == TaskActivity.task_id) & (TaskActivity.is_new == True))
            .filter(ProjectTask.project_id == project_id)
            .group_by(ProjectTask.id, TaskMembers.id)
            .order_by(ProjectTask.created_at.desc())
        )

        if module_type == "Estimation":
                is_estimation = True
        else:
            is_estimation = False
        query = query.filter(ProjectTask.is_estimation == is_estimation)
        
        if member_id:
            member_ids = member_id.split(",")
            query = query.filter(TaskMembers.member_id.in_(member_ids))
        # Calculate the total number of items
        item_count = query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            page = 1
            page_size = item_count

        task_data = query.all()

        response = []
        task_id_lookups = {}

        # For each task, fetch the assigned members
        for task, task_activity_count in task_data:
            assigned_members_query = (
                db.query(Members, TaskMembers)
                .join(TaskMembers, Members.id == TaskMembers.member_id)
                .filter(TaskMembers.task_id == task.id)
            )
            assigned_members_data = assigned_members_query.all()

            # Prepare the list of assigned members for the task
            assigned_members = [
                MemberResponse(
                    member_id=member_data.id,
                    member_name=f"{member_data.first_name} {member_data.last_name}"
                )
                for member_data, task_member_data in assigned_members_data
            ]

            # Call the utility function to determine task status
            task_status_info = check_task_completion_status(
                start_date=task.start_date,
                due_date=task.due_date,
                completed_date=task.completed_date if task.completed_date else None
            )

            start_date_formatted = task.start_date.strftime("%b %d, %Y") if task.start_date else None
            due_date_formatted = task.due_date.strftime("%b %d, %Y") if task.due_date else None

            # Check if the due date has passed
            status = await get_task_status_name_by_id(db, task.task_status_id)
            past_due = False
            if status != "Completed":
                if task.due_date and task.due_date.date() < datetime.now().date():
                    past_due = True
            else:
                if task.due_date and task.completed_date and task.completed_date.date() > task.due_date.date():
                    past_due = True

            task_response = TaskInfo(
                id=task.id,
                project_id=task.project_id if task.project_id else "",
                task_status_id=task.task_status_id if task.task_status_id else "",
                task_status=status,
                task_title=task.task_title,
                task_description=task.task_description,
                start_date=start_date_formatted,
                due_date=due_date_formatted,
                assigned_members=assigned_members,
                task_activity_count=task_activity_count,
                past_due=past_due,
                task_completion_status_info=task_status_info
            )

            response.append(task_response)
            task_id_lookups[task.id] = len(response) - 1

        # Calculate page count
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        return {
            "data": response, 
            "page_count": page_count, 
            "item_count": item_count,
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An unexpected error occurred while fetching tasks: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")



async def get_task_by_id(db: Session, task_id: str):
    """
    Fetch a task by its ID, including assigned members and their roles.

    Args:
    - db (Session): The database session.
    - task_id (str): The ID of the task to retrieve.

    Returns:
    - A dictionary containing task details, members, roles, and other related information.
    """
    try:
        # Query task data with assigned members and their roles
        task_data = (
            db.query(ProjectTask, Members, TaskMembers, Roles)
            .outerjoin(TaskMembers, ProjectTask.id == TaskMembers.task_id)
            .outerjoin(Members, TaskMembers.member_id == Members.id)
            .outerjoin(MemberRole, MemberRole.member_id == Members.id)
            .outerjoin(Roles, MemberRole.role_id == Roles.id)
            .filter(ProjectTask.id == task_id)
            .all()
        )

        if not task_data:
            raise ValueError(f"Task with ID {task_id} not found.")

        # Fetch task activity count
        task_activity_count = db.query(func.count(TaskActivity.id)).filter(
            TaskActivity.task_id == task_id,
            TaskActivity.is_new == True
        ).scalar()

        # Fetch total comment count
        total_comment_count = db.query(func.count(TaskComments.id)).filter(
            TaskComments.task_id == task_id
        ).scalar()

        task_response = None
        assigned_members_dict = {}

        for task, member, task_member, role in task_data:
            if task_response is None:
                # Determine if the due date has passed
                past_due = False
                if task.due_date and task.due_date < datetime.now():
                    past_due = True

                # Build the initial task response
                task_response = {
                    "id": task.id,
                    "project_id": task.project_id if task.project_id else "",
                    "task_status_id": task.task_status_id if task.task_status_id else "",
                    "task_title": task.task_title,
                    "task_description": task.task_description,
                    "start_date": task.start_date.isoformat() if task.start_date else None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "owner_id": task.created_by,
                    "task_activity_count": task_activity_count,
                    "total_comment_count":total_comment_count,
                    "past_due": past_due,
                    "assigned_members": []
                }

            if member and task_member:
                # Add member if not already in dict
                if task_member.member_id not in assigned_members_dict:
                    assigned_members_dict[task_member.member_id] = {
                        "member_id": task_member.member_id,
                        "member_name": f"{member.first_name} {member.last_name}",
                        "roles": []
                    }

                # Append the role to the member's roles list
                if role:
                    assigned_members_dict[task_member.member_id]["roles"].append({
                        "id": role.id,
                        "role_name": role.name
                    })

        # Convert assigned_members_dict to a list for the response
        task_response["assigned_members"] = [
            {
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "roles": member["roles"]
            }
            for member in assigned_members_dict.values()
        ]

        return {"data": task_response, "status": "success"}

    except Exception as error:
        logger.exception(f"An unexpected error occurred while fetching the task: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def update_task(db: Session, task_id: str, update_data:TaskUpdateRequest, current_member: Members):
    """
    Update an existing task with the provided data.

    Args:
        db (Session): The database session.
        task_id (str): The ID of the task to update.
        update_data (TaskUpdateRequest): The data to update the task with.

    Returns:
        dict: The updated task details.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
 
        # Begin a transaction
        with db.begin():
            # Update task details
            task = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
            if not task:
                raise HTTPStatusException(status_code=404, detail=f"Task not found")
            
            updated_fields = {}

            if update_data.project_id is not None:
                task.project_id = update_data.project_id

            if update_data.task_title is not None:
                updated_fields['task_title'] = (task.task_title, update_data.task_title)
                task.task_title = update_data.task_title

            if update_data.task_description is not None:
                updated_fields['task_description'] = (task.task_description, update_data.task_description)
                task.task_description = update_data.task_description

            if update_data.start_date is not None:
                updated_fields['start_date'] = (task.start_date, update_data.start_date)
                task.start_date = update_data.start_date

            if update_data.due_date is not None:
                updated_fields['due_date'] = (task.due_date, update_data.due_date)
                task.due_date = update_data.due_date

            task.updated_by = current_member.id


            # Log the update of a task in the task_activity table.
            activity_id = await log_task_activity(db, task.id, "Updated task", current_member.id, details={
                "changes": updated_fields
            })

            return JSONResponse(status_code=200, content={"task_id": task.id, "activity_id": activity_id, "message": "Task Updated Successfully", "status": "success"})


    except HTTPStatusException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})

    except Exception as e:
        db.rollback()
        logger.exception(f"An unexpected error occurred while updating the task: {e}")
        raise e




async def get_task_status(db: Session):
    """
    Fetch all task statuses.

    Args:
    - db (Session): The database session.

    Returns:
    - dict: A dictionary containing task statuses and a success message.
    """
    try:
        task_status_data = db.query(task_status.TaskStatus).all()
        
        response = [
            {
                "id": task.id,
                "status": task.status,
                "created_at": task.created_at.strftime("%d/%m/%Y %H:%M:%S") if task.created_at else None,
                "created_by": task.created_by
            }
            for task in task_status_data
        ]
        
        return {"data": response, "status": "success"}
    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")



async def create_comment(db:Session,task_id: str,comment: str,attachments:Optional[List[UploadFile]],current_member: Members):
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        
        with db.begin():

            new_comment = TaskComments(
                task_id = task_id,
                comment = comment,
                created_by = current_member.id
            )

            db.add(new_comment)
            db.flush()

            if attachments is not None:
                for attachment in attachments:

                    new_attachment = TaskAttachments(
                        task_id = task_id,
                        task_comment_id = new_comment.id,
                        file_name = attachment.filename,
                        file_type = attachment.content_type,
                        created_by = current_member.id
                    )

                    db.add(new_attachment)
                    db.flush()

                    # Claaing function "upload_to_s3" to upload the attachment to S3
                    upload_path = f"task_attachments/{task_id}/{new_comment.id}/{new_attachment.id}"
                    file_path = await upload_to_s3(attachment, upload_path)
                    new_attachment.file_path = file_path
        
            # Log the add comment of a task in the task_activity table.
            await log_task_activity(db, task_id, "Commented", current_member.id)

        
        return JSONResponse(status_code=201, content={"comment_id": new_comment.id,"message": "Comment Added Sucessfully", "status": "success"})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        raise error


async def comment_by_id(db: Session, comment_id: str):
    """
    Fetch a comment by its ID.

    Args:
    - db (Session): The database session.
    - comment_id (str): The ID of the comment to retrieve.

    Raises:
    - ValueError: If the comment is not found.
    """
    try:
        comment_data = (
            db.query(TaskComments, TaskAttachments, Members)
            .outerjoin(TaskAttachments, onclause=TaskComments.id == TaskAttachments.task_comment_id)
            .outerjoin(Members, onclause=TaskComments.created_by == Members.id)
            .filter(TaskComments.id == comment_id)
            .all()
        )

        if not comment_data:
            raise ValueError(f"Comment with ID {comment_id} not found.")

        comment_dict = {}
        for comment, comment_attachment, creator in comment_data:
            if comment.id not in comment_dict:
                created_by_name = f"{creator.first_name} {creator.last_name}" if creator else None
                member_id = creator.id if creator else None
                comment_dict[comment.id] = TaskCommentInfo(
                    id=comment.id,
                    task_id=comment.task_id,
                    created_by_name=created_by_name,
                    member_id=member_id,
                    created_at=comment.created_at.strftime("%b %d, %Y, %H:%M"),
                    comment=comment.comment,
                    comment_attachments=[]
                )

            if comment_attachment:
                attachment_response = AttachmentResponse(
                    id=comment_attachment.id,
                    task_comment_id = comment_attachment.task_comment_id,
                    file_name=comment_attachment.file_name,
                    file_path=comment_attachment.file_path,
                    file_type=comment_attachment.file_type
                )
                comment_dict[comment.id].comment_attachments.append(attachment_response)

        return {"data": comment_dict[comment_id], "status": "success"}
    
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    
    except Exception as error:
        logger.exception(f"An unexpected error occurred while fetching the comment: {error}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


async def update_comment(
    db: Session, 
    comment_id: str, 
    new_comment: str, 
    attachments:Optional[List[UploadFile]],
    deleted_attachment_ids: Optional[str],
    current_member: Members
):
    """
    Update a comment and its attachments.

    Args:
    - db (Session): The database session.
    - comment_id (str): The ID of the comment to update.
    - comment (str): The new comment content.
    - attachments (List[UploadFile]): New attachments to associate with the comment.
    - current_member: The member making the request.

    Returns:
    - dict: A response indicating the success of the operation.
    """
    try:

        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        
        with db.begin():

            comment = db.query(TaskComments).filter(TaskComments.id == comment_id).first()

            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")

            comment.comment = new_comment
            comment.created_by = current_member.id

            if attachments:
                for attachment in attachments:

                    new_attachment = TaskAttachments(
                        task_id = comment.task_id,
                        task_comment_id = comment.id,
                        file_name = attachment.filename,
                        file_type = attachment.content_type,
                        created_by = current_member.id
                    )

                    db.add(new_attachment)
                    db.flush()

                    # Claaing function "upload_to_s3" to upload the attachment to S3
                    upload_path = f"task_attachments/{comment.task_id}/{new_comment}/{new_attachment.id}"
                    file_path = await upload_to_s3(attachment, upload_path)
                    new_attachment.file_path = file_path
            
            # Process deleted attachments
            if deleted_attachment_ids:
                attachment_ids = [id.strip() for id in deleted_attachment_ids.split(',')]
                for attachment_id in attachment_ids:
                    attachment = db.query(TaskAttachments).filter(TaskAttachments.id == attachment_id).first()
                    if attachment:
                        await delete_from_s3(attachment.file_path)

                        db.delete(attachment)
                        
            await log_task_activity(db, comment.task_id, "Updated comment", current_member.id)

    
        return JSONResponse(status_code=200, content={"comment_id": comment.id, "message": "Comment updated successfully", "status": "success"})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred: {error}")
        raise error




async def delete_comment(db: Session, comment_id: str, current_member:Members):
    """
    Delete a comment and its attachments.

    Args:
    - db (Session): The database session.
    - comment_id (str): The ID of the comment to delete.
    - current_member: The member making the request.

    Returns:
    - dict: A response indicating the success of the operation.
    """
    try:

        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        
        with db.begin():
            comment = db.query(TaskComments).filter(TaskComments.id == comment_id).first()

            if not comment:
                raise HTTPException(status_code = 404, detail="Comment not found")

            attachments = db.query(TaskAttachments).filter(TaskAttachments.task_comment_id == comment_id).all()
            if attachments:
                attachment_ids = []
                for attachment in attachments:
                    attachment_ids.append(attachment.id)
                    await delete_from_s3(attachment.file_path)
                
                db.query(TaskAttachments).filter(TaskAttachments.id.in_(attachment_ids)).delete()
            
            task_id = comment.task_id

            db.delete(comment)

            # Log the update comment of a task in the task_activity table.
            await log_task_activity(db, task_id, "Deleted comment", current_member.id)

        return JSONResponse(status_code=200, content={"comment_id": comment.id,"message": "Comment deleted successfully", "status": "success"})

    except Exception as error:
        logger.exception(f"An unexpected error occurred: {error}")
        raise error



async def manage_task_members(
    db: Session,
    task_id: str,
    member_id: str,
    action: str,
    current_member: Members,
    project_id: str
) -> dict:
    """
    **Summary:**
    Manage (assign or unassign) task members in a project.

    **Args:**
    - `db` (Session): The database session.
    - `task_id` (str): The ID of the task.
    - `member_id` (str): The ID of the member to assign or unassign.
    - `action` (str): The action to perform ("assign" or "unassign").
    - `current_member` (Members): The current member performing the action.
    - `project_id` (str): The ID of the project.

    **Returns:**
    - dict: A message indicating whether the action was successful.
    """
    try:
        if db.in_transaction():
            # If there is any active transaction, commit it
            db.commit()

        # Begin a transaction
        with db.begin():
            task_data = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
            
            if action == "assign":
                # Check if the member is already assigned to this task
                existing_assignment = (
                    db.query(TaskMembers)
                    .filter(TaskMembers.task_id == task_id, TaskMembers.member_id == member_id)
                    .first()
                )

                if existing_assignment:
                    return JSONResponse(
                        status_code=400, 
                        content={"message": "Member is already assigned to this task", "status": "error"}
                    )

                # Fetch member roles
                member_roles = db.query(MemberRole).filter(MemberRole.member_id == member_id).all()

                if not member_roles:
                    raise HTTPStatusException(status_code=404, detail=f"No member roles found for member ID: {member_id}")

                # Validate active project membership with a valid role
                active_project_member = (
                    db.query(ProjectMembers)
                    .filter(
                        ProjectMembers.member_role_id.in_([role.id for role in member_roles]),
                        ProjectMembers.is_active == True,
                        ProjectMembers.project_id == project_id
                    )
                    .first()
                )

                if not active_project_member:
                    raise HTTPStatusException(status_code=404, detail=f"No roles found for member ID: {member_id} in project ID: {project_id}")

                # Assign the member to the task
                task_member = TaskMembers(
                    task_id=task_id,
                    member_id=member_id,
                    created_by=current_member.id,
                    created_at=datetime.now()
                )

                db.add(task_member)
                member_name = await get_member_name_by_id(db, member_id)
                # Log the assign member of a task in the task_activity table.
                await log_task_activity(db, task_id, "Assigned task", current_member.id, details={"assigned_to": member_name})

            elif action == "unassign":
                # Unassign the member from the task
                task_member = (
                    db.query(TaskMembers)
                    .filter(TaskMembers.task_id == task_id, TaskMembers.member_id == member_id)
                    .first()
                )

                if task_member:
                    member_name = await get_member_name_by_id(db, member_id)
                    # Log the unassign member of a task in the task_activity table.
                    await log_task_activity(db, task_id, "Unassigned task", current_member.id, details={"unassigned_from": member_name})
                    db.delete(task_member)

        return JSONResponse(status_code=201, content={"message": f"Member {action}ed successfully", "status": "success"})

    except HTTPStatusException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred while managing members: {error}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while managing members")




async def update_task_status(
    db: Session,
    task_id: str,
    task_status_id: str,
    current_member: Members
) -> dict:
    """
    Update the status of a task.

    Args:
        db (Session): The database session.
        task_id (str): The ID of the task to update.
        new_status (str): The new status to assign to the task.
        current_member_id (str): The ID of the member making the change.

    Returns:
        dict: A dictionary with the status code and content for the response.
    """
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()

       # Begin a transaction 
        with db.begin():
            task = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
            
            from_status = await get_task_status_name_by_id(db, task.task_status_id)
            if not task:
                return {"status_code": 404, "content": {"message": "Task not found"}}

            status_record = db.query(task_status.TaskStatus).filter(task_status.TaskStatus.id == task_status_id).first()
            to_status = await get_task_status_name_by_id(db, status_record.id)
            if not status_record:
                return {"status_code": 400, "content": {"message": "Invalid status"}}

            if to_status == "Completed":
                task.completed_date = datetime.now()
            else:
                task.completed_date = None


            task.task_status_id = status_record.id
            

            # Log update status of a task in the task_activity table.
            await log_task_activity(db, task.id, "Changed status", current_member.id, details={"from_status": from_status, "to_status": to_status})

        return JSONResponse(status_code=200, content={"message": "Task status updated successfully", "status": "success"})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred while updating task status: {error}")
        return {"status_code": 500, "content": {"message": "Internal Server Error"}}



async def delete_attachment(db: Session, attachment_id: str, current_member: Members):
    """
    Delete an attachment from the database.

    Args:
        db (Session): The database session.
        attachment_id (str): The ID of the attachment to delete.
        current_member_id (str): The ID of the member requesting the deletion.

    Returns:
        dict: A message indicating the result of the operation.
    """
    try:
        if db.in_transaction():
            db.commit()

        with db.begin():
            attachment = db.query(TaskAttachments).filter(TaskAttachments.id == attachment_id).first()
            if not attachment:
                raise HTTPException(status_code=404, detail="Attachment not found")
            
            filename = attachment.file_name
            file_path = attachment.file_path
            task_id = attachment.task_id
            db.delete(attachment)

            await delete_from_s3(file_path)
            
            # Log delete attachment of a task in the task_activity table.
            await log_task_activity(db, task_id, "Deleted attachment", current_member.id, details={"file_name": filename})

        return JSONResponse(status_code=200, content={"message": "Attachment deleted successfully", "status": "success"})

    except HTTPException as http_error:
        db.rollback()
        return JSONResponse(status_code=http_error.status_code, content={"message": http_error.detail})

    except Exception as error:
        db.rollback()
        logger.exception(f"An unexpected error occurred while deleting the attachment: {error}")
        raise error



async def get_task_activities_by_task_id(
    db: Session, 
    task_id: str, 
    page: Optional[int] = None, 
    page_size: Optional[int] = None
):
    """
    Fetch task activities filtered by task ID, including the creator's name, with optional pagination.

    Args:
    - db (Session): The database session.
    - task_id (str): The ID of the task to filter activities by.
    - page (Optional[int]): The page number for pagination (default: None).
    - page_size (Optional[int]): The number of items per page for pagination (default: None).

    Returns:
    - dict: A dictionary containing the paginated task activities, page count, item count, and status.
    """
    try:
        query = (
            db.query(TaskActivity, Members)
            .outerjoin(Members, TaskActivity.created_by == Members.id)
            .filter(TaskActivity.task_id == task_id)
            .order_by(TaskActivity.created_at.desc())
        )

        total_activities = query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            offset = 0
            page_size = total_activities if total_activities else 1
            page = 1

        task_activities = query.all()

        task_activity_responses = [
            TaskActivityInfo(
                id=activity.id,
                task_id=activity.task_id,
                activity=activity.activity,
                created_at=activity.created_at.strftime("%b %d, %Y, %H:%M"),
                created_by=activity.created_by,
                is_new=activity.is_new,
                member_name=f"{member.first_name} {member.last_name}" if member else None
            )
            for activity, member in task_activities
        ]

        # Calculate page count
        page_count = math.ceil(total_activities / page_size) if page_size > 0 else 0

        return {
            "data": task_activity_responses,
            "page_count": page_count,
            "item_count": total_activities,
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An error occurred while fetching task activities: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def list_comments_by_task_id(
    db: Session, 
    task_id: str,
    page: Optional[int] = None, 
    page_size: Optional[int] = None
):
    """
    Fetch all comments filtered by task ID, including any attachments, with optional pagination.

    Args:
    - db (Session): The database session.
    - task_id (str): The ID of the task to filter comments by.
    - page (Optional[int]): The page number for pagination.
    - page_size (Optional[int]): The number of items per page for pagination.

    Returns:
    - dict: A dictionary containing the paginated comments, page count, item count, and status.
    """
    try:
        query = (
            db.query(TaskComments, Members)
            # .outerjoin(TaskAttachments, onclause=TaskComments.id == TaskAttachments.task_comment_id)
            .outerjoin(Members, onclause=TaskComments.created_by == Members.id)
            .filter(TaskComments.task_id == task_id)
            .order_by(TaskComments.created_at.desc())
        )

        total_comments = query.count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            offset = 0
            page_size = total_comments if total_comments else 1
            page = 1

        comments_data = query.all()

        comment_dict = {}
        for comment, creator in comments_data:
            if comment.id not in comment_dict:
                created_by_name = f"{creator.first_name} {creator.last_name}" if creator else None
                member_id = creator.id if creator else None
                comment_dict[comment.id] = TaskCommentInfo(
                    id=comment.id,
                    task_id=comment.task_id,
                    created_at=comment.created_at.strftime("%b %d, %Y, %H:%M"),
                    created_by_name=created_by_name,
                    member_id=member_id,
                    comment=comment.comment,
                    comment_attachments=[]
                )

            for attachment in comment.task_attachments:
                print(attachment.to_dict)
                if attachment:
                    attachment_response = AttachmentResponse(
                        id=attachment.id,
                        task_comment_id=attachment.task_comment_id,
                        file_name=attachment.file_name,
                        file_path=attachment.file_path,
                        file_type=attachment.file_type
                    )
                comment_dict[comment.id].comment_attachments.append(attachment_response)

        # Calculate page count
        page_count = math.ceil(total_comments / page_size) if page_size > 0 else 0

        # Return the list of comments
        response = list(comment_dict.values())
        return {
            "data": response,
            "page_count": page_count,
            "item_count": total_comments,
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An error occurred while fetching comments: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def list_attachments_by_task_id(
    db: Session, 
    task_id: str, 
    page: Optional[int] = None, 
    page_size: Optional[int] = None
):
    try:
        # Set the limit depending on the pagination info
        if page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size
        else:
            skip = 0
            limit = db.query(TaskAttachments).filter(TaskAttachments.task_id == task_id).count()
            page = 1

        # Query data with filters
        query = db.query(TaskAttachments).filter(TaskAttachments.task_id == task_id)
        
        # Order data, apply pagination, and retrieve all matching records
        attachments = query.order_by(TaskAttachments.created_at.asc()).offset(skip).limit(limit).all()
        
        if page_size is None:
            page_size = len(attachments)
        
        # Getting the total number of items count
        total_attachments = query.count()
        page_count = math.ceil(total_attachments / page_size) if page_size > 0 else 0
        item_count = total_attachments if page_count > 0 else 0

        attachment_responses = [
            {
                "id": attachment.id,
                "task_id": attachment.task_id,
                "task_comment_id": attachment.task_comment_id,
                "file_name": attachment.file_name,
                "file_path": get_aws_full_path(attachment.file_path) if attachment.file_path else None,
                "file_type": attachment.file_type
            }
            for attachment in attachments
        ]

        return {
            "data": attachment_responses,
            "page_count": page_count,
            "item_count": item_count,
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An error occurred while fetching attachments: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

async def download_attachment(
    db: Session, 
    project_id: str, 
    attachment_id: str
):
    try:
        # Retrieve the attachment from the database
        attachment = db.query(TaskAttachments).get(attachment_id)

        # Check if attachment exists
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # File path in S3
        file_path = attachment.file_path

        file_stream, content_type, filename = download_from_s3(file_path)
    
        # Return the file as a streaming response
        return StreamingResponse(file_stream, media_type=content_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
    
    except HTTPException as http_error:
        # Rethrow HTTP exceptions without additional logging
        raise http_error
    
    except Exception as error:
        print(str(error))
        logger.exception(f"An error occurred while downloading attachment {attachment_id} for project {project_id}: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")



async def all_tasks(
    member_ids: Optional[str],
    project_id: Optional[str],
    keyword: Optional[str],
    task_status: Optional[str],
    is_past_due: Optional[bool],
    is_near_due_date: Optional[bool],
    current_member: Members, 
    db: Session, 
    page: Optional[int] = 1, 
    page_size: Optional[int] = 5
) -> dict:
    """
    Fetch all tasks with their associated task members, attachments, and activity count.

    Args:
    - member_ids (Optional[str]): A comma-separated list of member IDs to filter tasks.
    - project_id (Optional[str]): The ID of the project to filter tasks.
    - keyword (Optional[str]): A keyword to filter tasks by title or description.
    - task_status (Optional[str]): The status to filter tasks.
    - current_member (Members): The current member's information.
    - db (Session): The database session.
    - page (Optional[int]): The page number for pagination (default is 1).
    - page_size (Optional[int]): The number of items per page for pagination (default is 5).

    Returns:
    - dict: A dictionary containing the paginated task data and pagination details.
    """
    try:
        query = (
            db.query(
                ProjectTask.id,
                ProjectTask.project_id,
                Projects.name,
                ProjectTask.task_status_id,
                ProjectTask.task_title,
                ProjectTask.task_description,
                ProjectTask.start_date,
                ProjectTask.due_date,
                ProjectTask.completed_date,
                ProjectTask.created_at,
                ProjectTask.created_by,
                ProjectTask.updated_at,
                ProjectTask.updated_by,
            )
            .outerjoin(Projects, Projects.id == ProjectTask.project_id)
            .outerjoin(ProjectMembers, Projects.id == ProjectMembers.project_id)
            .outerjoin(TaskMembers, ProjectTask.id == TaskMembers.task_id)
            .outerjoin(TaskStatus, TaskStatus.id == ProjectTask.task_status_id)
            .group_by(ProjectTask.id, Projects.id)
            .order_by(ProjectTask.created_at.desc())
        )

        if member_ids:
            member_id_list = member_ids.split(',')
            query = query.filter(TaskMembers.member_id.in_(member_id_list))

        if project_id:
            query = query.filter(ProjectTask.project_id == project_id)

        if keyword:
            query = query.filter(
                or_(
                    ProjectTask.task_title.ilike(f"%{keyword}%"),
                    ProjectTask.task_description.ilike(f"%{keyword}%")
                )
            )

        if task_status:
            query = query.filter(TaskStatus.status == task_status)
        
        if is_past_due is not None:
            query = query.filter(ProjectTask.is_past_due == is_past_due)

        if is_near_due_date is not None:
            query = query.filter(ProjectTask.is_near_due_date == is_near_due_date)


        # Calculate the total number of items
        item_count = query.distinct().count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            page = 1
            page_size = item_count

        task_data = query.all()

        response = []
        for task in task_data:
            due_date_formatted = task.due_date.strftime("%b %d, %Y") if task.due_date else None

            assigned_members_query = (
                db.query(Members, TaskMembers)
                .join(TaskMembers, Members.id == TaskMembers.member_id)
                .filter(TaskMembers.task_id == task.id)
            )
            assigned_members_data = assigned_members_query.all()

            # Prepare the list of assigned members for the task
            assigned_members = [
                    {
                    "member_id":member_data.id,
                    "member_name":f"{member_data.first_name} {member_data.last_name}"
                    }
            
                for member_data, task_member_data in assigned_members_data
            ]

            # Check if the due date has passed
            status = await get_task_status_name_by_id(db, task.task_status_id)
            past_due = False
            if status != "Completed":
                if task.due_date and task.due_date.date() < datetime.now().date():
                    past_due = True
            else:
                if task.due_date and task.completed_date and task.completed_date.date() > task.due_date.date():
                    past_due = True

            # Directly creating a dictionary instead of using TaskInfo
            task_response = {
                "id": task.id,
                "project_id": task.project_id if task.project_id else "",
                "project_name": task.name,
                "task_status": status,
                "task_title": task.task_title,
                "assigned_members":assigned_members,
                "due_date": due_date_formatted,
                "past_due": past_due,
            }

            response.append(task_response)

        # Calculate page count
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        return {
            "data": response, 
            "page_count": page_count,
            "item_count": item_count, 
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An unexpected error occurred while fetching tasks: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")


# async def get_self_assigned_tasks(
#     member_id: str,
#     role_id: str,
#     current_member: Members, 
#     db: Session, 
#     page: Optional[int] = 1, 
#     page_size: Optional[int] = 5
# ) -> dict:
#     """
#     Fetch all tasks with their associated task members, attachments, and activity count.

#     Args:
#     - member_id (str): The ID of the member to fetch tasks for.
#     - current_member (Members): The current member's information.
#     - db (Session): The database session.
#     - page (Optional[int]): The page number for pagination.
#     - page_size (Optional[int]): The number of items per page for pagination.

#     Returns:
#     - dict: A dictionary containing the paginated task data and pagination details.
#     """
#     try:
            
#         query = (
#             db.query(
#                 ProjectTask.id,
#                 ProjectTask.project_id,
#                 Projects.name,
#                 ProjectTask.task_status_id,
#                 ProjectTask.task_title,
#                 ProjectTask.task_description,
#                 ProjectTask.start_date,
#                 ProjectTask.due_date,
#                 ProjectTask.completed_date,
#                 ProjectTask.created_at,
#                 ProjectTask.created_by,
#                 ProjectTask.updated_at,
#                 ProjectTask.updated_by,
#             )
#             .outerjoin(Projects, Projects.id == ProjectTask.project_id)
#             .outerjoin(ProjectMembers, Projects.id == ProjectMembers.project_id)
#             .outerjoin(TaskMembers, ProjectTask.id == TaskMembers.task_id)
#             .group_by(ProjectTask.id, Projects.id)
#             .order_by(ProjectTask.created_at.desc())
#         )

#         if member_id and role_id:
#             member_role_id = db.query(MemberRole.id).filter(MemberRole.member_id == member_id, MemberRole.role_id == role_id).first()
#             query = query.filter(ProjectMembers.member_role_id == member_role_id[0], TaskMembers.member_id == member_id)


#         # Calculate the total number of items
#         item_count = query.distinct().count()

#         # Apply pagination if page and page_size are provided
#         if page is not None and page_size is not None:
#             offset = (page - 1) * page_size
#             query = query.offset(offset).limit(page_size)
#         else:
#             page = 1
#             page_size = item_count

#         task_data = query.all()

#         response = []
#         task_id_lookups = {}

#         for task in task_data:
#             due_date_formatted = task.due_date.strftime("%b %d, %Y") if task.due_date else None

#             # Check if the due date has passed
#             status = await get_task_status_name_by_id(db, task.task_status_id)
#             past_due = False
#             if status != "Completed":
#                 if task.due_date and task.due_date.date() < datetime.now().date():
#                     past_due = True
#             else:
#                 if task.due_date and task.completed_date and task.completed_date.date() > task.due_date.date():
#                     past_due = True

#             # Directly creating a dictionary instead of using TaskInfo
#             task_response = {
#                 "id": task.id,
#                 "project_id": task.project_id if task.project_id else "",
#                 "project_name": task.name,
#                 "task_status": status,
#                 "task_title": task.task_title,
#                 "due_date": due_date_formatted,
#                 "past_due": past_due,
#             }

#             response.append(task_response)
#             task_id_lookups[task.id] = len(response) - 1

#         # Calculate page count
#         page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

#         return {
#             "data": response, 
#             "page_count": page_count, 
#             "item_count": item_count, 
#             "status": "success"
#         }

#     except Exception as error:
#         logger.exception(f"An unexpected error occurred while fetching tasks: {error}")
#         raise HTTPException(status_code=500, detail="Internal server error")



async def get_self_assigned_tasks(
    member_id: str,
    role_id: str,
    module_type: str,
    current_member: Members, 
    db: Session, 
    page: Optional[int] = 1, 
    page_size: Optional[int] = 5
) -> dict:
    """
    Fetch all tasks with their associated task members, attachments, and activity count.

    Args:
    - member_id (str): The ID of the member to fetch tasks for.
    - current_member (Members): The current member's information.
    - db (Session): The database session.
    - page (Optional[int]): The page number for pagination.
    - page_size (Optional[int]): The number of items per page for pagination.

    Returns:
    - dict: A dictionary containing the paginated task data and pagination details.
    """
    try:
        if module_type == "Estimation":
            is_estimation = True
        else:
            is_estimation = False
        
        query = (
            db.query(
                ProjectTask.id,
                ProjectTask.project_id,
                Projects.name,
                ProjectTask.task_status_id,
                ProjectTask.task_title,
                ProjectTask.task_description,
                ProjectTask.start_date,
                ProjectTask.due_date,
                ProjectTask.completed_date,
                ProjectTask.created_at,
                ProjectTask.created_by,
                ProjectTask.updated_at,
                ProjectTask.updated_by,
            )
            .outerjoin(Projects, Projects.id == ProjectTask.project_id)
            .outerjoin(ProjectMembers, Projects.id == ProjectMembers.project_id)
            .outerjoin(TaskMembers, ProjectTask.id == TaskMembers.task_id)
            .filter(ProjectTask.is_estimation == is_estimation)
            .group_by(ProjectTask.id, Projects.id)
            .order_by(ProjectTask.created_at.desc())
        )

        if member_id and role_id:
            member_role_id = db.query(MemberRole.id).filter(MemberRole.member_id == member_id, MemberRole.role_id == role_id).first()
            query = query.filter(ProjectMembers.member_role_id == member_role_id[0])


        # Calculate the total number of items
        item_count = query.distinct().count()

        # Apply pagination if page and page_size are provided
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        else:
            page = 1
            page_size = item_count

        task_data = query.all()

        response = []
        task_id_lookups = {}

        for task in task_data:
            due_date_formatted = task.due_date.strftime("%b %d, %Y") if task.due_date else None

            # Check if the due date has passed
            status = await get_task_status_name_by_id(db, task.task_status_id)
            past_due = False
            if status != "Completed":
                if task.due_date and task.due_date.date() < datetime.now().date():
                    past_due = True
            else:
                if task.due_date and task.completed_date and task.completed_date.date() > task.due_date.date():
                    past_due = True

            # Directly creating a dictionary instead of using TaskInfo
            task_response = {
                "id": task.id,
                "project_id": task.project_id if task.project_id else "",
                "project_name": task.name,
                "task_status": status,
                "task_title": task.task_title,
                "due_date": due_date_formatted,
                "past_due": past_due,
            }

            response.append(task_response)
            task_id_lookups[task.id] = len(response) - 1

        # Calculate page count
        page_count = math.ceil(item_count / page_size) if page_size > 0 else 0

        return {
            "data": response, 
            "page_count": page_count, 
            "item_count": item_count, 
            "status": "success"
        }

    except Exception as error:
        logger.exception(f"An unexpected error occurred while fetching tasks: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")








