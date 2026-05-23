"""
Migración: facturación por empresa, suscripciones y métodos de pago.

Uso: python -m scripts.migrate_company_billing
"""

from sqlalchemy import text
from sqlmodel import Session, select

from app.database import engine
from app.models.billing import Subscription
from app.models.tenant import Company, Tenant
from app.services.billing_service import (
    copy_tenant_billing_to_company,
    ensure_default_subscription,
)


def column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    )
    return r.first() is not None


def main() -> None:
    company_cols = [
        ("legal_name", "VARCHAR(200)"),
        ("billing_email", "VARCHAR(255)"),
        ("billing_phone", "VARCHAR(30)"),
        ("billing_address", "VARCHAR(300)"),
        ("billing_city", "VARCHAR(100)"),
        ("billing_postal_code", "VARCHAR(20)"),
        ("billing_province", "VARCHAR(100)"),
        ("billing_country", "VARCHAR(2) DEFAULT 'ES'"),
    ]

    with engine.connect() as conn:
        for col, typ in company_cols:
            if not column_exists(conn, "companies", col):
                conn.execute(text(f"ALTER TABLE companies ADD COLUMN {col} {typ}"))
        conn.commit()

    with Session(engine) as session:
        tenants = list(session.exec(select(Tenant)).all())
        for tenant in tenants:
            companies = list(
                session.exec(select(Company).where(Company.tenant_id == tenant.id)).all()
            )
            for company in companies:
                copy_tenant_billing_to_company(tenant, company)
                session.add(company)
                ensure_default_subscription(session, tenant, company)
        session.commit()
        print(f"Migración OK: {len(tenants)} cuentas, suscripciones por empresa.")


if __name__ == "__main__":
    main()
