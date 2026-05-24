"""Columnas SMTP en system_settings y tabla mail_logs."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)

SMTP_COLUMNS = [
    ("smtp_host", "VARCHAR(255)"),
    ("smtp_port", "INTEGER NOT NULL DEFAULT 587"),
    ("smtp_user", "VARCHAR(255)"),
    ("smtp_password", "VARCHAR(255)"),
    ("smtp_use_tls", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("mail_from_address", "VARCHAR(255)"),
    ("mail_from_name", "VARCHAR(255) DEFAULT 'alcurro'"),
]


def column_exists(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for col, typedef in SMTP_COLUMNS:
            if not column_exists(conn, "system_settings", col):
                conn.execute(
                    text(f"ALTER TABLE system_settings ADD COLUMN {col} {typedef}")
                )
                print(f"Columna system_settings.{col} creada.")

        if "mail_logs" not in inspect(conn).get_table_names():
            conn.execute(
                text(
                    """
                    CREATE TABLE mail_logs (
                        id UUID PRIMARY KEY,
                        to_address VARCHAR(255) NOT NULL,
                        subject VARCHAR(500) NOT NULL,
                        event_type VARCHAR(50) NOT NULL,
                        success BOOLEAN NOT NULL DEFAULT FALSE,
                        detail VARCHAR(1000),
                        tenant_id UUID REFERENCES tenants(id),
                        envelope_id UUID,
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text("CREATE INDEX ix_mail_logs_created_at ON mail_logs (created_at)")
            )
            conn.execute(
                text("CREATE INDEX ix_mail_logs_success ON mail_logs (success)")
            )
            print("Tabla mail_logs creada.")
        else:
            print("Tabla mail_logs ya existe.")


if __name__ == "__main__":
    main()
