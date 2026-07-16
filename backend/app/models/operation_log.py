"""operation_logs 操作日志表模型。

对应数据库设计 4.1 表8。记录数据同步/价格检查/AI 生成等操作日志（details 不得记录明文 Key）。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    operation_type: Mapped[Optional[str]] = mapped_column(String(50))
    operator: Mapped[str] = mapped_column(String(50), default="system")
    details: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[date] = mapped_column(server_default=func.now(), index=True)