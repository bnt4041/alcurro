#!/usr/bin/env python3
"""
Migración v2: añade ls_product_id a pricing_plans.
Idempotente (IF NOT EXISTS).
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
            cur.execute("""
                ALTER TABLE pricing_plans
                ADD COLUMN IF NOT EXISTS ls_product_id VARCHAR(80);
            """)
        conn.commit()
    print("✓ Migración lemon_squeezy_v2 completada")


if __name__ == "__main__":
    run()
