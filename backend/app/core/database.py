"""数据库会话管理。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.app_debug and not settings.is_prod,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Redis 客户端（进度反馈、缓存等）----------
try:
    import redis as _redis
    redis_client = _redis.from_url(settings.redis_url, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None
