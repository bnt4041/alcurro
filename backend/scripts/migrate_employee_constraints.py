"""
Índices únicos de employees por empresa (no globales).

Uso: python -m scripts.migrate_employee_constraints
"""

from sqlalchemy import text

from app.database import engine


def main() -> None:
    with engine.connect() as conn:
        conn.execute(
            text("DROP INDEX IF EXISTS ix_employees_employee_code")
        )
        conn.execute(text("DROP INDEX IF EXISTS ix_employees_phone"))
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_code_company
                ON employees (company_id, employee_code)
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_phone_company
                ON employees (company_id, phone)
                """
            )
        )
        conn.commit()
    print("Índices de employees actualizados (único por empresa).")


if __name__ == "__main__":
    main()
