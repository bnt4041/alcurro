"""Jerarquía organizativa y plantillas de grupos por defecto."""

from uuid import UUID

from sqlmodel import Session, select

# Permisos por defecto (evita import circular con permissions.py)
TENANT_ADMIN_PERMS = frozenset(
    {
        "employees.read",
        "employees.write",
        "employees.delete",
        "clock_ins.read",
        "clock_ins.write",
        "leave.read",
        "leave.write",
        "leave.approve",
        "shifts.read",
        "shifts.write",
        "documents.read",
        "documents.write",
        "settings.read",
        "settings.write",
        "tenant.read",
        "tenant.write",
        "tenant.billing",
        "companies.read",
        "companies.write",
        "work_centers.read",
        "work_centers.write",
        "departments.read",
        "departments.write",
        "groups.read",
        "groups.write",
        "gowa.manage",
    }
)
MANAGER_PERMS = frozenset(
    {
        "employees.read",
        "employees.write",
        "clock_ins.read",
        "clock_ins.write",
        "leave.read",
        "leave.write",
        "leave.approve",
        "shifts.read",
        "shifts.write",
        "documents.read",
        "documents.write",
        "tenant.read",
        "companies.read",
        "work_centers.read",
        "departments.read",
        "groups.read",
    }
)
INSPECTOR_PERMS = frozenset(
    {
        p
        for p in TENANT_ADMIN_PERMS
        if p.endswith(".read") or p == "leave.approve"
    }
)
from app.models.organization import Department, GroupTemplate, WorkCenter
from app.models.rbac import UserGroup
from app.models.tenant import Company, Tenant

DEFAULT_GROUP_TEMPLATES: list[tuple[str, str, frozenset[str], bool]] = [
    (
        "Administradores de cuenta",
        "Control total del tenant: empresas, centros, departamentos y configuración",
        TENANT_ADMIN_PERMS,
        True,
    ),
    (
        "Responsables",
        "Gestión de equipos: empleados, fichajes, vacaciones y turnos en su ámbito",
        MANAGER_PERMS,
        True,
    ),
    (
        "Empleados con panel",
        "Consulta de fichajes y vacaciones propias",
        frozenset(
            {
                "clock_ins.read",
                "leave.read",
                "leave.write",
                "documents.read",
                "legal.read",
            }
        ),
        True,
    ),
    (
        "Inspector de Trabajo",
        "Solo lectura en todos los módulos",
        INSPECTOR_PERMS,
        True,
    ),
]


def ensure_group_templates(session: Session) -> None:
    for i, (name, desc, perms, is_sys) in enumerate(DEFAULT_GROUP_TEMPLATES):
        existing = session.exec(
            select(GroupTemplate).where(GroupTemplate.name == name)
        ).first()
        if existing:
            existing.description = desc
            existing.permissions = sorted(perms)
            existing.is_system = is_sys
            existing.sort_order = i
            session.add(existing)
            continue
        session.add(
            GroupTemplate(
                name=name,
                description=desc,
                permissions=sorted(perms),
                is_system=is_sys,
                sort_order=i,
            )
        )


def clone_groups_for_tenant(session: Session, tenant_id: UUID) -> dict[str, UserGroup]:
    templates = session.exec(
        select(GroupTemplate).order_by(GroupTemplate.sort_order)
    ).all()
    result: dict[str, UserGroup] = {}
    for tpl in templates:
        g = UserGroup(
            tenant_id=tenant_id,
            name=tpl.name,
            description=tpl.description,
            is_system=tpl.is_system,
            permissions=list(tpl.permissions),
        )
        session.add(g)
        session.flush()
        result[tpl.name] = g
    return result


def seed_tenant_organization(
    session: Session,
    tenant: Tenant,
    company_name: str | None = None,
) -> tuple[Company, WorkCenter, Department]:
    """Crea empresa + centro + departamento por defecto para un tenant nuevo."""
    from app.services.billing_service import (
        copy_tenant_billing_to_company,
        ensure_default_subscription,
    )

    company = Company(
        tenant_id=tenant.id,
        name=company_name or tenant.name,
        tax_id=tenant.tax_id,
    )
    copy_tenant_billing_to_company(tenant, company)
    session.add(company)
    session.flush()

    wc = WorkCenter(
        company_id=company.id,
        name="Centro principal",
        code="CENTRO-01",
    )
    session.add(wc)
    session.flush()

    dept = Department(
        work_center_id=wc.id,
        name="General",
        code="GEN",
    )
    session.add(dept)
    session.flush()
    ensure_default_subscription(session, tenant, company)
    return company, wc, dept


def seed_company_organization(
    session: Session, company: Company
) -> tuple[WorkCenter, Department]:
    """Centro y departamento por defecto para una empresa nueva (sin crear otra empresa)."""
    existing = session.exec(
        select(WorkCenter).where(WorkCenter.company_id == company.id)
    ).first()
    if existing:
        dept = session.exec(
            select(Department).where(Department.work_center_id == existing.id)
        ).first()
        if dept:
            return existing, dept

    code = f"C-{str(company.id).replace('-', '')[:8].upper()}"
    wc = WorkCenter(
        company_id=company.id,
        name="Centro principal",
        code=code[:50],
    )
    session.add(wc)
    session.flush()
    dept = Department(work_center_id=wc.id, name="General", code="GEN")
    session.add(dept)
    session.flush()
    return wc, dept


def employee_ids_in_scope(
    session: Session,
    tenant_id: UUID,
    company_id: UUID | None = None,
    work_center_id: UUID | None = None,
    department_id: UUID | None = None,
) -> list[UUID]:
    from app.models.models import Employee

    company_ids = [c.id for c in session.exec(
        select(Company).where(Company.tenant_id == tenant_id)
    ).all()]
    if company_id:
        company_ids = [company_id] if company_id in company_ids else []

    wc_ids: list[UUID] | None = None
    if work_center_id:
        wc = session.get(WorkCenter, work_center_id)
        wc_ids = [work_center_id] if wc and wc.company_id in company_ids else []
    elif company_ids:
        wc_ids = list(
            session.exec(
                select(WorkCenter.id).where(
                    WorkCenter.company_id.in_(company_ids)  # type: ignore[attr-defined]
                )
            ).all()
        )

    dept_ids: list[UUID] | None = None
    if department_id:
        dept_ids = [department_id]
    elif wc_ids is not None:
        dept_ids = list(
            session.exec(
                select(Department.id).where(
                    Department.work_center_id.in_(wc_ids)  # type: ignore[attr-defined]
                )
            ).all()
        )

    stmt = select(Employee.id).where(Employee.company_id.in_(company_ids))  # type: ignore[attr-defined]
    if dept_ids is not None:
        stmt = stmt.where(Employee.department_id.in_(dept_ids))  # type: ignore[attr-defined]
    return list(session.exec(stmt).all())
