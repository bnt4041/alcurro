"""Migration: add has_own_balance/default_days to leave_types + employee_leave_balances table."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        lt_cols = {c["name"] for c in inspect(conn).get_columns("leave_types")}

        if "has_own_balance" not in lt_cols:
            conn.execute(text(
                "ALTER TABLE leave_types ADD COLUMN has_own_balance BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            print("migrate_leave_balance_v1: added has_own_balance to leave_types")

        if "default_days" not in lt_cols:
            conn.execute(text(
                "ALTER TABLE leave_types ADD COLUMN default_days DOUBLE PRECISION"
            ))
            print("migrate_leave_balance_v1: added default_days to leave_types")

        tables = inspect(conn).get_table_names()
        if "employee_leave_balances" not in tables:
            conn.execute(text("""
                CREATE TABLE employee_leave_balances (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    leave_type_id   UUID NOT NULL REFERENCES leave_types(id) ON DELETE CASCADE,
                    total_days      DOUBLE PRECISION NOT NULL DEFAULT 0,
                    notes           VARCHAR(500),
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_emp_leave_type UNIQUE (employee_id, leave_type_id)
                )
            """))
            conn.execute(text(
                "CREATE INDEX ix_emp_leave_balances_employee ON employee_leave_balances (employee_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_emp_leave_balances_type ON employee_leave_balances (leave_type_id)"
            ))
            print("migrate_leave_balance_v1: created employee_leave_balances table")


if __name__ == "__main__":
    main()
