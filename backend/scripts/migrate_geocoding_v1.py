"""Migration: add address column to clock_ins for reverse geocoding."""

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
        cols = {c["name"] for c in inspect(conn).get_columns("clock_ins")}
        for col, definition in [
            ("address",       "VARCHAR(500)"),
            ("latitude_out",  "DOUBLE PRECISION"),
            ("longitude_out", "DOUBLE PRECISION"),
            ("address_out",   "VARCHAR(500)"),
        ]:
            if col not in cols:
                conn.execute(text(f"ALTER TABLE clock_ins ADD COLUMN {col} {definition}"))
                print(f"migrate_geocoding_v1: added {col} column to clock_ins")


if __name__ == "__main__":
    main()
