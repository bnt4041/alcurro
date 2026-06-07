#!/usr/bin/env bash
# backup.sh — Copia de seguridad de PostgreSQL + uploads
# Uso:  bash scripts/backup.sh
# Cron: 0 3 * * * cd /var/www/alcurro && bash scripts/backup.sh >> data/backups/backup.log 2>&1

set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_USER="${POSTGRES_USER:-hrm}"
DB_NAME="${POSTGRES_DB:-hrm}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando backup..."

# ── 1. PostgreSQL dump ────────────────────────────────────────────────────────
SQL_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"
docker exec hrm-postgres pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$SQL_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] DB dump: $SQL_FILE ($(du -sh "$SQL_FILE" | cut -f1))"

# ── 2. Uploads (tar incremental ligero) ───────────────────────────────────────
UPLOADS_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/uploads"
if [ -d "$UPLOADS_DIR" ] && [ "$(ls -A "$UPLOADS_DIR" 2>/dev/null)" ]; then
  UPLOADS_FILE="$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz"
  tar -czf "$UPLOADS_FILE" -C "$(dirname "$UPLOADS_DIR")" "$(basename "$UPLOADS_DIR")"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Uploads: $UPLOADS_FILE ($(du -sh "$UPLOADS_FILE" | cut -f1))"
fi

# ── 3. Limpiar backups antiguos ───────────────────────────────────────────────
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +$KEEP_DAYS -delete
find "$BACKUP_DIR" -name "uploads_*.tar.gz" -mtime +$KEEP_DAYS -delete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completado. Conservando últimos $KEEP_DAYS días."

# ── Resumen ───────────────────────────────────────────────────────────────────
echo ""
echo "Backups disponibles:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || true
