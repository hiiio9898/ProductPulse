# ProductPulse Backend

FastAPI 后端。

## 目录结构

```text
app/
├── main.py              # 应用入口
├── core/                # 配置 / 数据库 / 鉴权 / 日志 / 响应
├── api/v1/              # 路由层（按模块）
├── models/              # SQLAlchemy 模型（Phase 1）
├── schemas/             # Pydantic 入参/出参（Phase 1）
├── services/            # 业务逻辑（Phase 1+）
├── adapters/            # 外部 API 适配层（Phase 0.5+）
├── tasks/               # Celery 定时任务（Phase 1+）
└── utils/
alembic/                 # 数据库迁移（Phase 1）
tests/                   # pytest 测试
scripts/                 # 工具脚本（三方 API 连通性测试等）
```

## 本地启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# 从仓库根目录复制环境变量
copy ..\.env.example .env
# 启动（需先 docker compose up -d 起 PG + Redis）
uvicorn app.main:app --reload
```

- Swagger 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

## 测试

```bash
pytest
```