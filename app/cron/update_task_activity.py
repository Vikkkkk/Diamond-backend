from models import get_db
from datetime import datetime, timedelta
from loguru import logger
from models.task_activity import TaskActivity

def update_old_task_activities():
    db = next(get_db())
    try:
        if db.in_transaction():
            # if there is an any active transaction then commit it
            db.commit()
        # Begin a transaction
        with db.begin():
            cutoff_time = datetime.now() - timedelta(days=2)
            db.query(TaskActivity).filter(
                TaskActivity.created_at < cutoff_time,
                TaskActivity.is_new == True
            ).update({TaskActivity.is_new: False}, synchronize_session=False)
        logger.info("Updated old TaskActivity records where is_new was set to False.")
    except Exception as error:
        db.rollback()
        logger.error(f"Failed to update TaskActivity records: {error}")