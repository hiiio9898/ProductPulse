# ProductPulse 外贸选品决策系统

帮外贸卖家（速卖通/TikTok）在耗材品类（3D 打印耗材、墨水、相纸等）里，用数据决定「选什么品、怎么定价」，把选品成功率从行业平均 20% 提升到 60% 以上。

## 技术栈

- **后端**：Python 3.10 + FastAPI
- **前端**：React 18 + TypeScript + Ant Design 5
- **数据**：PostgreSQL 15 + Redis 7
- **定时任务**：Celery + Beat（Redis 做 Broker）
- **AI**：智谱 GLM-5.2（主力）+ GLM-5.1/deepseek（备用）
- **外部数据源**：Sorftime（选品情报）、1688 开放平台（比价）
- **部署**：Docker + Docker Compose + Nginx，单机部署（v1.0 MVP）

## 目录结构

```text
ProductPulse/
├── AGENTS.md                 # Codex 项目指令 + 已绑定 Skills
├── Handoff/                  # 交接文档 + 开发执行 TODO
│   ├── Handoff.md
│   └── TODO.md
├── 项目开发文档/              # 全套开发文档（v1.1）
├── backend/                  # FastAPI 后端（Phase 0 起创建）
└── frontend/                 # React + AntD 前端（Phase 0 起创建）
```

## 快速开始

> 详见各子目录 README 与 `项目开发文档/9.部署与运维方案.md`。

### 1. 启动依赖服务

```bash
docker compose up -d        # PostgreSQL 15 + Redis 7
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp ../.env.example .env     # 按需填写
uvicorn app.main:app --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 文档

开发文档位于 `项目开发文档/`，建议阅读顺序：立项（1）→ 需求（2）→ 设计（3-6）→ 工程规范（7-8）→ 上线（9-10）。

执行进度跟踪见 `Handoff/TODO.md`。

## 开发规范

遵循 `项目开发文档/7.开发规范与质量标准.md`：
- 提交规范：`<type>(<scope>): <subject>`（feat / fix / docs / style / refactor / test / chore）
- 分支策略：`main`（生产）→ `develop`（集成）→ `feature/<模块>-<简述>`