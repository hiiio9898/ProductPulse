"""system_configs 系统配置表模型。

对应数据库设计 4.1 表7。键值对配置（阈值/AI 模型优先级等）。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[date] = mapped_column(server_default=func.now(), onupdate=func.now())