from sqlalchemy import func
from sqlalchemy.orm import Session
from models.task_activity import TaskActivity
from models.members import Members
from models.task_status import TaskStatus
from repositories.member_repositories import get_member_name_by_id
from fastapi import UploadFile
from typing import List
from fastapi.responses import JSONResponse
import os


async def get_task_status_name_by_id(db: Session, id: str):
    task_status = (
            db.query(TaskStatus.status)
            .filter(TaskStatus.id == id)
            .first()
        )
    return task_status.status

async def log_task_activity(db: Session, task_id: str, activity: str, created_by: str, details: dict = None):
    """
    Logs an activity related to a task in the task_activity table.

    :param db: SQLAlchemy session to use for the transaction.
    :param task_id: ID of the task to which this activity is related.
    :param activity: Description of the activity.
    :param created_by: ID of the user who performed the activity.
    :param details: Optional dictionary with additional details (e.g., assigned member name, file name, status change).
    """

    current_member_name = await get_member_name_by_id(db, created_by)

    if activity == "Created task":
        activity = f"<strong>{current_member_name}</strong> Created task: {details.get('task_title')}"

    elif activity == "Updated task":
        changes = details.get('changes')
        activity = ""
        for field, (old, new) in changes.items():
            field_name = field.replace('_', ' ').capitalize()
            activity += f"<strong>{field_name}</strong> from <strong>{old}</strong> to <strong>{new}</strong><br>"

    elif activity == "Deleted task":
        activity = f"<strong>{current_member_name}</strong>  Deleted task: <strong>{details.get('task_title')}</strong>"

    elif activity == "Assigned task":
        activity = f"<strong>{current_member_name}</strong> Assigned task to <strong>{details.get('assigned_to')}</strong>"

    elif activity == "Unassigned task":
        activity = f"<strong>{current_member_name}</strong> Unassigned task from <strong>{details.get('unassigned_from')}</strong>"

    elif activity == "Uploaded files":
        activity = f"<strong>{current_member_name}</strong> Uploaded <strong>{details.get('file_type', 'files')}</strong> to this task"

    elif activity == "Deleted attachment":
        activity = f"<strong>{current_member_name}</strong> Deleted attachment <strong>{details.get('file_name')}</strong>"

    elif activity == "Added attachment":
        activity = f"<strong>{current_member_name}</strong> Added attachment <strong>{details.get('file_name')}</strong>"

    elif activity == "Changed status":
        activity = f"<strong>{current_member_name}</strong> Changed status from <strong>{details.get('from_status')}</strong> to <strong>{details.get('to_status')}</strong>"

    elif activity == "Updated comment":
        activity = f"<strong>{current_member_name}</strong> Updated a comment"

    elif activity == "Deleted comment":
        activity = f"<strong>{current_member_name}</strong> Deleted a comment"

    elif activity == "Commented":
        activity = f"<strong>{current_member_name}</strong> Added a comment"

    new_activity = TaskActivity(
        task_id=task_id,
        activity=activity,
        created_by=created_by
    )
    db.add(new_activity)
    db.flush()
    return new_activity.id



ACCEPTED_FORMATS = {
    "documents": [".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt"],
    "spreadsheets": [".xls", ".xlsx", ".csv", ".ods"],
    "presentations": [".ppt", ".pptx", ".odp"],
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "videos": [".mp4", ".avi", ".mov", ".wmv", ".mkv"],
}

MAX_FILE_SIZE_MB = 25

async def validate_attachments(attachments: List[UploadFile]):
    """
    Validate the format and size of the attachments.
    """
    for attachment in attachments:
        file_extension = os.path.splitext(attachment.filename)[1].lower()

        # Validate file format
        if not any(file_extension in formats for formats in ACCEPTED_FORMATS.values()):
            return JSONResponse(
                content={"status": "error", "message": f"Unsupported file format: {attachment.filename} ({file_extension})"},
                status_code=400
            )

        # Validate file size
        file_size_mb = len(await attachment.read()) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return JSONResponse(
                content={"status": "error", "message": f"File {attachment.filename} exceeds the size limit of 25 MB"},
                status_code=400
            )

    return None

