"""Permisos granulares, grupos personalizables y compatibilidad coarse (read/write/admin)."""

from enum import StrEnum
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.models import Employee, Role
from app.models.rbac import EmployeeGroup, UserGroup


class Perm(StrEnum):
    EMPLOYEES_READ = "employees.read"
    EMPLOYEES_WRITE = "employees.write"
    EMPLOYEES_DELETE = "employees.delete"
    CLOCK_INS_READ = "clock_ins.read"
    CLOCK_INS_WRITE = "clock_ins.write"
    LEAVE_READ = "leave.read"
    LEAVE_WRITE = "leave.write"
    LEAVE_APPROVE = "leave.approve"
    SHIFTS_READ = "shifts.read"
    SHIFTS_WRITE = "shifts.write"
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_WRITE = "documents.write"
    SETTINGS_READ = "settings.read"
    SETTINGS_WRITE = "settings.write"
    TENANT_READ = "tenant.read"
    TENANT_WRITE = "tenant.write"
    TENANT_BILLING = "tenant.billing"
    COMPANIES_READ = "companies.read"
    COMPANIES_WRITE = "companies.write"
    WORK_CENTERS_READ = "work_centers.read"
    WORK_CENTERS_WRITE = "work_centers.write"
    DEPARTMENTS_READ = "departments.read"
    DEPARTMENTS_WRITE = "departments.write"
    GROUPS_READ = "groups.read"
    GROUPS_WRITE = "groups.write"
    GOWA_MANAGE = "gowa.manage"


class Permission(StrEnum):
    """Permisos coarse usados por routers existentes."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


PERM_LABELS: dict[str, str] = {
    Perm.EMPLOYEES_READ: "Ver empleados",
    Perm.EMPLOYEES_WRITE: "Editar empleados",
    Perm.EMPLOYEES_DELETE: "Eliminar empleados",
    Perm.CLOCK_INS_READ: "Ver fichajes",
    Perm.CLOCK_INS_WRITE: "Registrar fichajes",
    Perm.LEAVE_READ: "Ver vacaciones",
    Perm.LEAVE_WRITE: "Gestionar vacaciones",
    Perm.LEAVE_APPROVE: "Aprobar vacaciones",
    Perm.SHIFTS_READ: "Ver turnos",
    Perm.SHIFTS_WRITE: "Gestionar turnos",
    Perm.DOCUMENTS_READ: "Ver documentos",
    Perm.DOCUMENTS_WRITE: "Gestionar documentos",
    Perm.SETTINGS_READ: "Ver configuración",
    Perm.SETTINGS_WRITE: "Editar configuración",
    Perm.TENANT_READ: "Ver cuenta",
    Perm.TENANT_WRITE: "Editar cuenta y branding",
    Perm.TENANT_BILLING: "Datos de facturación",
    Perm.COMPANIES_READ: "Ver empresas",
    Perm.COMPANIES_WRITE: "Gestionar empresas",
    Perm.WORK_CENTERS_READ: "Ver centros de trabajo",
    Perm.WORK_CENTERS_WRITE: "Gestionar centros de trabajo",
    Perm.DEPARTMENTS_READ: "Ver departamentos",
    Perm.DEPARTMENTS_WRITE: "Gestionar departamentos",
    Perm.GROUPS_READ: "Ver grupos",
    Perm.GROUPS_WRITE: "Gestionar grupos y permisos",
    Perm.GOWA_MANAGE: "WhatsApp (goWA)",
}

ALL_PERMS: frozenset[str] = frozenset(Perm)

MODULE_PERMS: dict[str, dict[Permission, frozenset[str]]] = {
    "employees": {
        Permission.READ: frozenset({Perm.EMPLOYEES_READ}),
        Permission.WRITE: frozenset({Perm.EMPLOYEES_WRITE}),
        Permission.ADMIN: frozenset({Perm.EMPLOYEES_DELETE}),
    },
    "clock_ins": {
        Permission.READ: frozenset({Perm.CLOCK_INS_READ}),
        Permission.WRITE: frozenset({Perm.CLOCK_INS_WRITE}),
        Permission.ADMIN: frozenset({Perm.CLOCK_INS_WRITE}),
    },
    "leave": {
        Permission.READ: frozenset({Perm.LEAVE_READ}),
        Permission.WRITE: frozenset({Perm.LEAVE_WRITE, Perm.LEAVE_APPROVE}),
        Permission.ADMIN: frozenset({Perm.LEAVE_APPROVE, Perm.LEAVE_WRITE}),
    },
    "shifts": {
        Permission.READ: frozenset({Perm.SHIFTS_READ}),
        Permission.WRITE: frozenset({Perm.SHIFTS_WRITE}),
        Permission.ADMIN: frozenset({Perm.SHIFTS_WRITE}),
    },
    "documents": {
        Permission.READ: frozenset({Perm.DOCUMENTS_READ}),
        Permission.WRITE: frozenset({Perm.DOCUMENTS_WRITE}),
        Permission.ADMIN: frozenset({Perm.DOCUMENTS_WRITE}),
    },
    "settings": {
        Permission.READ: frozenset({Perm.SETTINGS_READ}),
        Permission.WRITE: frozenset({Perm.SETTINGS_WRITE}),
        Permission.ADMIN: frozenset({Perm.SETTINGS_WRITE}),
    },
    "tenant": {
        Permission.READ: frozenset({Perm.TENANT_READ}),
        Permission.WRITE: frozenset({Perm.TENANT_WRITE, Perm.TENANT_BILLING}),
        Permission.ADMIN: frozenset(
            {Perm.TENANT_WRITE, Perm.TENANT_BILLING, Perm.GOWA_MANAGE}
        ),
    },
    "companies": {
        Permission.READ: frozenset({Perm.COMPANIES_READ}),
        Permission.WRITE: frozenset({Perm.COMPANIES_WRITE}),
        Permission.ADMIN: frozenset({Perm.COMPANIES_WRITE}),
    },
    "work_centers": {
        Permission.READ: frozenset({Perm.WORK_CENTERS_READ}),
        Permission.WRITE: frozenset({Perm.WORK_CENTERS_WRITE}),
        Permission.ADMIN: frozenset({Perm.WORK_CENTERS_WRITE}),
    },
    "departments": {
        Permission.READ: frozenset({Perm.DEPARTMENTS_READ}),
        Permission.WRITE: frozenset({Perm.DEPARTMENTS_WRITE}),
        Permission.ADMIN: frozenset({Perm.DEPARTMENTS_WRITE}),
    },
    "groups": {
        Permission.READ: frozenset({Perm.GROUPS_READ}),
        Permission.WRITE: frozenset({Perm.GROUPS_WRITE}),
        Permission.ADMIN: frozenset({Perm.GROUPS_WRITE}),
    },
}

TENANT_ADMIN_PERMS: frozenset[str] = ALL_PERMS

MANAGER_PERMS: frozenset[str] = frozenset(
    {
        Perm.EMPLOYEES_READ,
        Perm.EMPLOYEES_WRITE,
        Perm.CLOCK_INS_READ,
        Perm.CLOCK_INS_WRITE,
        Perm.LEAVE_READ,
        Perm.LEAVE_WRITE,
        Perm.LEAVE_APPROVE,
        Perm.SHIFTS_READ,
        Perm.SHIFTS_WRITE,
        Perm.DOCUMENTS_READ,
        Perm.DOCUMENTS_WRITE,
        Perm.TENANT_READ,
        Perm.COMPANIES_READ,
        Perm.WORK_CENTERS_READ,
        Perm.DEPARTMENTS_READ,
        Perm.GROUPS_READ,
    }
)

INSPECTOR_PERMS: frozenset[str] = frozenset(
    p for p in Perm if p.endswith(".read") or p == Perm.LEAVE_APPROVE
)

ROLE_DEFAULT_PERMS: dict[Role, frozenset[str]] = {
    Role.TENANT_ADMIN: TENANT_ADMIN_PERMS,
    Role.ADMIN: TENANT_ADMIN_PERMS,
    Role.MANAGER: MANAGER_PERMS,
    Role.SUPERVISOR: MANAGER_PERMS,
    Role.LABOR_INSPECTOR: INSPECTOR_PERMS,
    Role.EMPLOYEE: frozenset(),
}


def normalize_role(role: Role) -> Role:
    if role == Role.ADMIN:
        return Role.TENANT_ADMIN
    if role == Role.SUPERVISOR:
        return Role.MANAGER
    return role


def get_employee_permissions(
    session: Session, employee: Employee, tenant_id: UUID
) -> frozenset[str]:
    group_ids = session.exec(
        select(EmployeeGroup.group_id).where(EmployeeGroup.employee_id == employee.id)
    ).all()
    if group_ids:
        perms: set[str] = set()
        for gid in group_ids:
            group = session.get(UserGroup, gid)
            if group and group.tenant_id == tenant_id:
                perms.update(group.permissions)
        if perms:
            return frozenset(perms)
    return ROLE_DEFAULT_PERMS.get(normalize_role(employee.role), frozenset())


def has_perm(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    perm: str,
) -> bool:
    return perm in get_employee_permissions(session, employee, tenant_id)


def has_coarse(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    coarse: Permission,
    module: str,
) -> bool:
    effective = get_employee_permissions(session, employee, tenant_id)
    required = MODULE_PERMS.get(module, {}).get(coarse, frozenset())
    return bool(effective & required)


def require_permission(coarse: Permission, module: str):
    def checker(
        user: Employee = Depends(get_current_user),
        ctx: TenantContext = Depends(get_tenant_context),
        session: Session = Depends(get_session),
    ) -> Employee:
        if not has_coarse(session, user, ctx.tenant.id, coarse, module):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return user

    return checker


def require_perm(perm: str):
    def checker(
        user: Employee = Depends(get_current_user),
        ctx: TenantContext = Depends(get_tenant_context),
        session: Session = Depends(get_session),
    ) -> Employee:
        if not has_perm(session, user, ctx.tenant.id, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return user

    return checker
