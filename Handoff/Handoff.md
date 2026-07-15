# ProductPulse 项目交接文档

> 写给一个完全没有上下文的新会话。读完这一份，你就能接手继续工作。
> 最后更新：2026-07-15

---

## 一、我们在做什么

**项目**：ProductPulse —— 外贸选品决策系统 v1.0

**一句话定位**：帮外贸卖家（速卖通/TikTok）在耗材品类（3D 打印耗材、墨水、相纸等）里，用数据决定「选什么品、怎么定价」，把选品成功率从行业平均 20% 提升到 60% 以上。

**技术栈**：
- 后端：Python 3.10 + FastAPI
- 前端：React 18 + Ant Design 5
- 数据：PostgreSQL 15 + Redis 7
- 定时任务：Celery + Beat（Redis 做 Broker）
- AI：智谱 GLM-5.2（主力）+ GLM-5.1/deepseek（备用）
- 外部数据源：Sorftime（选品情报）、1688 开放平台（比价）
- 部署：Docker + Docker Compose + Nginx，单机部署（v1.0 MVP）

**当前阶段的产物**：目前仓库里**只有文档，还没有任何代码**。这套文档是从用户粘贴的一份「全套开发文档」原文整理、评审、增强而来的。

---

## 二、项目当前状态

### 仓库结构（`E:\CODE\ProductPulse`）

```
ProductPulse/
├── AGENTS.md                 # Codex 项目指令 + 已绑定的 Skills 清单
├── Handoff/                  # 本交接文档所在
└── 项目开发文档/              # 全套开发文档（v1.1，已评审增强）
    ├── README.md             # 文档索引 + 修订历史
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

### 原始文档来源（仅供参考，勿再改动）

`C:\Users\pingc\.codex\attachments\5f76122e-cb09-4d26-81dd-f19f2bb5e57c\pasted-text.txt` —— 用户最初粘贴的整份文档（UTF-8 编码，含聊天式伪代码围栏 `markdown`/`text`）。整理工作已全部完成，这个文件只是留档。

---

## 三、已经完成了什么

### 第一轮：拆分 + 格式修复（v1.0）

1. 把用户粘贴的整份长文档，按目录拆成 10 份独立 Markdown。
2. 清除了原文里大量聊天式伪代码围栏（裸的 `markdown`、`text`、` ``` `，共 17 处）。
3. 补全了被误删的代码块围栏（```sql / ```json / ```bash / ```yaml）。
4. 把 Tab 分隔的纯文本还原成标准 Markdown 表格。
5. 修复丢失的标题层级（FR-03~06 的 `###`、`7.7 安全规范` 等）。
6. 选定并「部署」了 7 个项目相关的 Codex Skill，写入根目录 `AGENTS.md`。

### 第二轮：评审 + 增强（v1.1）

对 3~10 号文档做了内容评审并扩写：

| 文档 | 增强内容 |
|------|---------|
| 1.立项章程 | 新增干系人、可量化成功指标、预算、退出/搁置标准、交付物 |
| 3.系统架构 | 新增外部 API 容错（重试/超时/断路器/降级/幂等）、缓存策略表 |
| 4.数据库 | 新增 `product_metrics_daily` 历史表、软删除、`pg_trgm` 索引、Mermaid ER 图、分区归档 |
| 5.API | 详细接口 2→5 个（新增 dashboard/config/health）、风险规则 CRUD、鉴权/限流/幂等 |
| 6.UI&UX | 新增页面状态规范（5 态）、交互细节、AntD 组件规范、设计 Token |
| 7.开发规范 | 新增后端/前端目录结构、错误处理规范（含代码示例）、环境管理（Alembic） |
| 8.测试 | 新增测试环境、9 组用例（含边界/非功能）、测试周期与自动化矩阵 |
| 9.部署 | 新增 Nginx 配置、日志轮转、自动备份脚本、healthcheck |
| 10.排期 | 新增 Mermaid 阶段依赖图、各阶段准入/准出标准 |

### 已确认的业务基线（不要擅自改动业务规则）

- `1.项目立项章程.md`：项目目标、范围、可行性
- `2.需求规格说明书SRS.md`：FR-01~06 的**阈值、风险规则库、任务调度时间**都是用户已确认的值

> 这些是业务事实，文档整理/代码实现都必须遵循，只能补充工程细节。

---

## 四、当前卡在哪

**严格说没卡住**——文档工作已全部完成并通过校验。但有几个「尚未开始的待办」，是接手后的起点：

1. **代码一行都还没写**：仓库里没有 `backend/`、`frontend/`，没有 git 仓库（从未 `git init`）。
2. **外部依赖未开通**：Sorftime API Key、1688 企业实名认证、智谱 GLM API Key 都还没申请（这是用户侧动作，排期 Phase 0 的任务）。
3. **文档未经用户最终拍板**：v1.1 的增强内容（如新增的 `product_metrics_daily` 表、容错策略、准入准出标准）是 agent 评审建议，用户尚未逐条确认。

---

## 五、下一步计划

按 `项目开发文档/10.项目排期与里程碑.md` 的 6 周排期推进：

| 优先级 | 动作 |
|--------|------|
| 1（建议先做） | `git init` + 首次提交，把当前文档纳入版本控制 |
| 2（Phase 0） | 提醒用户申请三方 API Key + 完成 1688 企业认证（外部审核有等待期，越早越好） |
| 3（Phase 1） | 搭项目骨架：按 `7.开发规范` 的目录结构建 `backend/`（FastAPI）和 `frontend/`（React+AntD） |
| 4（Phase 1） | 数据库建表 + Alembic 迁移脚本（严格按 `4.数据库设计` 的 8 张表） |
| 5（Phase 1） | 选品算法引擎 + 看板首页 API + 前端框架（P0 核心） |

**关键路径提醒**：Phase 0 的「1688 企业认证」→ Phase 2 的「比价模块」是强依赖，认证审核是外部等待项，W1 必须启动。

---

## 六、踩过的坑（别再踩）

### 1. PowerShell 读 UTF-8 中文乱码（最坑）
- **现象**：用 `Get-Content` 读用户粘贴的 UTF-8 文档，中文显示成乱码（`澶栬锤閫夊搧`）。
- **原因**：PowerShell 控制台默认用 GBK 解码，但文件实际是 UTF-8。
- **正确做法**：用 `[System.IO.File]::ReadAllText(path, [System.Text.Encoding]::UTF8)` 或 `Get-Content -Encoding UTF8`；写入用 `[System.IO.File]::WriteAllText(path, content, (New-Object System.Text.UTF8Encoding $false))`（`$false` = 无 BOM）。

### 2. 原文的「伪代码围栏」
- 用户粘贴的文档里，每段代码块用聊天式的 `markdown` 开头、`text` 结尾（不是标准 ```` ```markdown ````/```` ``` ````）。整理时必须识别并清掉这些裸标记，否则渲染错乱。
- 清理后要检查代码块成对：` ``` ` 出现次数必须是偶数。

### 3. 代码块围栏被误删
- 第一轮清理时，连带把合法的 ```` ```sql ```` 开围栏也删了，只剩裸 `sql` 标签，导致 SQL/JSON 全部不渲染。**清理伪围栏时只删 `markdown`/`text`/裸 ` ``` `，不要删带语言标识的开围栏。**

### 4. 标题层级被代码块连带吃掉
- SRS 的 FR-03~06 原本在一个 ```` ```markdown ```` 块里，提取时丢了 `###` 前缀。重写文档时要逐个确认 H1/H2/H3 层级完整。

### 5. Node REPL 里 `const`/`let` 不能重复声明
- 跨多次 `js` 调用时，用 `var` 或换名字，避免 `Identifier has already been declared`。遇到报错优先复用已有绑定，不要立即 `js_reset`（会丢上下文）。

### 6. 文档 vs AGENTS.md 要同步
- 文档迁移进 `项目开发文档/` 文件夹后，AGENTS.md 里的路径引用一度没更新。**改动文档位置/结构后，必须同步更新 AGENTS.md 和 README.md。**

### 7. ASCII 架构图在非等宽字体下错位
- 架构图、ER 图用 ASCII 画的，必须用 ```` ```text ```` 包裹才能等宽对齐；关系图改用 Mermaid（GitHub/编辑器原生渲染）。

---

## 七、已绑定的 Skills（在 AGENTS.md 里）

新会话在本仓库工作时，这些 Skill 会自动优先激活，无需用户点名：

| Skill | 用途 |
|-------|------|
| `database-design` | 数据库表结构、索引、迁移 |
| `security-best-practices` | 安全评审（OWASP） |
| `code-documentation` | API 文档、README |
| `pm-execution-test-scenarios` | 测试用例派生 |
| `ui-ux-pro-max` + `web-design-guidelines` | UI 设计与可访问性 |
| `python-skills` | Python 工程规范 |
| `doc-coauthoring` | 文档协同撰写 |

---

## 八、给新会话的快速上手建议

1. 先读 `AGENTS.md`（项目指令 + Skill 清单）。
2. 再读 `项目开发文档/README.md`（文档索引 + 修订历史）。
3. 按编号快速过一遍 1~10 号文档（重点 2.SRS 的业务基线、4.数据库、5.API、10.排期）。
4. 确认用户想从哪一步开始：是继续完善文档、还是进入代码实现（Phase 0/1）。
5. 如果用户要开始写代码，**先 `git init`**，再按 `7.开发规范` 的目录结构搭骨架。