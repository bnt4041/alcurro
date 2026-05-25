"""Historial de conversación WhatsApp para contexto IA."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def table_exists(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not table_exists(conn, "ai_whatsapp_messages"):
            conn.execute(
                text(
                    """
                    CREATE TABLE ai_whatsapp_messages (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        employee_id UUID NOT NULL REFERENCES employees(id),
                        role VARCHAR(20) NOT NULL,
                        content VARCHAR(4000) NOT NULL,
                        intent_code VARCHAR(50),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_ai_wa_msg_employee
                    ON ai_whatsapp_messages (tenant_id, employee_id, created_at DESC)
                    """
                )
            )
            print("Tabla ai_whatsapp_messages creada.")


if __name__ == "__main__":
    main()
