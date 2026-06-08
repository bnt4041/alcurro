"""Migration: add pending_plan_id and pending_billing_cycle to subscriptions."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://hrm:hrm@postgres:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        cols = {c["name"] for c in inspect(conn).get_columns("subscriptions")}
        for col, definition in [
            ("pending_plan_id", "UUID REFERENCES pricing_plans(id)"),
            ("pending_billing_cycle", "VARCHAR(20)"),
        ]:
            if col not in cols:
                conn.execute(text(f"ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS {col} {definition}"))
                print(f"migrate_pending_plan_v1: added {col}")


if __name__ == "__main__":
    main()
