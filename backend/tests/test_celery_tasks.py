"""Celery 任务主函数集成测试（mock 全部外部依赖）。"""

from unittest.mock import patch, MagicMock
from datetime import date
import asyncio


def test_sync_1688_prices_empty():
    """无已关联产品时应正常返回 0 刷新。"""
    from app.tasks.sync_1688 import sync_1688_prices

    with patch("app.tasks.sync_1688.SessionLocal") as mock_session_cls:
        db = MagicMock()
        mock_session_cls.return_value = db
        # 无已关联产品
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock
        db.query.return_value.filter_by.return_value.all.return_value = []

        stats = sync_1688_prices.run()
        assert stats["refreshed"] == 0


def test_generate_report_skips_existing():
    """已存在的日报应跳过（幂等）。"""
    from app.tasks.generate_report import generate_daily_report

    with patch("app.tasks.generate_report.SessionLocal") as mock_session_cls:
        db = MagicMock()
        mock_session_cls.return_value = db

        existing = MagicMock()
        existing.id = 99
        existing.recommendations = "已有内容"
        db.query.return_value.filter_by.return_value.first.return_value = existing

        result = generate_daily_report.run("2026-07-16")
        assert result["status"] == "skipped"


def test_generate_report_no_data_success():
    """无产品数据也能生成（走无数据 prompt 分支）。"""
    from app.tasks.generate_report import generate_daily_report

    with patch("app.tasks.generate_report.SessionLocal") as mock_session_cls, \
         patch("app.tasks.generate_report.ai_provider") as mock_ai, \
         patch("app.tasks.generate_report.build_daily_report_prompt") as mock_prompt:

        db = MagicMock()
        mock_session_cls.return_value = db
        db.query.return_value.filter_by.return_value.first.return_value = None

        mock_prompt.return_value = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "无数据"},
        ]
        mock_ai.chat.return_value = MagicMock(
            content="## 今日推荐\n暂无\n## 趋势解读\n无\n## 风险提示\n无\n## 行动建议\n观察",
            model_used="glm-4-flash", elapsed_ms=1000, success=True,
        )

        result = generate_daily_report.run("2026-07-16")
        assert result["status"] == "success"


def test_lifespan_startup():
    """main.py lifespan 能正常启动（不崩）。"""
    from app.main import create_app
    app = create_app()
    assert app.title == "ProductPulse API"
    # 路由数合理
    api_routes = [r for r in app.routes if hasattr(r, "path") and "/api/v1" in r.path]
    assert len(api_routes) >= 15


def test_celery_beat_schedule():
    """确认定时任务调度配置完整。"""
    from app.celery_app import celery_app
    assert "sync-sorftime-daily" in celery_app.conf.beat_schedule
    assert "generate-daily-report" in celery_app.conf.beat_schedule
    assert "sync-1688-prices" in celery_app.conf.beat_schedule