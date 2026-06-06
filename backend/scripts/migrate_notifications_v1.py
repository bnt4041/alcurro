"""Notificaciones v1: job_title en empleados, tablas de notificaciones, migrar manager→employee."""

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
        inspector = inspect(conn)
        tables = inspector.get_table_names()
        columns = {c["name"] for c in inspector.get_columns("employees")}

        # 1. job_title en employees
        if "job_title" not in columns:
            conn.execute(text("ALTER TABLE employees ADD COLUMN job_title VARCHAR(100)"))
            print("Columna employees.job_title añadida.")
        else:
            print("Columna employees.job_title ya existe.")

        # 2. Migrar role manager → EMPLOYEE
        conn.execute(
            text("UPDATE employees SET role = 'EMPLOYEE' WHERE role = 'manager'")
        )
        print("Empleados con role=manager migrados a EMPLOYEE.")

        # 3. Tabla notification_preferences
        if "notification_preferences" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE notification_preferences (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                        event_type VARCHAR(50) NOT NULL,
                        channel VARCHAR(20) NOT NULL,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_notif_pref_employee ON notification_preferences (employee_id)"
                )
            )
            print("Tabla notification_preferences creada.")
        else:
            print("Tabla notification_preferences ya existe.")

        # 4. Tabla notifications
        if "notifications" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE notifications (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                        employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                        event_type VARCHAR(50) NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        body VARCHAR(1000) NOT NULL,
                        link VARCHAR(500),
                        actor_name VARCHAR(200),
                        read_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_notifications_employee ON notifications (employee_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_notifications_tenant ON notifications (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_notifications_created ON notifications (created_at DESC)"
                )
            )
            print("Tabla notifications creada.")
        else:
            print("Tabla notifications ya existe.")


if __name__ == "__main__":
    main()
