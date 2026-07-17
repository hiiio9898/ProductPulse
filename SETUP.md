# ProductPulse 环境与密钥准备清单

> 目标：换一台电脑，照此文档从上到下走一遍，即可把项目完整跑起来。
> 最后更新：2026-07-17

---

## 一、必装软件

| 软件 | 版本 | 用途 | 安装方式 |
|------|------|------|----------|
| Git | 2.30+ | 拉取代码、提交 | https://git-scm.com |
| Docker Desktop | 最新 | 运行 PG/Redis/后端/Nginx 全套容器 | https://docker.com（含 Compose v2） |
| Python | 3.10.x | 本地后端开发 / 脚本 | https://python.org（勾选 Add to PATH） |
| Node.js | 18+ | 前端构建 | https://nodejs.org（含 npm） |

验证安装：

```powershell
git --version
docker --version
docker compose version
python --version      # 应显示 3.10.x
node --version        # 应显示 v18+
```

> Docker Desktop 安装后需启动并等待右下角图标变绿（Linux 容器模式）。

---

## 二、拉取代码

```powershell
git clone https://github.com/hiiio9898/ProductPulse.git
cd ProductPulse
```

---

## 三、外部账号与密钥（必须先准备）

本项目用到 3 类外部服务，需自行注册并拿到 Key。

### 3.1 智谱 GLM（AI 日报 / 标题翻译）

- 注册：https://open.bigmodel.cn
- 路径：控制台 → API Keys → 创建
- 推荐：订阅 CodingPlan（支持 glm-5.2，额度高）
- 需要的值：**1 个 API Key**（形如 `xxxxxxxx.xxxxxxxx`）

### 3.2 Sorftime（选品情报 + 1688 比价数据源）

- 注册：https://www.sorftime.com
- 路径：个人中心 → API → 创建
- 两类 Key 都要：
  - **API SK（Standard API）**：后端拉产品/类目/销量用
  - **MCP SK**：AI 日报时让 GLM 直连 Sorftime MCP 用
- 多 Key 轮换：系统支持逗号分隔多 Key，额度用完自动切换下一个；建议各准备 2-3 个

> 1688 比价无需单独注册 1688 开放平台，复用 Sorftime 的 `ProductSearchFromName`（domain=601）即可。

### 3.3 汇率 API（实时汇率换算）

- 注册：https://app.exchangerate-api.com（免费版足够）
- 路径：注册后在 Dashboard 看到 API Key
- 需要的值：**1 个 ExchangeRate API Key**
- 说明：后端用它在比价时做美元↔人民币换算，Redis 缓存 6 小时

---

## 四、配置 .env

```powershell
copy .env.example .env
```

编辑 `.env`，填入以下字段（**粗体为必须修改**）：

```env
# 应用密钥：本地开发可留默认，生产必须改（openssl rand -hex 32）
APP_SECRET_KEY=change_me_to_a_random_string

# 数据库密码（本地开发可用 change_me，生产必须改）
DB_PASSWORD=change_me

# Sorftime —— 多 Key 用逗号分隔
SORFTIME_API_SK=你的API_SK_1,你的API_SK_2,你的API_SK_3
SORFTIME_MCP_SK=你的MCP_SK_1,你的MCP_SK_2,你的MCP_SK_3

# 智谱 GLM
GLM_API_KEY=你的GLM_API_KEY
GLM_MODEL_PRIMARY=glm-5.2
GLM_MODEL_FALLBACK=glm-4.7

# 汇率 API
EXCHANGE_RATE_API_KEY=你的汇率API_KEY

# CORS（前端地址，本地开发默认即可）
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost
```

> `.env` 已在 `.gitignore` 中，不会提交。**切勿把真实密钥提交到 Git。**

---

## 五、一键启动（Docker 生产编排，推荐）

```powershell
docker compose up -d --build
```

这会启动 5 个容器：

| 容器 | 端口 | 说明 |
|------|------|------|
| productpulse_app | 8000 | FastAPI 后端（含 Alembic 自动迁移） |
| productpulse_celery | - | 定时任务（同步、日报） |
| productpulse_nginx | 80 / 443 | 反向代理，托管前端 dist |
| productpulse_postgres | 5432 | PostgreSQL 15 |
| productpulse_redis | 6379 | Redis 7（Celery broker + 缓存） |

启动后初始化数据库与种子数据：

```powershell
docker compose exec app python scripts/init_db.py
```

验证：

```powershell
curl http://localhost/api/v1/health
# 应返回 {"code":0,"message":"success",...}
```

浏览器打开 http://localhost（前端），登录 Token 见 `.env` 的 `APP_SECRET_KEY`。

---

## 六、本地开发模式（可选，前后端分离热更新）

### 6.1 只起依赖容器

```powershell
docker compose -f docker-compose.dev.yml up -d   # 只起 PG + Redis
```

### 6.2 后端热更新

```powershell
cd backend
py -3.10 -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://127.0.0.1:8000
```

> Windows 注意：`requirements.txt` 若因编码报错，先 `python -m pip install --upgrade pip` 再装。

### 6.3 前端热更新

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### 6.4 运行测试

```powershell
cd backend
.venv\Scriptsctivate
pytest -q          # 应 100 passed
```

---

## 七、常见问题

| 问题 | 解决 |
|------|------|
| `docker compose up` 报 `no configuration file` | 确认在项目根目录执行，不在子目录 |
| app 容器反复重启（exit 255） | 多为 Alembic 迁移版本错位，见 STAGE_SUMMARY.md「踩坑记录」 |
| 前端打开空白 | 确认后端 8000 端口正常；浏览器 F12 看网络请求 |
| Sorftime 报额度用完 | `.env` 配多个 Key，系统自动轮换 |
| GLM 报 429 | 系统已自动重试并降级到 4.7 → 4-flash，无需手动处理 |
| PowerShell 中文乱码 | 文件本身是 UTF-8，仅终端显示问题，不影响功能 |

---

## 八、登录令牌

本项目 MVP 阶段使用固定 Bearer Token 鉴权（无用户体系）。

- Token 值 = `.env` 中的 `APP_SECRET_KEY`
- 前端登录页输入该值即可
- 生产部署务必改为随机字符串：`openssl rand -hex 32`
