"""Celery 应用配置。

Beat 调度配置在 Phase 1 接入具体任务后补充。
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "productpulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)

# Phase 1 在此注册任务模块
celery_app.autodiscover_tasks(["app.tasks"])
celery_app.conf.beat_schedule = {
    "sync-sorftime-daily": {
        "task": "sync_sorftime_daily",
        "schedule": crontab(hour=8, minute=0),
        "options": {"timezone": "Asia/Shanghai"},
    },
}