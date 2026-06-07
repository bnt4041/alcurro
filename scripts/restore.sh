#!/usr/bin/env bash
# restore.sh — Restaurar PostgreSQL desde un backup
# Uso:  bash scripts/restore.sh data/backups/db_20260607_030000.sql.gz
#
# ADVERTENCIA: sobreescribe la base de datos actual.

set -euo pipefail

BACKUP_FILE="${1:-}"
DB_USER="${POSTGRES_USER:-hrm}"
DB_NAME="${POSTGRES_DB:-hrm}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Uso: $0 <archivo.sql.gz>"
  echo ""
  echo "Backups disponibles:"
  ls -lh "$(dirname "$0")/../data/backups/"*.sql.gz 2>/dev/null || echo "  (ninguno)"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: fichero no encontrado: $BACKUP_FILE"
  exit 1
fi

echo "ADVERTENCIA: Esto sobreescribirá la base de datos '$DB_NAME'."
read -r -p "¿Continuar? [s/N] " CONFIRM
if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
  echo "Cancelado."
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restaurando desde $BACKUP_FILE..."

# Terminar conexiones activas y recrear la BD
docker exec hrm-postgres psql -U "$DB_USER" -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE IF EXISTS $DB_NAME;" \
  -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Restaurar
zcat "$BACKUP_FILE" | docker exec -i hrm-postgres psql -U "$DB_USER" -d "$DB_NAME" -q

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restauración completada."
echo "Reinicia el backend: docker restart hrm-backend"
