# ProductPulse 阶段性总结

> 本文档在每个阶段结束时整理更新，记录「做了什么、当前状态、已知问题、下一步」。
> 触发方式：对 Codex 说「阶段性总结」即自动整理更新本文档。
> 最后更新：2026-07-17（比价缓存 + 文档体系完善）

---

## 一、项目定位

**ProductPulse = 外贸耗材选品决策系统**。帮速卖通/TikTok 卖家在 3D 打印耗材、墨水、相纸等品类里，用数据决定「选什么品、怎么定价、货源比价」，把选品成功率从行业 20% 提升到 60%+。

---

## 二、技术架构

```text
前端 React18+TS+AntD5  ──┐
                         ├──► Nginx :80/:443 ──► FastAPI :8000 ──► PostgreSQL 15
定时 Celery + Beat ───────┤                     │
                         │                     ├──► Sorftime API（选品情报 + 1688 比价）
                         │                     ├──► 智谱 GLM（AI 日报 + 标题翻译）
                         └──► Redis 7（Broker + 缓存 + 汇率缓存）
```

- 单机 Docker 部署，5 容器全编排
- 全程 UTF-8，支持中英文国际化

---

## 三、已完成里程碑

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 环境准备 + 前后端骨架 + Docker + Sorftime/GLM 接入 | ✅ |
| Phase 1 | 8 张表 + 选品算法 + 风险规则 + 定时任务 + 核心 API + 前端联调 | ✅ |
| Phase 2 | 1688 比价 + 标题匹配 + 利润计算 + 价格预警 + 竞品监控 | ✅ |
| Phase 3 | AI 日报（GLM 5.2→4.7→4-flash 降级）+ Prompt + 重新生成 | ✅ |
| Phase 4 | 单元测试 100 个 + 集成测试 + UAT 18/18 PASS | ✅ |
| Phase 5 | 生产部署（5 容器 healthy）+ Nginx + 备份脚本 + DEPLOY.md | ✅ |
| 追加功能 | 登录页 / 中英文 i18n / 多平台(Amazon+TikTok) / 多 Key 轮换 / 429 重试 | ✅ |
| 比价增强 | 完整成本模型（物流+关税+佣金+包装+退货）/ 实时汇率 / 标题翻译 / 比价缓存 | ✅ |

---

## 四、当前运行状态（2026-07-17 快照）

| 容器 | 状态 |
|------|------|
| productpulse_app | Up (healthy) |
| productpulse_celery | Up |
| productpulse_nginx | Up |
| productpulse_postgres | Up (healthy) |
| productpulse_redis | Up (healthy) |

数据量：Amazon 339 + TikTok 39 条产品，部分已有价格快照。

---

## 五、核心功能清单

1. **选品看板**：多平台/站点/品类筛选，综合评分排序，风险标签
2. **数据同步**：TikTok（默认）/ Amazon，8 国站点，Sorftime 多 Key 轮换
3. **比价分析**：TikTok 美元售价 → 汇率换算 → 1688 货源匹配（GLM 翻译标题）→ 完整成本模型 → 利润/毛利率
4. **比价缓存**：默认返回上次结果（省 API 额度），点「刷新比价」才重新实时拉取
5. **价格监控**：±5% 变动预警 + 竞品监控页
6. **AI 日报**：GLM 生成 Markdown 日报，429 自动重试 + 进度反馈
7. **配置中心**：Sorftime/GLM 配置 + 风险规则
8. **国际化**：中英文实时切换

---

## 六、成本模型（比价用）

```text
总成本(¥) = 拿货价 + 国际物流(¥25) + 关税(5%) + 平台佣金(8%) + 包装(¥3) + 退货损耗(3%)
毛利(¥)   = 售价(¥) - 总成本(¥)
毛利率     = 毛利 / 售价
汇率来源   = exchangerate-api.com，Redis 缓存 6 小时（当前 ≈ 6.78）
```

TikTok 价格单位是美元（Amazon 是美分，已做 `/100` 处理）。

---

## 七、踩坑记录（换机时重点注意）

1. **PowerShell 编码**：写文件用 `[System.IO.File]::WriteAllText` + UTF8Encoding(false)，绝不用 `Set-Content`（加 BOM）；多行 Python 写到 `.py` 再执行，不要用 `-c`。
2. **Alembic 迁移版本错位**：若 app 容器报 `Can't locate revision`，用 `alembic stamp <上一版>` 后 `alembic upgrade head` 修复（见提交 538713b）。
3. **npm 在 PowerShell 被拦**：用 `cmd /c "npm run build 2>&1"`。
4. **Docker 代码改动后**：`docker compose up -d --build app celery` 后必须 `docker compose restart nginx`（上游 IP 缓存）。
5. **Sorftime 额度**：单 Key 日额度有限，务必配多 Key 逗号分隔，系统自动轮换。
6. **GLM 并发**：CodingPlan 的 glm-5.2 高并发会 429，已实现重试 + 降级链。

---

## 八、待优化项（非阻塞）

- [ ] 配置中心支持自定义品类增删
- [ ] 选品页同步拉取实时进度条
- [ ] HTTPS 证书（生产域名 + Let's Encrypt）
- [ ] 监控页 TikTok 利润分析补全
- [ ] 日报 prompt 在 TikTok 数据稀疏时优化内容
- [ ] 前端 chunk 拆分（当前打包 1.4MB）

---

## 九、换机启动顺序（TL;DR）

1. 装 Git + Docker Desktop + Python 3.10 + Node 18
2. `git clone` → `copy .env.example .env` → 填密钥（GLM / Sorftime API+MCP / 汇率）
3. `docker compose up -d --build`
4. `docker compose exec app python scripts/init_db.py`
5. 浏览器开 http://localhost，用 `.env` 的 `APP_SECRET_KEY` 登录

详见 `SETUP.md`。
