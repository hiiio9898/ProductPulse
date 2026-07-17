# ProductPulse - 外贸选品决策系统

本仓库为「外贸选品决策系统 v1.0」的全套开发文档与后续实现代码。
技术栈：Python 3.10 + FastAPI（后端）、React 18 + Ant Design 5（前端）、PostgreSQL 15、Redis 7、Celery、Docker + Nginx。

## 仓库结构

```
ProductPulse/
├── AGENTS.md                 # 本文件
└── 项目开发文档/              # 全套开发文档（v1.1，已评审增强）
    ├── README.md             # 文档索引与修订历史
    ├── 1.项目立项章程.md
    ├── 2.需求规格说明书SRS.md
    ├── 3.系统架构设计.md
    ├── 4.数据库设计文档ER图.md
    ├── 5.API接口设计文档.md
    ├── 6.UI&UX设计规范.md
    ├── 7.开发规范与质量标准.md
    ├── 8.测试计划与用例.md
    ├── 9.部署与运维方案.md
    └── 10.项目排期与里程碑.md
```

后续实现代码（`backend/`、`frontend/`）将在排期 Phase 1 起按 `7.开发规范与质量标准.md` 的目录结构创建。

## 已为本项目启用的 Skills

以下 Skills 已评估并选定为本项目「适用」（project-relevant）。在本仓库内工作时，应主动、优先使用这些 Skill 来完成对应类别的任务，无需用户再次点名：

| 用途 | Skill | 触发场景 |
|------|-------|---------|
| 数据库设计与评审 | `database-design` | 设计/评审 products、price_snapshots、product_metrics_daily 等表结构、索引、迁移脚本、分区归档 |
| 安全最佳实践评审 | `security-best-practices` | 评审 FastAPI 后端、React 前端的安全（API Key 管理、SQL 注入、令牌哈希、OWASP Top 10） |
| API 文档撰写 | `code-documentation` | 撰写/校正 API 接口文档（鉴权/幂等/错误示例）、README、开发者指南 |
| 测试用例设计 | `pm-execution-test-scenarios` | 由 FR 需求派生测试场景与用例（含边界/非功能，补充 8.测试计划） |
| 前端验收测试 | webapp-testing + playwright | 用 Playwright 驱动 React/AntD 看板与配置中心，完成 SRS 验收点（FR-01~06）的端到端与交互验证 |
| UI/UX 设计与评审 | `ui-ux-pro-max` + `web-design-guidelines` | 看板/配置中心页面设计、页面状态规范、设计 Token、可访问性评审 |
| 落地页/营销页设计 | design-taste-frontend | **仅限**项目落地页、介绍页、营销类页面设计；该 skill 自述「不适用于 dashboard/数据表/多步产品 UI」，故看板与配置中心页面仍用上一行 skill |
| Python 工程规范 | `python-skills` | 后端代码模式、异步、类型注解、错误处理、测试 |
| 文档协同 | `doc-coauthoring` | 多份设计文档的协同撰写与重构 |
| 阶段性总结与文档同步 | `project-summary` | 用户说「阶段性总结/整理文档/总结进度」时触发，自动更新 STAGE_SUMMARY.md / SETUP.md / README.md / Handoff/TODO.md，保证换机可复现、文档与代码同源 |

> 说明：以上 Skills 在当前 Codex 环境中已全局可用（位于 `~/.codex/skills` 与 `~/.agents/skills`）。本 AGENTS.md 的作用是将它们「绑定」到本项目作用域，使在本仓库工作时自动优先激活。

## 文档约定

- 文档统一使用 UTF-8 编码（无 BOM）、Markdown 格式，中文标点。
- 每份文档保留唯一一级标题（H1），章节使用 `## N.x`，子章节 `###`。
- 代码块必须带语言标识并完整闭合（```sql / ```json / ```bash / ```yaml / ```python / ```nginx / ```env / ```text）。
- 关系图、依赖图使用 Mermaid（```mermaid），ASCII 架构图用 ```text 包裹。
- 数据库变更、API 路由变更须同步更新 `项目开发文档/` 下对应文档（文档与代码同源）。

## 已确认基线

以下为已确认的业务基线，工作时不擅自改动其业务规则（可补充工程细节）：
- `项目开发文档/1.项目立项章程.md`
- `项目开发文档/2.需求规格说明书SRS.md`（FR-01~06 的阈值、风险规则、任务调度时间为已确认值）

## 文档版本

- v1.0（2026-07-15）：初版拆分整理 + 首轮评审修订（格式修复 + 内容补全）。
- v1.1（2026-07-15）：第二轮增强，详见 `项目开发文档/README.md` 修订历史。
- v1.3（2026-07-17）：新增 project-summary skill（阶段性总结触发器），绑定到本仓库作用域。
- v1.2（2026-07-16）：Skills 表新增 design-taste-frontend（落地页/营销页设计），并注明其不适用于看板/数据表类 UI 的边界。同日补充 webapp-testing + playwright（前端验收测试）。