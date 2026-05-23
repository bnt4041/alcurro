"""Grupos predefinidos y asignación por tipo de usuario."""

from sqlmodel import Session, select

from app.core.permissions import (
    INSPECTOR_PERMS,
    MANAGER_PERMS,
    TENANT_ADMIN_PERMS,
)
from app.models.models import Employee, Role
from app.models.rbac import EmployeeGroup, UserGroup

EMPLOYEE_PANEL_PERMS = frozenset(
    {
        "clock_ins.read",
        "leave.read",
        "leave.write",
        "documents.read",
        "legal.read",
    }
)

SYSTEM_GROUPS: list[tuple[str, str, frozenset[str]]] = [
    (
        "Administradores de cuenta",
        "Acceso completo a la cuenta (administrador de tenant)",
        TENANT_ADMIN_PERMS,
    ),
    (
        "Responsables",
        "Supervisión de equipos: empleados, fichajes, vacaciones y turnos",
        MANAGER_PERMS,
    ),
    (
        "Inspector de Trabajo",
        "Solo lectura en todos los módulos",
        INSPECTOR_PERMS,
    ),
    (
        "Empleados con panel",
        "Consulta de fichajes y vacaciones propias",
        EMPLOYEE_PANEL_PERMS,
    ),
]


def ensure_system_groups(session: Session, tenant_id) -> dict[str, UserGroup]:
    existing = {
        g.name: g
        for g in session.exec(
            select(UserGroup).where(UserGroup.tenant_id == tenant_id)
        ).all()
    }
    result: dict[str, UserGroup] = {}
    for name, desc, perms in SYSTEM_GROUPS:
        if name in existing:
            g = existing[name]
            if not g.is_system:
                g.is_system = True
            g.permissions = sorted(perms)
            session.add(g)
            result[name] = g
            continue
        g = UserGroup(
            tenant_id=tenant_id,
            name=name,
            description=desc,
            is_system=True,
            permissions=sorted(perms),
        )
        session.add(g)
        session.flush()
        result[name] = g
    return result


def assign_role_default_group(
    session: Session, employee: Employee, tenant_id
) -> None:
    groups = ensure_system_groups(session, tenant_id)
    role = employee.role
    target_name: str | None = None
    if role in (Role.TENANT_ADMIN, Role.ADMIN):
        target_name = "Administradores de cuenta"
    elif role in (Role.MANAGER, Role.SUPERVISOR):
        target_name = "Responsables"
    elif role == Role.LABOR_INSPECTOR:
        target_name = "Inspector de Trabajo"
    elif role == Role.EMPLOYEE:
        target_name = "Empleados con panel"
    if not target_name:
        return
    group = groups[target_name]
    exists = session.exec(
        select(EmployeeGroup).where(
            EmployeeGroup.employee_id == employee.id,
            EmployeeGroup.group_id == group.id,
        )
    ).first()
    if not exists:
        session.add(EmployeeGroup(employee_id=employee.id, group_id=group.id))


def sync_tenant_groups(session: Session, tenant_id) -> None:
    from app.models.tenant import Company

    ensure_system_groups(session, tenant_id)
    companies = session.exec(
        select(Company).where(Company.tenant_id == tenant_id)
    ).all()
    company_ids = [c.id for c in companies]
    for emp in session.exec(
        select(Employee).where(Employee.company_id.in_(company_ids))  # type: ignore[attr-defined]
    ).all():
        assign_role_default_group(session, emp, tenant_id)
