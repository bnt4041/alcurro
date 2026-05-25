"""Configuración de fichajes, documentos inbound y columnas de bienvenida."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def table_exists(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def column_exists(conn, table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(conn).get_columns(table)]
    return column in cols


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not table_exists(conn, "clock_settings"):
            conn.execute(
                text(
                    """
                    CREATE TABLE clock_settings (
                        tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
                        require_geolocation BOOLEAN NOT NULL DEFAULT FALSE,
                        clock_reminder_minutes INTEGER,
                        incident_reminder_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        incident_reminder_minutes INTEGER,
                        inbound_documents_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        inbound_document_codes JSONB NOT NULL
                            DEFAULT '["dni","photo","driving_license","legal_terms"]',
                        send_welcome_with_documents BOOLEAN NOT NULL DEFAULT TRUE,
                        welcome_message_extra VARCHAR(1000),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla clock_settings creada.")

        if not table_exists(conn, "employee_inbound_documents"):
            conn.execute(
                text(
                    """
                    CREATE TABLE employee_inbound_documents (
                        id UUID PRIMARY KEY,
                        employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                        document_code VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        document_delivery_id UUID REFERENCES document_deliveries(id),
                        received_at TIMESTAMP,
                        notes VARCHAR(500),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX ix_employee_inbound_employee
                    ON employee_inbound_documents (employee_id)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX uq_employee_inbound_code
                    ON employee_inbound_documents (employee_id, document_code)
                    """
                )
            )
            print("Tabla employee_inbound_documents creada.")

        if not column_exists(conn, "employees", "welcome_sent_at"):
            conn.execute(
                text("ALTER TABLE employees ADD COLUMN welcome_sent_at TIMESTAMP")
            )
            print("Columna employees.welcome_sent_at creada.")

        if not column_exists(conn, "employees", "last_clock_reminder_at"):
            conn.execute(
                text(
                    "ALTER TABLE employees ADD COLUMN last_clock_reminder_at TIMESTAMP"
                )
            )
            print("Columna employees.last_clock_reminder_at creada.")

        conn.execute(
            text(
                """
                INSERT INTO clock_settings (
                    tenant_id, require_geolocation, incident_reminder_enabled,
                    inbound_documents_enabled, inbound_document_codes,
                    send_welcome_with_documents, updated_at
                )
                SELECT id, FALSE, FALSE, TRUE,
                    '["dni","photo","driving_license","legal_terms"]'::jsonb,
                    TRUE, NOW()
                FROM tenants t
                WHERE NOT EXISTS (
                    SELECT 1 FROM clock_settings s WHERE s.tenant_id = t.id
                )
                """
            )
        )

    print("Migración clock_settings v1 OK.")


if __name__ == "__main__":
    main()
