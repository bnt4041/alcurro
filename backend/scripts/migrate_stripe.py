"""
Columnas Stripe y tabla stripe_payments.

Uso: python -m scripts.migrate_stripe
"""

from sqlalchemy import text

from app.database import engine


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
        if not column_exists(conn, "tenants", "stripe_customer_id"):
            conn.execute(
                text(
                    "ALTER TABLE tenants ADD COLUMN stripe_customer_id VARCHAR(120)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_tenants_stripe_customer_id "
                    "ON tenants (stripe_customer_id)"
                )
            )

        for col in [
            "stripe_product_id",
            "stripe_price_monthly_id",
            "stripe_price_annual_id",
        ]:
            if not column_exists(conn, "pricing_plans", col):
                conn.execute(
                    text(f"ALTER TABLE pricing_plans ADD COLUMN {col} VARCHAR(120)")
                )

        for col in ["stripe_subscription_id", "stripe_checkout_session_id"]:
            if not column_exists(conn, "subscriptions", col):
                conn.execute(
                    text(f"ALTER TABLE subscriptions ADD COLUMN {col} VARCHAR(120)")
                )
        if column_exists(conn, "subscriptions", "stripe_subscription_id"):
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_subscription_id "
                    "ON subscriptions (stripe_subscription_id)"
                )
            )

        if not table_exists(conn, "stripe_payments"):
            conn.execute(
                text(
                    """
                    CREATE TABLE stripe_payments (
                        id UUID PRIMARY KEY,
                        tenant_id UUID REFERENCES tenants(id),
                        subscription_id UUID REFERENCES subscriptions(id),
                        stripe_payment_intent_id VARCHAR(120),
                        stripe_invoice_id VARCHAR(120),
                        stripe_checkout_session_id VARCHAR(120),
                        amount_cents INTEGER NOT NULL DEFAULT 0,
                        currency VARCHAR(3) DEFAULT 'EUR',
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        description VARCHAR(500),
                        paid_at TIMESTAMP,
                        created_at TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_stripe_payments_tenant_id "
                    "ON stripe_payments (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_stripe_payments_stripe_invoice_id "
                    "ON stripe_payments (stripe_invoice_id)"
                )
            )
        conn.commit()
    print("Migración Stripe OK.")


if __name__ == "__main__":
    main()
