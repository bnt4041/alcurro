"""Tablas de incidencias y reglas automáticas."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def table_exists(conn, table: str) -> bool:
    return table in inspect(conn).get_table_names()


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not table_exists(conn, "incident_auto_rules"):
            conn.execute(
                text(
                    """
                    CREATE TABLE incident_auto_rules (
                        tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
                        late_entrada_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        late_entrada_grace_minutes INTEGER NOT NULL DEFAULT 10,
                        late_entrada_notify_whatsapp BOOLEAN NOT NULL DEFAULT TRUE,
                        late_entrada_require_justification BOOLEAN NOT NULL DEFAULT TRUE,
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla incident_auto_rules creada.")

        if not table_exists(conn, "incidents"):
            conn.execute(
                text(
                    """
                    CREATE TABLE incidents (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        employee_id UUID NOT NULL REFERENCES employees(id),
                        category VARCHAR(30) NOT NULL,
                        incident_type VARCHAR(50) NOT NULL,
                        status VARCHAR(30) NOT NULL DEFAULT 'open',
                        source VARCHAR(20) NOT NULL DEFAULT 'auto',
                        title VARCHAR(300) NOT NULL,
                        description VARCHAR(2000),
                        clock_in_id UUID REFERENCES clock_ins(id),
                        leave_request_id UUID REFERENCES leave_requests(id),
                        minutes_late INTEGER,
                        original_data JSON NOT NULL DEFAULT '{}',
                        modified_data JSON,
                        employee_justification VARCHAR(3000),
                        internal_notes VARCHAR(2000),
                        public_token VARCHAR(64),
                        whatsapp_notified_at TIMESTAMP,
                        justified_at TIMESTAMP,
                        resolved_at TIMESTAMP,
                        resolved_by_id UUID REFERENCES employees(id),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_incidents_tenant ON incidents (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_incidents_employee ON incidents (employee_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_incidents_public_token "
                    "ON incidents (public_token) WHERE public_token IS NOT NULL"
                )
            )
            print("Tabla incidents creada.")


if __name__ == "__main__":
    main()
