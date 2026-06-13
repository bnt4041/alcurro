"""Añade campos de omisión de fichaje a incident_auto_rules y last_incident_reminder_at a employees."""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE incident_auto_rules
            ADD COLUMN IF NOT EXISTS missing_clock_in_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS missing_clock_in_hours NUMERIC(5,2) NOT NULL DEFAULT 2.0,
            ADD COLUMN IF NOT EXISTS missing_clock_in_notify_whatsapp BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS missing_clock_in_require_justification BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS missing_clock_out_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS missing_clock_out_hours NUMERIC(5,2) NOT NULL DEFAULT 12.0,
            ADD COLUMN IF NOT EXISTS missing_clock_out_notify_whatsapp BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS missing_clock_out_require_justification BOOLEAN NOT NULL DEFAULT TRUE
        """))
        print("Columnas de omisión añadidas a incident_auto_rules.")

        conn.execute(text("""
            ALTER TABLE employees
            ADD COLUMN IF NOT EXISTS last_incident_reminder_at TIMESTAMP
        """))
        print("Columna last_incident_reminder_at añadida a employees.")


if __name__ == "__main__":
    main()
