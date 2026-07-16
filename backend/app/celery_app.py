"""Celery 应用配置。

定时任务调度：
- 08:00 Sorftime 选品数据同步
- 08:30 1688 拿货价刷新
- 09:00 AI 日报生成
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "productpulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.sync_sorftime",
        "app.tasks.sync_1688",
        "app.tasks.generate_report",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "sync-sorftime-daily": {
        "task": "sync_sorftime_daily",
        "schedule": crontab(hour=8, minute=0),
        "options": {"timezone": "Asia/Shanghai"},
    },
    "sync-1688-prices": {
        "task": "sync_1688_prices",
        "schedule": crontab(hour=8, minute=30),
        "options": {"timezone": "Asia/Shanghai"},
    },
    "generate-daily-report": {
        "task": "generate_daily_report",
        "schedule": crontab(hour=9, minute=0),
        "options": {"timezone": "Asia/Shanghai"},
    },
}