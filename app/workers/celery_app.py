"""Celery application — entrypoint for both worker and beat.

Run worker:  celery -A app.workers.celery_app worker --loglevel=info
Run beat:    celery -A app.workers.celery_app beat   --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "smart_pg",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "daily-meal-poll": {
        "task": "app.workers.tasks.send_daily_meal_polls",
        # 16:00 IST every day
        "schedule": crontab(hour=16, minute=0),
    },
    "monthly-rent-reminders": {
        "task": "app.workers.tasks.send_monthly_rent_reminders",
        # 09:00 IST on the 1st of every month, billing the previous month
        "schedule": crontab(hour=9, minute=0, day_of_month=1),
    },
}
