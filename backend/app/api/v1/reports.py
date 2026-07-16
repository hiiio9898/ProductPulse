"""AI 日报 API。

GET  /api/v1/reports/daily        - 获取今日 AI 日报
GET  /api/v1/reports/daily/{date} - 获取指定日期日报
POST /api/v1/reports/generate     - 手动触发 AI 日报生成
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.response import BizError, ErrorCode, ok_response
from app.core.security import AuthRequired
from app.models.daily_report import DailyReport

router = APIRouter(tags=["reports"])


def _report_to_dict(report: DailyReport) -> dict:
    return {
        "id": report.id,
        "report_date": str(report.report_date),
        "recommendations": report.recommendations,
        "trend_analysis": report.trend_analysis,
        "risk_alerts": report.risk_alerts,
        "action_suggestions": report.action_suggestions,
        "model_used": report.model_used,
        "generation_time_ms": report.generation_time_ms,
        "created_at": str(report.created_at) if report.created_at else None,
    }


@router.get("/reports/daily")
async def get_today_report(db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取今日 AI 日报。"""
    today = date.today()
    report = db.execute(
        select(DailyReport).where(DailyReport.report_date == today)
    ).scalar_one_or_none()

    if not report:
        return ok_response(data=None, message="今日日报尚未生成")
    return ok_response(data=_report_to_dict(report))


@router.get("/reports/daily/{report_date}")
async def get_report_by_date(report_date: str, db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取指定日期日报（格式 yyyy-MM-dd）。"""
    try:
        target = date.fromisoformat(report_date)
    except ValueError:
        raise BizError(ErrorCode.PARAM_INVALID, "日期格式错误，应为 yyyy-MM-dd")

    report = db.execute(
        select(DailyReport).where(DailyReport.report_date == target)
    ).scalar_one_or_none()

    if not report:
        raise BizError(ErrorCode.NOT_FOUND, f"{report_date} 无日报记录")
    return ok_response(data=_report_to_dict(report))


@router.post("/reports/generate")
async def trigger_generate(
    report_date: str | None = None,
    force: bool = False,
    _: bool = AuthRequired,
):
    """手动触发 AI 日报生成（异步任务）。

    force=true 时删除当天旧报告重新生成（用于切换模型后重新生成）。
    """
    from app.tasks.generate_report import generate_daily_report
    if force:
        from sqlalchemy import delete
        target = date.fromisoformat(report_date) if report_date else date.today()
        db = SessionLocal()
        db.execute(delete(DailyReport).where(DailyReport.report_date == target))
        db.commit()
        db.close()
    task = generate_daily_report.delay(report_date)
    return ok_response(data={"task_id": task.id, "status": "queued", "force": force})