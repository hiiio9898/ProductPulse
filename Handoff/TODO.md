# ProductPulse 开发执行 TODO

> 基于 Handoff/Handoff.md 的下一步计划与项目开发文档/10.项目排期与里程碑.md 制定。
> 规则：完成一个任务，勾选一个（[ ] -> [x]），逐步消除。
> 最后更新：2026-07-17（文档体系完善 + skill 创建）

---

## 进度总览

- [x] Phase 0：环境与版本控制准备（W1）
- [x] Phase 1：核心功能开发（W2-W3）
- [x] Phase 2：比价模块开发（W4）
- [x] Phase 3：AI 模块开发（W5）
- [x] Phase 4：测试与修复（W6）
- [x] Phase 5：部署上线（W6 末）

---

## Phase 0 - 全部完成

- [x] git init + .gitignore + README + .env.example
- [x] 后端骨架（FastAPI + 配置 + 响应体 + 日志 + 16 tests passed）
- [x] 前端骨架（React 18 + TS + AntD 5 + Router + axios）
- [x] Docker Compose（PG15 + Redis7 healthy）
- [x] Sorftime 真实接入（API/CLI SK + MCP SK + 1688 domain=601）
- [x] GLM API Key 已配置（glm-5.2 首选，4.7/4-flash 降级）

## Phase 1 - 全部完成

- [x] 8 张表 + Alembic 迁移
- [x] 选品算法引擎（阈值过滤 + 加权评分）
- [x] 风险规则引擎
- [x] Sorftime 定时任务（含多 key 轮换）
- [x] 核心 API + Bearer Token 鉴权
- [x] 前端核心页面 + 联调通过

## Phase 2 - 已完成

- [x] price_compare 标题匹配 + 利润计算 + 预警
- [x] sync_1688 每日刷新 + auto-match Top20
- [x] 价格预警 ±5% + 竞品监控页

## Phase 3 - 已完成

- [x] AI provider（GLM 5.2 -> 4.7 -> 4-flash 降级）
- [x] Prompt 模板 + 日报生成任务
- [x] 日报展示页（Markdown + 重新生成）
- [x] 429 限流重试 + Redis 进度反馈

## Phase 4 - 已完成

- [x] 单元测试 80%（100 个）+ 集成测试
- [x] Bug 修复 + UAT 18/18 PASS

## Phase 5 - 已完成

- [x] 生产 docker-compose（5 容器全编排）
- [x] Nginx 反向代理 + init_db.py + backup.sh
- [x] DEPLOY.md 部署指南
- [x] 首次数据同步（Amazon 339 + TikTok 39）
- [x] 系统上线（5 容器 healthy）

---

## 追加功能（2026-07-16~17）- 已完成

- [x] 前端登录页（token 校验 + localStorage）
- [x] 中英文国际化（react-i18next + 语言切换）
- [x] 多平台支持（Amazon + TikTok Shop，8 国站点）
- [x] Sorftime 多 key 自动轮换（3+3 key）
- [x] GLM 429 重试 + 实时进度反馈
- [x] 完整外贸成本比价（物流+关税+佣金+包装+退货）+ 实时汇率 + 标题翻译
- [x] 比价结果缓存（默认返回上次结果省 API，刷新按钮才重新拉取）
- [x] 文档体系完善（SETUP.md 环境密钥清单 + STAGE_SUMMARY.md 阶段总结 + README 快速导航）
- [x] project-summary skill 创建（说「阶段性总结」自动触发文档同步）

---

## 待优化项（非阻塞，按需推进）

- [ ] 配置中心加品类管理（增删自定义品类）
- [ ] 选品页同步拉取进度反馈
- [ ] HTTPS 证书配置（生产域名 + Let's Encrypt）
- [ ] 监控页 TikTok 产品利润分析
- [ ] 日报 prompt 优化（TikTok 数据为空时内容较简略）
