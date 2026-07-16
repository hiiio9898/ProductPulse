#!/usr/bin/env bash
# ProductPulse 备份脚本
# 用法（在宿主机执行）：
#   bash scripts/backup.sh           # 默认备份到 ./backups/
#   bash scripts/backup.sh /data/backup  # 指定目录
#
# 建议 crontab（每日凌晨 3 点）：
#   0 3 * * * cd /opt/productpulse && bash scripts/backup.sh >> /var/log/productpulse_backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="productpulse_postgres"
DB_USER="productpulse"
DB_NAME="productpulse"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] 开始备份 ProductPulse 数据库..."

DUMP_FILE="$BACKUP_DIR/productpulse_${TIMESTAMP}.sql.gz"
docker exec "$CONTAINER_NAME" \
    pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --clean --if-exists \
    | gzip > "$DUMP_FILE"

echo "[$(date)] 数据库备份完成: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"

REDIS_FILE="$BACKUP_DIR/redis_${TIMESTAMP}.rdb"
docker cp productpulse_redis:/data/dump.rdb "$REDIS_FILE" 2>/dev/null && \
    echo "[$(date)] Redis 快照: $REDIS_FILE" || \
    echo "[$(date)] Redis 快照跳过（无 RDB 文件）"

find "$BACKUP_DIR" -name "productpulse_*.sql.gz" -mtime +14 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +14 -delete 2>/dev/null || true

echo "[$(date)] 已清理 14 天前的旧备份"
echo "[$(date)] 备份全部完成"

# 恢复示例：
# gunzip < productpulse_YYYYMMDD.sql.gz | docker exec -i productpulse_postgres psql -U productpulse -d productpulse