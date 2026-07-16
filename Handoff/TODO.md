# ProductPulse 开发执行 TODO

> 基于 `Handoff/Handoff.md` 的「下一步计划」与 `项目开发文档/10.项目排期与里程碑.md` 制定。
> 规则：完成一个任务，勾选一个（`[ ]` → `[x]`），逐步消除。
> 最后更新：2026-07-15

---

## 进度总览

- [x] Phase 0：环境与版本控制准备（W1）
- [x] Phase 1：核心功能开发（W2-W3）
- [ ] Phase 2：比价模块开发（W4）
- [x] Phase 3：AI 模块开发（W5）
- [ ] Phase 4：测试与修复（W6）
- [ ] Phase 5：部署上线（W6 末）

---

## Phase 0：环境与版本控制准备（W1）

### 0.1 版本控制（先做，立即可执行）
- [x] `git init`，配置 `.gitignore`（Python / Node / IDE / .env）
- [x] 编写根目录 `README.md`（项目简介、技术栈、目录、启动指引）
- [x] 创建 `.env.example`（列出全部环境变量占位）
- [x] 首次提交：`chore: 初始化仓库与文档基线`

### 0.2 后端项目骨架
- [x] 创建 `backend/` 目录结构（按 7.1：app/core, api/v1, models, schemas, services, adapters, tasks, utils；alembic/, tests/, scripts/）
- [x] `requirements.txt`（FastAPI, SQLAlchemy, Alembic, Celery, Redis, psycopg2-binary, httpx, pydantic-settings, pytest 等）
- [x] `app/main.py` FastAPI 入口 + 健康检查 `/health`
- [x] `app/core/config.py` 配置管理（pydantic-settings 读取 .env）
- [x] 统一响应体 + `BizError` 异常处理（7.2）
- [x] 结构化 JSON 日志 + trace_id 注入（7.9）
- [x] 本地能 `uvicorn app.main:app --reload` 启动成功（Python 3.10.11 + 16 passed + health 200）

### 0.3 前端项目骨架
- [x] `npm create vite@latest frontend -- --template react-ts`（React 18 + TS）
- [x] 接入 Ant Design 5 + React Router
- [x] 按 7.1 建 `src/` 目录（api/components/pages/hooks/store/utils）
- [x] axios 封装 + 全局响应拦截器（4xx/5xx → message.error，401 跳登录）
- [x] 布局骨架（Sider + Header + Content，对应 6.UI&UX 规范）
- [x] `npm run dev` 能启动（构建已验证）并访问 `/health`

### 0.4 本地基础设施（Docker Compose）
- [x] `docker-compose.yml`：PostgreSQL 15 + Redis 7
- [x] 数据卷持久化、healthcheck
- [x] 能 `docker compose up -d`（Docker Desktop 29.6.1 + PG15/Redis7 healthy + 后端 Redis 连接正常）

### 0.5 三方 API 接入准备（用户侧 + 脚本）
> 用户侧动作（需提醒用户，外部审核有等待期）：
- [x] ~~注册 1688 开放平台并完成企业实名认证~~ → 已消除：Sorftime 内置 1688 查询(domain=601)
- [x] 获取 Sorftime API Key（API/CLI SK + MCP SK 已写入 .env）
- [ ] 获取智谱 GLM API Key

> 开发侧动作：
- [x] `backend/scripts/test_sorftime.py` 调通基础接口（含 mock fallback）
- [x] `backend/scripts/test_1688.py` 调通基础接口
- [x] `backend/scripts/test_glm.py` 调通基础接口
- [ ] **里程碑：测试脚本全部通过（Phase 0 准出）**

---

## Phase 1：核心功能开发（W2-W3）

### 1.1 数据库
- [x] 8 张表 SQLAlchemy 模型（products/price_snapshots/product_metrics_daily/daily_reports/recommendations/risk_rules/system_configs/operation_logs）
- [x] Alembic 首个迁移（pg_trgm + 索引 + 软删除 + 预置数据）
- [x] alembic upgrade head 跑通（9 表验证通过）

### 1.2 选品算法引擎
- [x] selection.py 阈值过滤（通用/耗材特殊）
- [x] 多维加权评分模型
- [x] 单元测试覆盖（14 个 selection/risk + 10 个 sorftime）

### 1.3 风险规则引擎
- [x] risk_engine.py 规则匹配
- [x] 风险标签与预警触发
- [ ] 单元测试覆盖

### 1.4 Sorftime 定时任务
- [x] tasks/sync_sorftime.py 每日 08:00 拉取
- [ ] `adapters/sorftime.py`：含重试/超时/断路器/降级/幂等
- [x] Celery Beat 调度配置

### 1.5 核心 API
- [x] dashboard.py 看板概览聚合
- [x] products.py 选品中心（列表/筛选/排序/分页/详情/推荐/同步）
- [x] config.py 阈值/规则/模型 CRUD
- [ ] `api/v1/health.py`：健康检查
- [x] 全部带 Bearer Token 鉴权

### 1.6 前端核心页面
- [x] 首页看板（4 KPI 卡 + 趋势表 + TOP1）
- [x] 选品中心（筛选 + 排序 + 分页 + 同步按钮）
- [x] 配置中心（阈值表单 + 风险规则 CRUD + Tab 切换）
- [x] 页面状态规范（加载/空/错误/重试）

### 1.7 Phase 1 联调
- [ ] 前后端联调选品→看板→配置全流程
- [ ] **里程碑：选品算法 + 看板 + 风险引擎联调通过**

---

## Phase 2：比价模块开发（W4）⚠️ 暂缓执行（用户决定保留设计、后续按需启用）

- [ ] `services/matching.py`：标题模糊匹配（pg_trgm + 人工确认 UI）
- [ ] `tasks/sync_1688.py`：1688 价格拉取定时任务
- [ ] `services/price_compare.py`：价格变动计算 + 预警触发（FR-03）
- [ ] SKU 关联管理（前后端 CRUD）
- [ ] 竞品监控页面
- [ ] **里程碑：比价监控 + 预警联调通过**
> 说明：1688 比价能力已通过 Sorftime ProductSearchFromName(domain=601) 验证可用，适配层已就绪。本阶段业务逻辑暂不实现，保留待用户后续按需启动。

## Phase 3：AI 模块开发（W5）

- [x] adapters/ai_provider.py 统一适配层（主力→备用自动降级，glm-4-flash 验证可用）
- [x] Prompt 模板 services/prompt_builder.py（数据聚合→结构化 prompt）
- [x] tasks/generate_report.py 每日 08:30 生成（四模块解析+幂等+操作日志）
- [x] AI 日报展示页面（Markdown 渲染 + 日期选择 + 重新生成 + 模型标签）
- [x] 模型可配置切换（config API + .env，glm-4-flash 主力）
- [ ] **里程碑：AI 日报自动生成 + 多模型切换**

## Phase 4：测试与修复（W6）

- [ ] 后端单元测试覆盖率 ≥80%
- [ ] 集成测试（关键 API 全覆盖，外部 API 用 Mock）
- [ ] 按 `8.测试计划与用例.md` 执行功能测试（9 组用例）
- [ ] Bug 修复
- [ ] UAT 验收
- [ ] **里程碑：0 个 P0 Bug，UAT 通过**

## Phase 5：部署上线（W6 末）

- [ ] 生产环境配置（按 `9.部署与运维方案.md`）
- [ ] Docker 镜像构建 + Docker Compose 部署
- [ ] Nginx 配置（反向代理 + IP 白名单 + HTTPS）
- [ ] 数据库初始化 + 首次数据同步
- [ ] 上线后 12 小时监控观察
- [ ] **里程碑：系统正式上线**

---

## 备注

- 代码必须遵循 `7.开发规范与质量标准.md`（PEP8+black、类型注解、Google style docstring、ESLint+Prettier）。
- 每次数据库/API 变更须同步更新 `项目开发文档/` 对应文档（文档与代码同源）。
- 已绑定的 Skills（database-design / security-best-practices / python-skills 等）自动优先使用。
- 提交规范：`<type>(<scope>): <subject>`。
---

## 追加任务：Sorftime 真实接口接入（2026-07-15）

> 用户提供 Sorftime 亚马逊数据 API 13 个接口文档后，将笼统的「Sorftime 数据源」落实为具体接口。

- [x] 整理 13 个接口规格为结构化参考文档（附录A-Sorftime接口规格.md）
- [x] 实现 `schemas/sorftime.py`（13 接口入参/出参类型）
- [x] 实现 `adapters/sorftime.py`（13 接口 + 重试/超时/缓存/容错解析/字段映射）
- [x] 编写适配层单元测试（mock，覆盖解析与字段差异）
- [x] 真实连通性验证通过（ProductRequest + 1688 ProductSearchFromName 真实数据）
- [ ] 选品算法引擎对齐 Sorftime 真实字段（Phase 1，product_search/potential_product）
- [ ] 每日拉取任务改用 product_search（Phase 1 tasks/sync_sorftime.py）