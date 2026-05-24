"""Columna work_schedule_periods en employees."""

import json
import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def column_exists(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not column_exists(conn, "employees", "work_schedule_periods"):
            conn.execute(
                text(
                    """
                    ALTER TABLE employees
                    ADD COLUMN work_schedule_periods JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            print("Columna employees.work_schedule_periods creada.")
        else:
            print("Columna employees.work_schedule_periods ya existe.")

        rows = conn.execute(
            text(
                """
                SELECT id, work_schedule_blocks, work_schedule_periods
                FROM employees
                WHERE work_schedule_periods = '[]'::jsonb
                  AND work_schedule_blocks IS NOT NULL
                  AND work_schedule_blocks::text != '[]'
                """
            )
        ).fetchall()

        from datetime import date

        today = date.today().isoformat()
        migrated = 0
        for row in rows:
            blocks = row.work_schedule_blocks
            if isinstance(blocks, str):
                blocks = json.loads(blocks)
            if not blocks:
                continue
            norm_blocks = []
            for b in blocks:
                if b.get("slots"):
                    norm_blocks.append(b)
                else:
                    norm_blocks.append(
                        {
                            "work_days": b.get("work_days", [0, 1, 2, 3, 4]),
                            "slots": [
                                {
                                    "work_start_time": b.get(
                                        "work_start_time", "09:00:00"
                                    ),
                                    "work_end_time": b.get(
                                        "work_end_time", "18:00:00"
                                    ),
                                    "break_minutes": b.get("break_minutes", 0),
                                }
                            ],
                        }
                    )
            period = {
                "valid_from": today,
                "valid_to": None,
                "blocks": norm_blocks,
            }
            conn.execute(
                text(
                    """
                    UPDATE employees
                    SET work_schedule_periods = :periods::jsonb
                    WHERE id = :id
                    """
                ),
                {"id": str(row.id), "periods": json.dumps([period])},
            )
            migrated += 1
        if migrated:
            print(f"Migrados {migrated} empleados a work_schedule_periods.")


if __name__ == "__main__":
    main()
