from apscheduler.schedulers.background import BackgroundScheduler
from .update_task_activity import update_old_task_activities
from .update_due_date import update_due_date

scheduler = BackgroundScheduler()

scheduler.add_job(update_old_task_activities, 'cron', hour=0, minute=0)
scheduler.add_job(update_due_date, 'cron', hour=0, minute=0)
