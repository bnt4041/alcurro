"""Tipología, etiquetas, caducidad y tenant en documentos."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)

DEFAULT_TYPES = [
    ("nomina", "Nómina", 0),
    ("contrato", "Contrato", 1),
    ("certificado", "Certificado", 2),
    ("comunicado", "Comunicado", 3),
    ("otro", "Otro", 4),
]


def table_exists(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def column_exists(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not table_exists(conn, "document_types"):
            conn.execute(
                text(
                    """
                    CREATE TABLE document_types (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        code VARCHAR(50) NOT NULL,
                        name VARCHAR(120) NOT NULL,
                        description VARCHAR(500),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE (tenant_id, code)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_document_types_tenant_id ON document_types (tenant_id)"
                )
            )
            print("Tabla document_types creada.")

        if not table_exists(conn, "document_tags"):
            conn.execute(
                text(
                    """
                    CREATE TABLE document_tags (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        name VARCHAR(80) NOT NULL,
                        color VARCHAR(20),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE (tenant_id, name)
                    )
                    """
                )
            )
            print("Tabla document_tags creada.")

        if not table_exists(conn, "document_delivery_tags"):
            conn.execute(
                text(
                    """
                    CREATE TABLE document_delivery_tags (
                        id UUID PRIMARY KEY,
                        document_delivery_id UUID NOT NULL
                            REFERENCES document_deliveries(id) ON DELETE CASCADE,
                        tag_id UUID NOT NULL REFERENCES document_tags(id) ON DELETE CASCADE,
                        UNIQUE (document_delivery_id, tag_id)
                    )
                    """
                )
            )
            print("Tabla document_delivery_tags creada.")

        for col, ddl in (
            ("tenant_id", "UUID REFERENCES tenants(id)"),
            ("document_type_id", "UUID REFERENCES document_types(id)"),
            ("title", "VARCHAR(255)"),
            ("expires_at", "DATE"),
        ):
            if not column_exists(conn, "document_deliveries", col):
                conn.execute(
                    text(f"ALTER TABLE document_deliveries ADD COLUMN {col} {ddl}")
                )
                print(f"Columna document_deliveries.{col} creada.")

        conn.execute(
            text(
                """
                UPDATE document_deliveries d
                SET tenant_id = c.tenant_id
                FROM companies c
                WHERE d.company_id = c.id AND d.tenant_id IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE document_deliveries d
                SET tenant_id = c.tenant_id
                FROM employees e
                JOIN companies c ON e.company_id = c.id
                WHERE d.employee_id = e.id AND d.tenant_id IS NULL
                """
            )
        )

        tenants = conn.execute(text("SELECT id FROM tenants")).fetchall()
        for (tenant_id,) in tenants:
            tid = str(tenant_id)
            for code, name, order in DEFAULT_TYPES:
                conn.execute(
                    text(
                        """
                        INSERT INTO document_types (
                            id, tenant_id, code, name, sort_order, is_active, created_at
                        )
                        SELECT gen_random_uuid(), CAST(:tid AS uuid), CAST(:code AS varchar(50)),
                               CAST(:name AS varchar(120)), :ord, TRUE, NOW()
                        WHERE NOT EXISTS (
                            SELECT 1 FROM document_types
                            WHERE tenant_id = CAST(:tid_check AS uuid)
                              AND code = CAST(:code_check AS varchar(50))
                        )
                        """
                    ),
                    {
                        "tid": tid,
                        "tid_check": tid,
                        "code": code,
                        "code_check": code,
                        "name": name,
                        "ord": order,
                    },
                )
        conn.execute(
            text(
                """
                UPDATE document_deliveries d
                SET document_type_id = dt.id
                FROM document_types dt
                WHERE d.tenant_id = dt.tenant_id
                  AND d.document_type = dt.code
                  AND d.document_type_id IS NULL
                """
            )
        )

        if column_exists(conn, "document_deliveries", "tenant_id"):
            try:
                conn.execute(
                    text(
                        """
                        ALTER TABLE document_deliveries
                        ALTER COLUMN tenant_id SET NOT NULL
                        """
                    )
                )
            except Exception:
                pass

    print("Migración documentos v2 OK.")


if __name__ == "__main__":
    main()
