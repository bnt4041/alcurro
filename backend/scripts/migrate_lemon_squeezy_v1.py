#!/usr/bin/env python3
"""
Migración: integración Lemon Squeezy.
Crea tabla ls_payments y añade columnas en pricing_plans, subscriptions,
tenants e invoices.
Se puede ejecutar varias veces de forma segura (IF NOT EXISTS).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.config import get_settings


def run() -> None:
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            # Tabla de pagos de Lemon Squeezy
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ls_payments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID REFERENCES tenants(id),
                    subscription_id UUID REFERENCES subscriptions(id),
                    ls_order_id VARCHAR(80),
                    ls_subscription_id VARCHAR(80),
                    ls_invoice_id VARCHAR(80),
                    amount_cents INTEGER NOT NULL DEFAULT 0,
                    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    description VARCHAR(500),
                    invoice_number VARCHAR(50),
                    receipt_url TEXT,
                    paid_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ls_payments_tenant ON ls_payments(tenant_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ls_payments_order ON ls_payments(ls_order_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ls_payments_sub ON ls_payments(ls_subscription_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ls_payments_invoice ON ls_payments(ls_invoice_id);")

            # Variantes de Lemon Squeezy en los planes de precios
            cur.execute("""
                ALTER TABLE pricing_plans
                ADD COLUMN IF NOT EXISTS ls_variant_id_monthly VARCHAR(80),
                ADD COLUMN IF NOT EXISTS ls_variant_id_annual VARCHAR(80);
            """)

            # Campos de suscripción para LS y control de fallos de pago
            cur.execute("""
                ALTER TABLE subscriptions
                ADD COLUMN IF NOT EXISTS ls_subscription_id VARCHAR(80),
                ADD COLUMN IF NOT EXISTS payment_failure_count INTEGER NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_payment_failure_at TIMESTAMP;
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_ls_sub ON subscriptions(ls_subscription_id);")

            # Customer ID y portal URL de LS en el tenant
            cur.execute("""
                ALTER TABLE tenants
                ADD COLUMN IF NOT EXISTS ls_customer_id VARCHAR(80),
                ADD COLUMN IF NOT EXISTS ls_customer_portal_url TEXT;
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tenants_ls_customer ON tenants(ls_customer_id);")

            # FK a ls_payments en la tabla de facturas internas
            cur.execute("""
                ALTER TABLE invoices
                ADD COLUMN IF NOT EXISTS ls_payment_id UUID REFERENCES ls_payments(id);
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_ls_payment ON invoices(ls_payment_id);")

        conn.commit()
    print("✓ Migración lemon_squeezy_v1 completada")


if __name__ == "__main__":
    run()
