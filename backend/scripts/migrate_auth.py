"""Añade password_hash y establece contraseñas de panel. docker exec hrm-backend python -m scripts.migrate_auth"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.security import hash_password
from app.database import engine
from app.models.models import Role
from sqlmodel import Session, select

from app.models.models import Employee

DEFAULT_PASSWORD = "admin123"


def migrate() -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
            )
        )
        conn.commit()
    with Session(engine) as session:
        panel_roles = {Role.ADMIN, Role.SUPERVISOR, Role.LABOR_INSPECTOR}
        for emp in session.exec(select(Employee)).all():
            if emp.role in panel_roles and not emp.password_hash:
                emp.password_hash = hash_password(DEFAULT_PASSWORD)
                session.add(emp)
        session.commit()
    print(f"Migración OK. Contraseña panel para admin/supervisor/inspector: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    migrate()
