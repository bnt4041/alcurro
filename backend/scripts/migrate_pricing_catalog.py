"""
Catálogo de tarifas y descuentos + enlaces en suscripciones.

Uso: python -m scripts.migrate_pricing_catalog
"""

from sqlalchemy import text
from sqlmodel import Session, select

from app.database import engine
from app.models.billing import PricingPlan, Subscription
from app.services.pricing_service import get_default_plan, sync_subscription_pricing
from app.models.billing import BillingCycle


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


def table_exists(conn, table: str) -> bool:
    r = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {"t": table},
    )
    return r.first() is not None


def main() -> None:
    with engine.connect() as conn:
        if not table_exists(conn, "pricing_plans"):
            conn.execute(
                text(
                    """
                    CREATE TABLE pricing_plans (
                        id UUID PRIMARY KEY,
                        code VARCHAR(50) UNIQUE NOT NULL,
                        name VARCHAR(120) NOT NULL,
                        description VARCHAR(500),
                        monthly_price_cents INTEGER NOT NULL,
                        annual_price_per_month_cents INTEGER NOT NULL,
                        max_active_users INTEGER NOT NULL DEFAULT 3,
                        currency VARCHAR(3) DEFAULT 'EUR',
                        is_active BOOLEAN DEFAULT TRUE,
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                )
            )
        if not table_exists(conn, "discounts"):
            conn.execute(
                text(
                    """
                    CREATE TABLE discounts (
                        id UUID PRIMARY KEY,
                        code VARCHAR(50) UNIQUE NOT NULL,
                        name VARCHAR(120) NOT NULL,
                        description VARCHAR(500),
                        discount_type VARCHAR(20) NOT NULL,
                        value INTEGER NOT NULL,
                        valid_from DATE NOT NULL,
                        valid_until DATE NOT NULL,
                        pricing_plan_id UUID REFERENCES pricing_plans(id),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                )
            )
        for col, typ in [
            ("pricing_plan_id", "UUID REFERENCES pricing_plans(id)"),
            ("discount_id", "UUID REFERENCES discounts(id)"),
        ]:
            if not column_exists(conn, "subscriptions", col):
                conn.execute(text(f"ALTER TABLE subscriptions ADD COLUMN {col} {typ}"))
        conn.commit()

    with Session(engine) as session:
        basica = session.exec(
            select(PricingPlan).where(PricingPlan.code == "basica")
        ).first()
        if not basica:
            basica = PricingPlan(
                code="basica",
                name="Básica",
                description="Hasta 3 usuarios activos. 18€/mes o 15€/mes con contrato anual.",
                monthly_price_cents=1800,
                annual_price_per_month_cents=1500,
                max_active_users=3,
                sort_order=0,
            )
            session.add(basica)
            session.commit()
            session.refresh(basica)
            print("Tarifa Básica creada.")

        subs = list(session.exec(select(Subscription)).all())
        for sub in subs:
            if not sub.pricing_plan_id:
                plan = get_default_plan(session) or basica
                sync_subscription_pricing(
                    session, sub, plan, sub.billing_cycle or BillingCycle.MONTHLY, None
                )
        session.commit()
        print(f"Migración OK. {len(subs)} suscripciones enlazadas.")


if __name__ == "__main__":
    main()
