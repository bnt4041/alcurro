#!/usr/bin/env python3
"""
Migración: crea las tablas platform_settings e invoices.
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
            # platform_settings (singleton)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS platform_settings (
                    id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000001',
                    legal_name VARCHAR(200) NOT NULL DEFAULT 'Alcurro SL',
                    tax_id VARCHAR(30) NOT NULL DEFAULT '',
                    billing_address VARCHAR(300),
                    billing_city VARCHAR(100),
                    billing_postal_code VARCHAR(10),
                    billing_province VARCHAR(100),
                    billing_country VARCHAR(2) NOT NULL DEFAULT 'ES',
                    billing_email VARCHAR(200),
                    billing_phone VARCHAR(30),
                    website VARCHAR(200),
                    iban VARCHAR(40),
                    bank_name VARCHAR(200),
                    swift_bic VARCHAR(20),
                    invoice_prefix VARCHAR(10) NOT NULL DEFAULT 'ALC',
                    invoice_next_number INTEGER NOT NULL DEFAULT 1,
                    invoice_current_year INTEGER NOT NULL DEFAULT 2024,
                    vat_rate INTEGER NOT NULL DEFAULT 21,
                    invoice_footer_text VARCHAR(500),
                    auto_send_invoice_email BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)

            # invoices
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(id),
                    number VARCHAR(50) NOT NULL UNIQUE,
                    recipient_legal_name VARCHAR(200),
                    recipient_tax_id VARCHAR(30),
                    recipient_address VARCHAR(300),
                    recipient_city VARCHAR(100),
                    recipient_postal_code VARCHAR(10),
                    recipient_province VARCHAR(100),
                    recipient_country VARCHAR(2) NOT NULL DEFAULT 'ES',
                    recipient_email VARCHAR(200),
                    concept VARCHAR(500) NOT NULL DEFAULT 'Suscripción alcurro',
                    base_cents INTEGER NOT NULL DEFAULT 0,
                    vat_rate INTEGER NOT NULL DEFAULT 21,
                    vat_cents INTEGER NOT NULL DEFAULT 0,
                    total_cents INTEGER NOT NULL DEFAULT 0,
                    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                    issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    due_date DATE,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    stripe_payment_id UUID REFERENCES stripe_payments(id),
                    credit_note_for_id UUID REFERENCES invoices(id),
                    pdf_url TEXT,
                    email_sent_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(number);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_stripe_payment ON invoices(stripe_payment_id);")
        conn.commit()
    print("✓ Migración billing_invoices completada")


if __name__ == "__main__":
    run()
