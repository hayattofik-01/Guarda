from celery import Celery

from app.config import settings

celery_app = Celery(
    "guarda",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=settings.scan_timeout_seconds + 60,
    timezone="UTC",
    beat_schedule={
        "enqueue-due-scans": {
            "task": "app.worker.tasks.enqueue_due_scans",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)

# Ensure tasks are registered when the worker boots.
celery_app.autodiscover_tasks(["app.worker"])

import app.worker.tasks  # noqa: E402,F401
