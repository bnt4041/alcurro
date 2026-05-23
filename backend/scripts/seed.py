"""Carga tenant demo + empleados. Uso: python -m scripts.seed"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.core.security import hash_password
from app.database import create_db_and_tables, engine
from app.models.models import Employee, Role, ShiftConfiguration, ShiftPatternType
from app.models.rbac import PlatformUser
from app.models.tenant import Company, Tenant
from app.services.rbac_service import ensure_system_groups, assign_role_default_group

PANEL_PASSWORD = "admin123"
TENANT_SLUG = "demo"


def seed() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        tenant = session.exec(select(Tenant).where(Tenant.slug == TENANT_SLUG)).first()
        if not tenant:
            tenant = Tenant(
                slug=TENANT_SLUG,
                name="Cuenta Demo",
                primary_color="#25d366",
                secondary_color="#12263a",
                accent_color="#25d366",
                legal_name="Cuenta Demo S.L.",
                tax_id="B12345678",
                billing_email="facturacion@demo.local",
                billing_address="Calle Ejemplo 1",
                billing_city="Madrid",
                billing_postal_code="28001",
                billing_province="Madrid",
                billing_country="ES",
                gowa_webhook_path=f"/webhook/whatsapp/{TENANT_SLUG}",
            )
            session.add(tenant)
            session.flush()

        company = session.exec(
            select(Company).where(Company.tenant_id == tenant.id)
        ).first()
        if not company:
            company = Company(tenant_id=tenant.id, name="Empresa Principal")
            session.add(company)
            session.flush()

        ensure_system_groups(session, tenant.id)

        if not session.exec(select(PlatformUser)).first():
            session.add(
                PlatformUser(
                    email="platform@hrm.local",
                    full_name="Admin Plataforma",
                    password_hash=hash_password("platform123"),
                )
            )

        if session.exec(
            select(Employee).where(Employee.company_id == company.id)
        ).first():
            sync_msg = "BD ya tiene empleados — sincronizando grupos."
            from app.services.rbac_service import sync_tenant_groups

            sync_tenant_groups(session, tenant.id)
            session.commit()
            print(sync_msg)
            return

        admin = Employee(
            company_id=company.id,
            phone="34600000001",
            email="admin@empresa.local",
            full_name="Admin RRHH",
            employee_code="ADM001",
            role=Role.TENANT_ADMIN,
            vacation_days_balance=30,
            password_hash=hash_password(PANEL_PASSWORD),
        )
        supervisor = Employee(
            company_id=company.id,
            phone="34600000002",
            email="supervisor@empresa.local",
            full_name="María García (Supervisor)",
            employee_code="SUP001",
            role=Role.MANAGER,
            vacation_days_balance=25,
            password_hash=hash_password(PANEL_PASSWORD),
        )
        inspector = Employee(
            company_id=company.id,
            phone="34600000003",
            email="inspector@empresa.local",
            full_name="Inspector Trabajo",
            employee_code="INS001",
            role=Role.LABOR_INSPECTOR,
            vacation_days_balance=0,
            password_hash=hash_password(PANEL_PASSWORD),
        )
        session.add(admin)
        session.add(supervisor)
        session.add(inspector)
        session.flush()
        for emp in (admin, supervisor, inspector):
            assign_role_default_group(session, emp, tenant.id)
        supervisor.supervisor_id = admin.id
        employee = Employee(
            company_id=company.id,
            phone="34600111222",
            email="empleado@empresa.local",
            full_name="Juan Pérez",
            employee_code="EMP001",
            role=Role.EMPLOYEE,
            vacation_days_balance=22,
            supervisor_id=supervisor.id,
        )
        session.add(employee)

        shift = ShiftConfiguration(
            company_id=company.id,
            name="Oficina L-V 8-17",
            pattern_type=ShiftPatternType.RIGID,
            weekly_hours=40,
            pattern_definition={
                "slots": [
                    {"day": d, "start": "08:00", "end": "17:00"}
                    for d in range(0, 5)
                ]
            },
        )
        session.add(shift)
        session.commit()
        print("Seed OK — login panel:")
        print(f"  Cuenta (tenant): {TENANT_SLUG}")
        print(f"  Contraseña: {PANEL_PASSWORD}")
        print("  Usuario cuenta: ADM001 / SUP001 / INS001")
        print("  Plataforma: platform@hrm.local / platform123")


if __name__ == "__main__":
    seed()
