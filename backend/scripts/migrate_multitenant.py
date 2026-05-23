"""Migración a multi-tenant. docker exec hrm-backend python -m scripts.migrate_multitenant"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.security import hash_password
from app.database import engine, create_db_and_tables
from app.models.models import Employee, Role, ShiftConfiguration
from app.models.tenant import Company, Tenant
from sqlmodel import Session, select

DEFAULT_SLUG = "demo"
DEFAULT_PASSWORD = "admin123"


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return r.first() is not None


def migrate() -> None:
    create_db_and_tables()
    with engine.connect() as conn:
        if not _column_exists(conn, "employees", "company_id"):
            conn.execute(
                text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS company_id UUID")
            )
            conn.execute(
                text(
                    "ALTER TABLE shift_configurations "
                    "ADD COLUMN IF NOT EXISTS company_id UUID"
                )
            )
            conn.commit()

    with Session(engine) as session:
        tenant = session.exec(
            select(Tenant).where(Tenant.slug == DEFAULT_SLUG)
        ).first()
        if not tenant:
            tenant = Tenant(
                slug=DEFAULT_SLUG,
                name="Cuenta Demo",
                gowa_webhook_path=f"/webhook/whatsapp/{DEFAULT_SLUG}",
            )
            session.add(tenant)
            session.flush()

        company = session.exec(
            select(Company).where(Company.tenant_id == tenant.id)
        ).first()
        if not company:
            company = Company(tenant_id=tenant.id, name="Empresa Principal")
            session.add(company)
            session.flush()

        for emp in session.exec(select(Employee)).all():
            if not getattr(emp, "company_id", None):
                emp.company_id = company.id
                session.add(emp)
            if emp.role in (Role.ADMIN, Role.SUPERVISOR, Role.LABOR_INSPECTOR):
                if not emp.password_hash:
                    emp.password_hash = hash_password(DEFAULT_PASSWORD)

        for sc in session.exec(select(ShiftConfiguration)).all():
            if not getattr(sc, "company_id", None):
                sc.company_id = company.id
                session.add(sc)

        session.commit()

    print("Migración multi-tenant OK")
    print(f"  Tenant: {DEFAULT_SLUG}")
    print(f"  Login: {DEFAULT_SLUG} / ADM001 / {DEFAULT_PASSWORD}")
    print("  Provisionar goWA: POST /api/tenants/current/provision-gowa (como admin)")


if __name__ == "__main__":
    migrate()
