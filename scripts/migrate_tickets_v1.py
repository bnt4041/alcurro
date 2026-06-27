"""Migración: campos de soporte en system_settings (tablas de tickets/comercial las crea create_all)."""

from app.database import engine
from sqlalchemy import text

ALTERS = [
    text(
        "ALTER TABLE system_settings "
        "ADD COLUMN IF NOT EXISTS whatsapp_public_number VARCHAR(40)"
    ),
    text(
        "ALTER TABLE system_settings "
        "ADD COLUMN IF NOT EXISTS platform_alert_phone VARCHAR(40)"
    ),
    text(
        "ALTER TABLE system_settings "
        "ADD COLUMN IF NOT EXISTS commercial_ai_enabled BOOLEAN NOT NULL DEFAULT TRUE"
    ),
]


def run() -> None:
    with engine.begin() as conn:
        for stmt in ALTERS:
            conn.execute(stmt)
    print("✅ Migración tickets_v1 (system_settings) completada.")


if __name__ == "__main__":
    run()
