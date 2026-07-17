# ProductPulse 外贸选品决策系统

帮外贸卖家（速卖通/TikTok）在耗材品类（3D 打印耗材、墨水、相纸等）里，用数据决定「选什么品、怎么定价」，把选品成功率从行业平均 20% 提升到 60% 以上。

## 快速导航

| 我想… | 看这里 |
|------|--------|
| 在新电脑把项目跑起来 | [SETUP.md](SETUP.md)（环境 + 密钥 + 一键启动） |
| 了解项目做到哪了 | [STAGE_SUMMARY.md](STAGE_SUMMARY.md)（阶段总结 + 踩坑 + 待办） |
| 生产部署 | [DEPLOY.md](DEPLOY.md) |
| 看完整开发文档 | `项目开发文档/`（立项→需求→设计→规范→测试→部署） |
| 看开发执行进度 | [Handoff/TODO.md](Handoff/TODO.md) |

## 技术栈

- **后端**：Python 3.10 + FastAPI + SQLAlchemy + Alembic
- **前端**：React 18 + TypeScript + Ant Design 5 + react-i18next
- **数据**：PostgreSQL 15 + Redis 7
- **定时任务**：Celery + Beat（Redis 做 Broker）
- **AI**：智谱 GLM-5.2（主力）→ GLM-4.7 → glm-4-flash（降级链）
- **外部数据源**：Sorftime（选品情报 + 1688 比价）、exchangerate-api（实时汇率）
- **部署**：Docker + Docker Compose + Nginx，单机 5 容器

## 目录结构

```text
ProductPulse/
├── README.md                 # 本文件
├── SETUP.md                  # 环境与密钥准备清单（换机必看）
├── STAGE_SUMMARY.md          # 阶段性总结（自动维护）
├── DEPLOY.md                 # 生产部署指南
├── AGENTS.md                 # Codex 项目指令 + 已绑定 Skills
├── .env.example              # 环境变量模板
├── docker-compose.yml        # 生产编排（5 容器）
├── docker-compose.dev.yml    # 开发依赖（仅 PG + Redis）
├── nginx/                    # Nginx 配置
├── Handoff/                  # 交接 + 执行 TODO + UAT 报告
├── 项目开发文档/              # 全套设计文档（v1.2）
├── backend/                  # FastAPI 后端
└── frontend/                 # React 前端
```

## 最快启动（3 步）

```powershell
# 1. 克隆 + 配置密钥
git clone https://github.com/hiiio9898/ProductPulse.git
cd ProductPulse
copy .env.example .env        # 编辑填入 GLM / Sorftime / 汇率 Key

# 2. 一键启动全套容器
docker compose up -d --build

# 3. 初始化数据库
docker compose exec app python scripts/init_db.py
```

浏览器打开 http://localhost，用 `.env` 的 `APP_SECRET_KEY` 登录。

> 完整步骤与密钥申请见 [SETUP.md](SETUP.md)。

## 核心功能

- 选品看板（多平台/站点/品类筛选 + 综合评分）
- 比价分析（1688 货源匹配 + 完整成本模型 + 实时汇率 + 比价缓存）
- 价格监控（±5% 预警 + 竞品监控）
- AI 日报（GLM 生成 + 429 重试降级）
- 中英文国际化

## 开发规范

遵循 `项目开发文档/7.开发规范与质量标准.md`：
- 提交规范：`<type>(<scope>): <subject>`（feat / fix / docs / refactor / test / chore）
- 分支策略：`main`（生产）→ `develop`（集成）→ `feature/<模块>-<简述>`

## 文档维护

- 阶段总结：对 Codex 说「阶段性总结」即自动更新 `STAGE_SUMMARY.md` 与相关文档
- 数据库/API 变更须同步更新 `项目开发文档/` 对应文档（文档与代码同源）
