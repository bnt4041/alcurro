#!/usr/bin/env python3
"""
Migración Paddle v1: renombra todos los campos/tablas de Lemon Squeezy a Paddle.

Idempotente: cada rename solo se ejecuta si la columna/tabla antigua existe y la
nueva no. Seguro de ejecutar en BD nuevas (no hace nada) y en BD con datos LS.

NOTA: create_all() corre antes que las migraciones, así que en una BD con datos
puede crear una tabla `paddle_payments` vacía junto a la `ls_payments` real. Este
script descarta la vacía y renombra la real conservando los datos históricos.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.config import get_settings


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return cur.fetchone() is not None


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
        (table, column),
    )
    return cur.fetchone() is not None


def _row_count(cur, table: str) -> int:
    cur.execute(f'SELECT count(*) FROM "{table}"')  # noqa: S608 (nombre validado)
    return cur.fetchone()[0]


def _rename_column(cur, table: str, old: str, new: str) -> None:
    if _column_exists(cur, table, old) and not _column_exists(cur, table, new):
        cur.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"')
        print(f"  · {table}.{old} → {new}")


def run() -> None:
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            # ── Tabla de pagos: ls_payments → paddle_payments ──────────────────
            ls_exists = _table_exists(cur, "ls_payments")
            paddle_exists = _table_exists(cur, "paddle_payments")
            if ls_exists:
                # create_all pudo crear una paddle_payments vacía: descartarla
                if paddle_exists and _row_count(cur, "paddle_payments") == 0:
                    cur.execute("DROP TABLE paddle_payments CASCADE")
                    print("  · DROP paddle_payments (vacía creada por create_all)")
                cur.execute("ALTER TABLE ls_payments RENAME TO paddle_payments")
                print("  · tabla ls_payments → paddle_payments")

            # Columnas de la tabla de pagos
            _rename_column(cur, "paddle_payments", "ls_order_id", "paddle_invoice_id")
            _rename_column(cur, "paddle_payments", "ls_subscription_id", "paddle_subscription_id")
            _rename_column(cur, "paddle_payments", "ls_invoice_id", "paddle_transaction_id")

            # ── pricing_plans ──────────────────────────────────────────────────
            _rename_column(cur, "pricing_plans", "ls_product_id", "paddle_product_id")
            _rename_column(cur, "pricing_plans", "ls_variant_id_monthly", "paddle_price_id_monthly")
            _rename_column(cur, "pricing_plans", "ls_variant_id_annual", "paddle_price_id_annual")

            # ── discounts ──────────────────────────────────────────────────────
            _rename_column(cur, "discounts", "ls_discount_id", "paddle_discount_id")

            # ── subscriptions ──────────────────────────────────────────────────
            _rename_column(cur, "subscriptions", "ls_subscription_id", "paddle_subscription_id")

            # ── pending_signups ────────────────────────────────────────────────
            _rename_column(cur, "pending_signups", "ls_subscription_id", "paddle_subscription_id")

            # ── tenants ────────────────────────────────────────────────────────
            _rename_column(cur, "tenants", "ls_customer_id", "paddle_customer_id")
            _rename_column(cur, "tenants", "ls_customer_portal_url", "paddle_customer_portal_url")

            # ── invoices (FK al pago) ──────────────────────────────────────────
            _rename_column(cur, "invoices", "ls_payment_id", "paddle_payment_id")

        conn.commit()
    print("✓ Migración paddle_v1 completada")


if __name__ == "__main__":
    run()
