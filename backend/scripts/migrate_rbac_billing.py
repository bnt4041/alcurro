"""RBAC: grupos, permisos, facturación en tenants, admin plataforma.

Uso: python -m scripts.migrate_rbac_billing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.security import hash_password
from app.database import create_db_and_tables, engine
from app.models.models import Employee
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.services.rbac_service import sync_tenant_groups

PLATFORM_EMAIL = "platform@hrm.local"
PLATFORM_PASSWORD = "platform123"


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).first()
    return r is not None


def migrate() -> None:
    create_db_and_tables()
    billing_cols = [
        ("legal_name", "VARCHAR(200)"),
        ("tax_id", "VARCHAR(50)"),
        ("billing_email", "VARCHAR(255)"),
        ("billing_phone", "VARCHAR(30)"),
        ("billing_address", "VARCHAR(300)"),
        ("billing_city", "VARCHAR(100)"),
        ("billing_postal_code", "VARCHAR(20)"),
        ("billing_province", "VARCHAR(100)"),
        ("billing_country", "VARCHAR(2) DEFAULT 'ES'"),
    ]
    with engine.connect() as conn:
        for col, typ in billing_cols:
            if not _column_exists(conn, "tenants", col):
                conn.execute(text(f"ALTER TABLE tenants ADD COLUMN {col} {typ}"))
                print(f"+ tenants.{col}")
        conn.commit()

    for sql in (
        "ALTER TYPE role ADD VALUE IF NOT EXISTS 'tenant_admin'",
        "ALTER TYPE role ADD VALUE IF NOT EXISTS 'manager'",
    ):
        with engine.connect() as conn:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()

    with engine.connect() as conn:
        conn.execute(
            text("UPDATE employees SET role = 'tenant_admin' WHERE role::text = 'admin'")
        )
        conn.execute(
            text("UPDATE employees SET role = 'manager' WHERE role::text = 'supervisor'")
        )
        conn.commit()

    with Session(engine) as session:
        for tenant in session.exec(select(Tenant)).all():
            if not tenant.legal_name:
                tenant.legal_name = tenant.name
            if not tenant.billing_country:
                tenant.billing_country = "ES"
            session.add(tenant)
            sync_tenant_groups(session, tenant.id)

    with Session(engine) as session:
        platform = session.exec(
            select(PlatformUser).where(PlatformUser.email == PLATFORM_EMAIL)
        ).first()
        if not platform:
            platform = PlatformUser(
                email=PLATFORM_EMAIL,
                full_name="Administrador Plataforma",
                password_hash=hash_password(PLATFORM_PASSWORD),
            )
            session.add(platform)
            print(f"Admin plataforma: {PLATFORM_EMAIL} / {PLATFORM_PASSWORD}")

        session.commit()
    print("Migración RBAC + facturación OK.")


if __name__ == "__main__":
    migrate()
