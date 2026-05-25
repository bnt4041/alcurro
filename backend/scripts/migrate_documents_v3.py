"""Avisos de caducidad configurables."""

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
        if not table_exists(conn, "document_notification_settings"):
            conn.execute(
                text(
                    """
                    CREATE TABLE document_notification_settings (
                        tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
                        enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        days_before VARCHAR(100) NOT NULL DEFAULT '30,7,1',
                        channel_whatsapp BOOLEAN NOT NULL DEFAULT TRUE,
                        channel_email BOOLEAN NOT NULL DEFAULT TRUE,
                        notify_employee BOOLEAN NOT NULL DEFAULT TRUE,
                        notify_managers BOOLEAN NOT NULL DEFAULT TRUE,
                        extra_emails VARCHAR(500),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla document_notification_settings creada.")

        if not table_exists(conn, "document_expiry_notification_logs"):
            conn.execute(
                text(
                    """
                    CREATE TABLE document_expiry_notification_logs (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        document_delivery_id UUID NOT NULL
                            REFERENCES document_deliveries(id) ON DELETE CASCADE,
                        days_before INTEGER NOT NULL,
                        channel VARCHAR(20) NOT NULL,
                        recipient VARCHAR(255) NOT NULL,
                        success BOOLEAN NOT NULL DEFAULT TRUE,
                        detail VARCHAR(500),
                        sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE (document_delivery_id, days_before, channel, recipient)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_doc_expiry_logs_tenant ON document_expiry_notification_logs (tenant_id)"
                )
            )
            print("Tabla document_expiry_notification_logs creada.")

        conn.execute(
            text(
                """
                INSERT INTO document_notification_settings (
                    tenant_id, enabled, days_before,
                    channel_whatsapp, channel_email,
                    notify_employee, notify_managers, updated_at
                )
                SELECT id, FALSE, '30,7,1', TRUE, TRUE, TRUE, TRUE, NOW()
                FROM tenants t
                WHERE NOT EXISTS (
                    SELECT 1 FROM document_notification_settings s
                    WHERE s.tenant_id = t.id
                )
                """
            )
        )

    print("Migración documentos v3 OK.")


if __name__ == "__main__":
    main()
