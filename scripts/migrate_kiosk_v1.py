"""Migración: modo kiosko (token por centro de trabajo + PIN por empleado)."""

from app.database import engine
from sqlalchemy import text

ALTERS = [
    text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS kiosk_pin_hash VARCHAR(255)"),
    text("ALTER TABLE work_centers ADD COLUMN IF NOT EXISTS kiosk_token VARCHAR(64)"),
    text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_work_centers_kiosk_token "
        "ON work_centers (kiosk_token)"
    ),
]


def run() -> None:
    with engine.begin() as conn:
        for stmt in ALTERS:
            conn.execute(stmt)
    print("✅ Migración kiosk_v1 completada.")


if __name__ == "__main__":
    run()
