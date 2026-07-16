# ProductPulse 部署指南

本文档对应 `项目开发文档/9.部署与运维方案.md`，提供从零到上线的完整步骤。

## 一、环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Docker Engine | 24+ | 容器运行时 |
| Docker Compose | v2+ | 编排（`docker compose` 子命令） |
| Git | 2.30+ | 拉取代码 |
| 服务器 | 2C4G+ | 推荐 4C8G 生产 |
| 磁盘 | 40G+ | 含 PG 数据 + 日志 + 备份 |

## 二、首次部署

### 1. 克隆代码

```bash
git clone https://github.com/hiiio9898/ProductPulse.git
cd ProductPulse
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**必须修改**以下项：

```env
# 生产必须：用 openssl rand -hex 32 生成
APP_SECRET_KEY=<替换为 64 位随机串>

# 数据库密码
DB_PASSWORD=<强密码>

# Sorftime（从 https://www.sorftime.com 账户中心获取）
SORFTIME_API_SK=<API/CLI SK>
SORFTIME_MCP_SK=<MCP SK>

# 智谱 GLM
GLM_API_KEY=<从 https://open.bigmodel.cn 获取>
GLM_MODEL_PRIMARY=glm-4-flash
GLM_MODEL_FALLBACK=glm-4-flash

# 前端可访问域名（生产请改实际域名）
CORS_ORIGINS=https://your-domain.com
```

### 3. 构建前端

```bash
cd frontend
npm install
npm run build    # 产物在 frontend/dist/
cd ..
```

Nginx 容器会挂载 `frontend/dist` 作为静态资源。

### 4. 启动全部服务

```bash
docker compose up -d --build
```

首次启动会：
- 构建 `backend` 镜像（FastAPI + Celery 共用）
- 启动 PostgreSQL、Redis、app、celery、nginx 共 5 个容器
- `app` 容器启动时自动执行 `alembic upgrade head` 建表

### 5. 初始化预置数据

```bash
docker compose exec app python scripts/init_db.py
```

该脚本会写入：
- `system_configs`（AI 模型优先级、选品阈值）
- `risk_rules`（墨水易燃、相纸易损等）
- 打印管理员 token（用于调用受保护接口）

### 6. 健康检查

```bash
# 容器状态
docker compose ps

# 后端健康
curl http://localhost/api/v1/health

# 期望返回
# {"code":0,"message":"success","data":{"status":"ok"},...}
```

浏览器访问 `http://localhost` 应看到前端首页。

## 三、日常运维

### 查看日志

```bash
docker compose logs -f app        # 后端
docker compose logs -f celery     # 定时任务
docker compose logs -f nginx      # 反向代理
```

### 重启服务

```bash
docker compose restart app
docker compose restart celery
```

### 更新代码

```bash
git pull
cd frontend && npm run build && cd ..
docker compose up -d --build app celery
docker compose exec app alembic upgrade head   # 如有新迁移
```

## 四、备份与恢复

### 自动备份（推荐 crontab）

```bash
# 每日凌晨 3 点
0 3 * * * cd /opt/ProductPulse && bash scripts/backup.sh >> /var/log/pp_backup.log 2>&1
```

备份产物：
- `backups/productpulse_YYYYMMDD_HHMMSS.sql.gz`（PG 逻辑备份）
- `backups/redis_YYYYMMDD_HHMMSS.rdb`（Redis 快照）
- 自动清理 14 天前的旧备份

### 手动恢复

```bash
gunzip < backups/productpulse_YYYYMMDD.sql.gz \
  | docker exec -i productpulse_postgres psql -U productpulse -d productpulse
```

## 五、域名与 HTTPS

生产建议配置 Nginx + Let's Encrypt：

1. 修改 `nginx/nginx.conf`，在 `server` 块添加：
   ```nginx
   listen 443 ssl;
   ssl_certificate     /etc/nginx/ssl/fullchain.pem;
   ssl_certificate_key /etc/nginx/ssl/privkey.pem;
   ```
2. 在 `docker-compose.yml` 的 `nginx.volumes` 挂载证书目录
3. 用 certbot 申请证书后重启 nginx

## 六、故障排查

| 现象 | 排查 |
|------|------|
| `app` 容器启动失败 | `docker compose logs app`；多为 `.env` 缺失或 DB 未就绪 |
| 健康检查超时 | 确认 `start_period: 40s` 足够；检查 PG 健康 |
| Celery 不执行任务 | `docker compose logs celery`；确认 Redis 连通 |
| 前端空白 | 确认 `frontend/dist` 已构建并被挂载 |
| GLM 报余额不足 | 确认 `.env` 的 `GLM_MODEL_PRIMARY=glm-4-flash`（CodingPlan 可用） |

## 七、架构拓扑

```text
              ┌─────────────┐
   用户 ──►   │   Nginx:80  │
              └──────┬──────┘
         ┌──────────┴──────────┐
         ▼                     ▼
   frontend/dist          app:8000 (FastAPI)
                              │
                   ┌──────────┼──────────┐
                   ▼          ▼          ▼
              PostgreSQL   Redis    Celery worker+beat
```