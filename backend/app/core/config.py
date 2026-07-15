"""应用配置管理。

通过 pydantic-settings 从环境变量 / .env 文件读取配置。
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，字段与 .env.example 一一对应。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 应用 ----------
    app_env: str = "dev"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "change_me_to_a_random_string"

    # ---------- 数据库 ----------
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "productpulse"
    db_user: str = "productpulse"
    db_password: str = "change_me"
    database_url: str | None = None

    @field_validator("database_url", mode="after")
    @classmethod
    def _build_database_url(cls, v, info):
        if v:
            return v
        data = info.data
        return (
            f"postgresql://{data.get('db_user')}:"
            f"{data.get('db_password')}@{data.get('db_host')}:"
            f"{data.get('db_port')}/{data.get('db_name')}"
        )

    # ---------- Redis / Celery ----------
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/1"
    celery_result_backend: str = "redis://127.0.0.1:6379/2"

    # ---------- CORS ----------
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ---------- 外部数据源：Sorftime ----------
    # Standard API / CLI 共用 Account-SK
    sorftime_api_sk: str = ""
    sorftime_api_base_url: str = "https://standardapi.sorftime.com/api"
    # MCP 专用 Account-SK（AI 日报）
    sorftime_mcp_sk: str = ""
    sorftime_mcp_url: str = "https://mcp.sorftime.com"
    # 兼容旧字段
    sorftime_api_key: str = ""

    # ---------- 1688 比价 ----------
    # 通过 Sorftime ProductSearchFromName (domain=601) 实现，复用 sorftime_api_sk
    ali1688_app_key: str = ""
    ali1688_app_secret: str = ""

    # ---------- AI ----------
    glm_api_key: str = ""
    glm_model_primary: str = "glm-5.2"
    glm_model_fallback: str = "glm-5.1"

    # ---------- 日志 ----------
    log_level: str = "INFO"

    @property
    def is_prod(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """单例配置，避免重复读取 .env。"""
    return Settings()


settings = get_settings()