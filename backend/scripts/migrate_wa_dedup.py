"""Tabla para deduplicación de mensajes WhatsApp entre múltiples workers."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        tables = inspect(conn).get_table_names()
        if "whatsapp_dedup" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE whatsapp_dedup (
                        wa_msg_id VARCHAR(200) PRIMARY KEY,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_whatsapp_dedup_created ON whatsapp_dedup (created_at)"
                )
            )
            print("Tabla whatsapp_dedup creada.")


if __name__ == "__main__":
    main()
