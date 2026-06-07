"""
Migration: add leave_types table and leave_type_id to leave_requests.

Inserts two default types per tenant:
  - Vacaciones (deducts_balance=True)
  - Baja       (deducts_balance=False)
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = inspector.get_table_names()

        # 1. Create leave_types table
        if "leave_types" not in tables:
            conn.execute(text("""
                CREATE TABLE leave_types (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    name            VARCHAR(100) NOT NULL,
                    deducts_balance BOOLEAN NOT NULL DEFAULT TRUE,
                    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                    sort_order      INTEGER NOT NULL DEFAULT 0,
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(text(
                "CREATE INDEX ix_leave_types_tenant_id ON leave_types (tenant_id)"
            ))
            print("migrate_leave_types_v1: created leave_types table")

        # 2. Add leave_type_id column to leave_requests (nullable for backwards compat)
        lr_cols = {c["name"] for c in inspector.get_columns("leave_requests")}
        if "leave_type_id" not in lr_cols:
            conn.execute(text("""
                ALTER TABLE leave_requests
                    ADD COLUMN leave_type_id UUID REFERENCES leave_types(id)
            """))
            print("migrate_leave_types_v1: added leave_type_id column")

        # 3. Seed default types for every existing tenant
        tenants = conn.execute(text("SELECT id FROM tenants")).fetchall()
        seeded = 0
        for (tenant_id,) in tenants:
            seeded += _seed_defaults(conn, tenant_id)
        if seeded:
            print(f"migrate_leave_types_v1: seeded {seeded} default leave types")


def _seed_defaults(conn, tenant_id) -> int:
    existing = conn.execute(
        text("SELECT name FROM leave_types WHERE tenant_id = :tid AND is_default = TRUE"),
        {"tid": tenant_id},
    ).fetchall()
    existing_names = {r[0] for r in existing}

    defaults = [
        ("Vacaciones", True, 0),
        ("Baja", False, 1),
    ]
    count = 0
    for name, deducts, sort_order in defaults:
        if name not in existing_names:
            conn.execute(
                text("""
                    INSERT INTO leave_types
                        (id, tenant_id, name, deducts_balance, is_default, is_active, sort_order, created_at)
                    VALUES
                        (:id, :tid, :name, :deducts, TRUE, TRUE, :sort_order, NOW())
                """),
                {
                    "id": str(uuid4()),
                    "tid": str(tenant_id),
                    "name": name,
                    "deducts": deducts,
                    "sort_order": sort_order,
                },
            )
            count += 1
    return count


if __name__ == "__main__":
    main()
