from models import get_db
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.project_task import ProjectTask
from models.projects import Projects
from utils.common import check_task_completion_status


def update_due_date():
    try:
        db = next(get_db())
        if db.in_transaction():
            # If there is any active transaction, commit it
            db.commit()
        
        # Begin a transaction
        with db.begin():
            # Filter tasks where the associated project's current_project_status is "In Progress"
            task_data = (
                db.query(ProjectTask)
                .join(Projects, ProjectTask.project_id == Projects.id)
                .filter(Projects.current_project_status == "In Progress")
                .all()
            )

            for task in task_data:
                # Check task status and determine if past due or near due
                task_status_info = check_task_completion_status(
                    start_date=task.start_date,
                    due_date=task.due_date,
                    completed_date=task.completed_date if task.completed_date else None
                )

                task.is_past_due = task_status_info['pastdue']
                task.is_near_due_date = task_status_info['is_near_due_date']

            # Commit the changes after all updates are done
            db.commit()

        logger.info("Updated Task records for past due and near due date status.")
    except Exception as error:
        db.rollback()
        logger.error(f"Failed to update Task records: {error}")
    
    finally:
        db.close()
