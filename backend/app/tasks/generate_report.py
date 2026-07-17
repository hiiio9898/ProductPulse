"""AI 日报生成定时任务。

每日 08:30（Asia/Shanghai，在 Sorftime 同步 08:00 之后）生成当日 AI 日报。
也可通过 API 手动触发。
"""

import time
from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.adapters.ai_provider import ai_provider
from app.services.prompt_builder import build_daily_report_prompt
from app.models.daily_report import DailyReport
from app.models.operation_log import OperationLog

def _update_progress(task_id, status, model=None, message=""):
    """更新日报生成进度到 Redis。"""
    if not task_id:
        return
    try:
        from app.core.database import redis_client
        if redis_client:
            import json
            progress = {"status": status, "model": model or "", "message": message}
            redis_client.setex(f"ai:report:{task_id}", 300, json.dumps(progress))
    except Exception:
        pass


logger = get_logger("tasks.generate_report")


@celery_app.task(name="generate_daily_report", bind=True)
def generate_daily_report(self, target_date: str | None = None) -> dict:
    """生成 AI 日报。

    流程：构建 prompt → 调用 AI → 解析分模块 → 写入 daily_reports → 记录操作日志。
    """
    report_date = date.fromisoformat(target_date) if target_date else date.today()
    logger.info("AI 日报生成开始", date=str(report_date))

    db = SessionLocal()
    start = time.time()

    try:
        # 幂等：同一天已生成则跳过（除非强制）
        existing = db.query(DailyReport).filter_by(report_date=report_date).first()
        if existing:
            logger.info("日报已存在，跳过", date=str(report_date))
            return {"status": "skipped", "date": str(report_date), "id": existing.id}

        # 构建 prompt
        messages = build_daily_report_prompt(db, report_date)

        # 调用 AI（主力 → 备用自动切换）
        result = ai_provider.chat(messages, temperature=0.7, max_tokens=2000, task_id=self.request.id)

        if not result.success:
            _update_progress(self.request.id, "failed", result.model_used, result.error or "Failed")
            logger.error("AI 日报生成失败", error=result.error)
            _log_operation(db, report_date, "failed", result.error, int((time.time() - start) * 1000))
            db.commit()
            return {"status": "failed", "error": result.error, "model": result.model_used}

        # 解析 Markdown 为四模块（简单按标题分割）
        sections = _split_sections(result.content)

        # 写入数据库（已存在则更新）
        report = existing or DailyReport(report_date=report_date)
        if not existing:
            db.add(report)

        report.recommendations = sections.get("今日推荐", "")
        report.trend_analysis = sections.get("趋势解读", "")
        report.risk_alerts = sections.get("风险提示", "")
        report.action_suggestions = sections.get("行动建议", "")
        report.model_used = result.model_used
        report.generation_time_ms = result.elapsed_ms
        # raw_prompt 脱敏（只存 user 消息摘要，不含 key）
        report.raw_prompt = messages[-1]["content"][:500] if messages else None

        db.commit()
        db.refresh(report)

        _log_operation(db, report_date, "success", None, result.elapsed_ms, result.model_used)
        db.commit()

        _update_progress(self.request.id, "success", result.model_used, "Report generated")
        logger.info("AI 日报生成完成", date=str(report_date), model=result.model_used, ms=result.elapsed_ms)
        return {
            "status": "success", "date": str(report_date), "id": report.id,
            "model_used": result.model_used, "elapsed_ms": result.elapsed_ms,
        }

    except Exception as e:
        db.rollback()
        logger.error("AI 日报生成异常", error=str(e))
        raise
    finally:
        db.close()


def _split_sections(content: str) -> dict:
    """把 AI 返回的 Markdown 按 ## 标题拆分为四模块。"""
    import re
    sections = {}
    # 匹配 ## 标题
    pattern = r"^##\s+(.+?)$"
    current_key = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        m = re.match(pattern, line.strip())
        if m:
            if current_key and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1).strip()
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def _log_operation(db, report_date, status, error, duration_ms, model=None):
    """记录操作日志。"""
    db.add(OperationLog(
        trace_id=f"ai_report_{report_date}",
        operation_type="ai_generate",
        operator="system",
        details={"date": str(report_date), "model": model} if model else {"date": str(report_date)},
        status=status,
        error_message=error,
        duration_ms=duration_ms,
    ))