"""Tablas legales y columnas de horario en employees."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def column_exists(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        tables = inspect(conn).get_table_names()

        if "legal_documents" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE legal_documents (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        code VARCHAR(50) NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        body TEXT NOT NULL,
                        version INTEGER NOT NULL DEFAULT 1,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_required BOOLEAN NOT NULL DEFAULT TRUE,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        CONSTRAINT uq_legal_doc_tenant_code UNIQUE (tenant_id, code)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_legal_documents_tenant_id ON legal_documents (tenant_id)"
                )
            )
            print("Tabla legal_documents creada.")
        else:
            print("Tabla legal_documents ya existe.")

        if "legal_acceptances" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE legal_acceptances (
                        id UUID PRIMARY KEY,
                        employee_id UUID NOT NULL REFERENCES employees(id),
                        legal_document_id UUID NOT NULL REFERENCES legal_documents(id),
                        document_version INTEGER NOT NULL,
                        accepted_at TIMESTAMP NOT NULL,
                        CONSTRAINT uq_legal_acceptance_employee_doc
                            UNIQUE (employee_id, legal_document_id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_legal_acceptances_employee_id ON legal_acceptances (employee_id)"
                )
            )
            print("Tabla legal_acceptances creada.")
        else:
            print("Tabla legal_acceptances ya existe.")

        if not column_exists(conn, "employees", "shift_configuration_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE employees
                    ADD COLUMN shift_configuration_id UUID
                        REFERENCES shift_configurations(id)
                    """
                )
            )
            print("Columna employees.shift_configuration_id creada.")
        if not column_exists(conn, "employees", "work_start_time"):
            conn.execute(
                text("ALTER TABLE employees ADD COLUMN work_start_time TIME")
            )
            print("Columna employees.work_start_time creada.")
        if not column_exists(conn, "employees", "work_end_time"):
            conn.execute(
                text("ALTER TABLE employees ADD COLUMN work_end_time TIME")
            )
            print("Columna employees.work_end_time creada.")
        if not column_exists(conn, "employees", "work_days"):
            conn.execute(
                text(
                    """
                    ALTER TABLE employees
                    ADD COLUMN work_days JSONB NOT NULL DEFAULT '[0,1,2,3,4]'::jsonb
                    """
                )
            )
            print("Columna employees.work_days creada.")

    from sqlmodel import Session, select

    from app.database import engine as app_engine
    from app.models.tenant import Tenant
    from app.services.legal_service import seed_default_legal_documents

    with Session(app_engine) as session:
        for tenant in session.exec(select(Tenant)).all():
            seed_default_legal_documents(session, tenant.id)
        session.commit()
    print("Documentos legales por defecto verificados para todos los tenants.")


if __name__ == "__main__":
    main()
