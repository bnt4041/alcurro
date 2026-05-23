"""Jerarquía org: centros, departamentos, department_id en empleados, plantillas de grupos.

Uso: python -m scripts.migrate_org_hierarchy
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models.models import Employee
from app.models.organization import Department, WorkCenter
from app.models.tenant import Company, Tenant
from app.services.org_service import (
    clone_groups_for_tenant,
    ensure_group_templates,
    seed_tenant_organization,
)


def _column_exists(conn, table: str, column: str) -> bool:
    r = conn.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).first()
    return r is not None


def migrate() -> None:
    create_db_and_tables()
    with engine.connect() as conn:
        if not _column_exists(conn, "employees", "department_id"):
            conn.execute(
                text(
                    "ALTER TABLE employees ADD COLUMN department_id UUID "
                    "REFERENCES departments(id)"
                )
            )
            print("+ employees.department_id")
        conn.commit()

    with Session(engine) as session:
        ensure_group_templates(session)
        for tenant in session.exec(select(Tenant)).all():
            companies = session.exec(
                select(Company).where(Company.tenant_id == tenant.id)
            ).all()
            if not companies:
                seed_tenant_organization(session, tenant)
                companies = session.exec(
                    select(Company).where(Company.tenant_id == tenant.id)
                ).all()
            for company in companies:
                wc = session.exec(
                    select(WorkCenter).where(WorkCenter.company_id == company.id)
                ).first()
                if not wc:
                    wc = WorkCenter(
                        company_id=company.id,
                        name="Centro principal",
                        code="CENTRO-01",
                    )
                    session.add(wc)
                    session.flush()
                dept = session.exec(
                    select(Department).where(Department.work_center_id == wc.id)
                ).first()
                if not dept:
                    dept = Department(
                        work_center_id=wc.id, name="General", code="GEN"
                    )
                    session.add(dept)
                    session.flush()
                for emp in session.exec(
                    select(Employee).where(Employee.company_id == company.id)
                ).all():
                    if not emp.department_id:
                        emp.department_id = dept.id
                        session.add(emp)
            from app.models.rbac import UserGroup

            if not session.exec(
                select(UserGroup).where(UserGroup.tenant_id == tenant.id)
            ).first():
                clone_groups_for_tenant(session, tenant.id)
        session.commit()
    print("Migración jerarquía organizativa OK.")


if __name__ == "__main__":
    migrate()
