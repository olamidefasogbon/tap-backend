# core/celery_app.py
from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "tap_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.escrow_release", "tasks.profit_sweep"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Lagos",
    enable_utc=True,
)

# The "Beat" schedule for the nightly anti-commingling sweep
celery_app.conf.beat_schedule = {
    "nightly-profit-sweep": {
        "task": "tasks.profit_sweep.nightly_profit_sweep",
        "schedule": crontab(hour=23, minute=59), # Runs at 11:59 PM Lagos time
    },
}