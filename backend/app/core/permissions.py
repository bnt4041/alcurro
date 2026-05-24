"""Permisos granulares, grupos personalizables y compatibilidad coarse (read/write/admin)."""

from enum import StrEnum
from typing import Literal
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
    EMPLOYEES_READ_OWN = "employees.read_own"
    EMPLOYEES_WRITE = "employees.write"
    EMPLOYEES_CREATE_OWN = "employees.create_own"
    EMPLOYEES_UPDATE_OWN = "employees.update_own"
    EMPLOYEES_DELETE = "employees.delete"
    CLOCK_INS_READ = "clock_ins.read"
    CLOCK_INS_READ_OWN = "clock_ins.read_own"
    CLOCK_INS_WRITE = "clock_ins.write"
    CLOCK_INS_CREATE_OWN = "clock_ins.create_own"
    CLOCK_INS_UPDATE_OWN = "clock_ins.update_own"
    BREAKS_READ = "breaks.read"
    BREAKS_READ_OWN = "breaks.read_own"
    BREAKS_WRITE = "breaks.write"
    BREAKS_CREATE_OWN = "breaks.create_own"
    BREAKS_UPDATE_OWN = "breaks.update_own"
    LEAVE_READ = "leave.read"
    LEAVE_READ_OWN = "leave.read_own"
    LEAVE_WRITE = "leave.write"
    LEAVE_CREATE_OWN = "leave.create_own"
    LEAVE_UPDATE_OWN = "leave.update_own"
    LEAVE_APPROVE = "leave.approve"
    SHIFTS_READ = "shifts.read"
    SHIFTS_READ_OWN = "shifts.read_own"
    SHIFTS_WRITE = "shifts.write"
    SHIFTS_CREATE_OWN = "shifts.create_own"
    SHIFTS_UPDATE_OWN = "shifts.update_own"
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_READ_OWN = "documents.read_own"
    DOCUMENTS_WRITE = "documents.write"
    DOCUMENTS_CREATE_OWN = "documents.create_own"
    DOCUMENTS_UPDATE_OWN = "documents.update_own"
    SIGNATURES_READ = "signatures.read"
    SIGNATURES_READ_OWN = "signatures.read_own"
    SIGNATURES_WRITE = "signatures.write"
    SIGNATURES_CREATE_OWN = "signatures.create_own"
    SIGNATURES_UPDATE_OWN = "signatures.update_own"
    LEGAL_READ = "legal.read"
    LEGAL_READ_OWN = "legal.read_own"
    LEGAL_WRITE = "legal.write"
    LEGAL_CREATE_OWN = "legal.create_own"
    LEGAL_UPDATE_OWN = "legal.update_own"
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


WriteAction = Literal["create", "update", "any"]


def read_own_perm(module: str) -> str:
    return f"{module}.read_own"


def create_own_perm(module: str) -> str:
    return f"{module}.create_own"


def update_own_perm(module: str) -> str:
    return f"{module}.update_own"


# Módulos con datos por empleado (alcance propio)
OWN_SCOPE_MODULES: frozenset[str] = frozenset(
    {
        "employees",
        "clock_ins",
        "breaks",
        "leave",
        "shifts",
        "documents",
        "signatures",
        "legal",
    }
)


PERM_LABELS: dict[str, str] = {
    Perm.EMPLOYEES_READ: "Ver todos los empleados",
    Perm.EMPLOYEES_READ_OWN: "Ver sólo los del usuario",
    Perm.EMPLOYEES_WRITE: "Crear y modificar todos",
    Perm.EMPLOYEES_CREATE_OWN: "Crear sólo los del usuario",
    Perm.EMPLOYEES_UPDATE_OWN: "Modificar sólo los del usuario",
    Perm.EMPLOYEES_DELETE: "Eliminar empleados",
    Perm.CLOCK_INS_READ: "Ver todos los fichajes",
    Perm.CLOCK_INS_READ_OWN: "Ver sólo los del usuario",
    Perm.CLOCK_INS_WRITE: "Crear y modificar todos",
    Perm.CLOCK_INS_CREATE_OWN: "Crear sólo los del usuario",
    Perm.CLOCK_INS_UPDATE_OWN: "Modificar sólo los del usuario",
    Perm.BREAKS_READ: "Ver todas las paradas",
    Perm.BREAKS_READ_OWN: "Ver sólo las del usuario",
    Perm.BREAKS_WRITE: "Crear y modificar todas",
    Perm.BREAKS_CREATE_OWN: "Crear sólo las del usuario",
    Perm.BREAKS_UPDATE_OWN: "Modificar sólo las del usuario",
    Perm.LEAVE_READ: "Ver todas las vacaciones",
    Perm.LEAVE_READ_OWN: "Ver sólo las del usuario",
    Perm.LEAVE_WRITE: "Gestionar todas las vacaciones",
    Perm.LEAVE_CREATE_OWN: "Crear sólo las del usuario",
    Perm.LEAVE_UPDATE_OWN: "Modificar sólo las del usuario",
    Perm.LEAVE_APPROVE: "Aprobar vacaciones",
    Perm.SHIFTS_READ: "Ver todos los turnos",
    Perm.SHIFTS_READ_OWN: "Ver sólo los del usuario",
    Perm.SHIFTS_WRITE: "Crear y modificar todos",
    Perm.SHIFTS_CREATE_OWN: "Crear sólo los del usuario",
    Perm.SHIFTS_UPDATE_OWN: "Modificar sólo los del usuario",
    Perm.DOCUMENTS_READ: "Ver todos los documentos",
    Perm.DOCUMENTS_READ_OWN: "Ver sólo los del usuario",
    Perm.DOCUMENTS_WRITE: "Crear y modificar todos",
    Perm.DOCUMENTS_CREATE_OWN: "Crear sólo los del usuario",
    Perm.DOCUMENTS_UPDATE_OWN: "Modificar sólo los del usuario",
    Perm.SIGNATURES_READ: "Ver todas las firmas",
    Perm.SIGNATURES_READ_OWN: "Ver sólo las del usuario",
    Perm.SIGNATURES_WRITE: "Crear y modificar todas",
    Perm.SIGNATURES_CREATE_OWN: "Crear sólo las del usuario",
    Perm.SIGNATURES_UPDATE_OWN: "Modificar sólo las del usuario",
    Perm.LEGAL_READ: "Ver textos legales (todos)",
    Perm.LEGAL_READ_OWN: "Ver sólo cumplimiento del usuario",
    Perm.LEGAL_WRITE: "Gestionar textos legales",
    Perm.LEGAL_CREATE_OWN: "Crear sólo los del usuario",
    Perm.LEGAL_UPDATE_OWN: "Modificar sólo los del usuario",
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

# Catálogo agrupado por apartado del panel (orden de navegación)
PERM_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Empleados",
        [
            Perm.EMPLOYEES_READ,
            Perm.EMPLOYEES_READ_OWN,
            Perm.EMPLOYEES_WRITE,
            Perm.EMPLOYEES_CREATE_OWN,
            Perm.EMPLOYEES_UPDATE_OWN,
            Perm.EMPLOYEES_DELETE,
        ],
    ),
    (
        "Fichajes",
        [
            Perm.CLOCK_INS_READ,
            Perm.CLOCK_INS_READ_OWN,
            Perm.CLOCK_INS_WRITE,
            Perm.CLOCK_INS_CREATE_OWN,
            Perm.CLOCK_INS_UPDATE_OWN,
        ],
    ),
    (
        "Paradas",
        [
            Perm.BREAKS_READ,
            Perm.BREAKS_READ_OWN,
            Perm.BREAKS_WRITE,
            Perm.BREAKS_CREATE_OWN,
            Perm.BREAKS_UPDATE_OWN,
        ],
    ),
    (
        "Vacaciones",
        [
            Perm.LEAVE_READ,
            Perm.LEAVE_READ_OWN,
            Perm.LEAVE_WRITE,
            Perm.LEAVE_CREATE_OWN,
            Perm.LEAVE_UPDATE_OWN,
            Perm.LEAVE_APPROVE,
        ],
    ),
    (
        "Turnos",
        [
            Perm.SHIFTS_READ,
            Perm.SHIFTS_READ_OWN,
            Perm.SHIFTS_WRITE,
            Perm.SHIFTS_CREATE_OWN,
            Perm.SHIFTS_UPDATE_OWN,
        ],
    ),
    (
        "Documentos",
        [
            Perm.DOCUMENTS_READ,
            Perm.DOCUMENTS_READ_OWN,
            Perm.DOCUMENTS_WRITE,
            Perm.DOCUMENTS_CREATE_OWN,
            Perm.DOCUMENTS_UPDATE_OWN,
        ],
    ),
    (
        "Firmas electrónicas",
        [
            Perm.SIGNATURES_READ,
            Perm.SIGNATURES_READ_OWN,
            Perm.SIGNATURES_WRITE,
            Perm.SIGNATURES_CREATE_OWN,
            Perm.SIGNATURES_UPDATE_OWN,
        ],
    ),
    (
        "Textos legales",
        [
            Perm.LEGAL_READ,
            Perm.LEGAL_READ_OWN,
            Perm.LEGAL_WRITE,
            Perm.LEGAL_CREATE_OWN,
            Perm.LEGAL_UPDATE_OWN,
        ],
    ),
    (
        "Organización",
        [
            Perm.COMPANIES_READ,
            Perm.COMPANIES_WRITE,
            Perm.WORK_CENTERS_READ,
            Perm.WORK_CENTERS_WRITE,
            Perm.DEPARTMENTS_READ,
            Perm.DEPARTMENTS_WRITE,
        ],
    ),
    (
        "Grupos y permisos",
        [Perm.GROUPS_READ, Perm.GROUPS_WRITE],
    ),
    (
        "Cuenta",
        [
            Perm.TENANT_READ,
            Perm.TENANT_WRITE,
            Perm.TENANT_BILLING,
            Perm.GOWA_MANAGE,
        ],
    ),
    (
        "Configuración sistema",
        [Perm.SETTINGS_READ, Perm.SETTINGS_WRITE],
    ),
]

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
    "breaks": {
        Permission.READ: frozenset({Perm.BREAKS_READ}),
        Permission.WRITE: frozenset({Perm.BREAKS_WRITE}),
        Permission.ADMIN: frozenset({Perm.BREAKS_WRITE}),
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
    "signatures": {
        Permission.READ: frozenset({Perm.SIGNATURES_READ, Perm.DOCUMENTS_READ}),
        Permission.WRITE: frozenset({Perm.SIGNATURES_WRITE, Perm.DOCUMENTS_WRITE}),
        Permission.ADMIN: frozenset({Perm.SIGNATURES_WRITE, Perm.DOCUMENTS_WRITE}),
    },
    "legal": {
        Permission.READ: frozenset({Perm.LEGAL_READ}),
        Permission.WRITE: frozenset({Perm.LEGAL_WRITE}),
        Permission.ADMIN: frozenset({Perm.LEGAL_WRITE}),
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
        Perm.BREAKS_READ,
        Perm.BREAKS_WRITE,
        Perm.LEAVE_READ,
        Perm.LEAVE_WRITE,
        Perm.LEAVE_APPROVE,
        Perm.SHIFTS_READ,
        Perm.SHIFTS_WRITE,
        Perm.LEGAL_READ,
        Perm.LEGAL_WRITE,
        Perm.DOCUMENTS_READ,
        Perm.DOCUMENTS_WRITE,
        Perm.SIGNATURES_READ,
        Perm.SIGNATURES_WRITE,
        Perm.TENANT_READ,
        Perm.COMPANIES_READ,
        Perm.WORK_CENTERS_READ,
        Perm.DEPARTMENTS_READ,
        Perm.GROUPS_READ,
    }
)

INSPECTOR_PERMS: frozenset[str] = frozenset(
    p
    for p in Perm
    if p.endswith(".read") or p.endswith(".read_own") or p == Perm.LEAVE_APPROVE
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


def has_full_write(
    session: Session, employee: Employee, tenant_id: UUID, module: str
) -> bool:
    effective = get_employee_permissions(session, employee, tenant_id)
    required = MODULE_PERMS.get(module, {}).get(Permission.WRITE, frozenset())
    return bool(effective & required)


def can_write_action(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    module: str,
    action: WriteAction,
) -> bool:
    if has_full_write(session, employee, tenant_id, module):
        return True
    perms = get_employee_permissions(session, employee, tenant_id)
    if action in ("create", "any") and create_own_perm(module) in perms:
        return True
    if action in ("update", "any") and update_own_perm(module) in perms:
        return True
    return False


def has_coarse(
    session: Session,
    employee: Employee,
    tenant_id: UUID,
    coarse: Permission,
    module: str,
) -> bool:
    effective = get_employee_permissions(session, employee, tenant_id)
    required = MODULE_PERMS.get(module, {}).get(coarse, frozenset())
    if effective & required:
        return True
    if coarse == Permission.READ:
        if read_own_perm(module) in effective:
            return True
        if module == "signatures" and Perm.DOCUMENTS_READ_OWN in effective:
            return True
    if coarse == Permission.WRITE:
        if create_own_perm(module) in effective or update_own_perm(module) in effective:
            return True
        if module == "signatures" and (
            Perm.DOCUMENTS_CREATE_OWN in effective or Perm.DOCUMENTS_UPDATE_OWN in effective
        ):
            return True
    return False


def require_write(module: str, action: WriteAction = "any"):
    def checker(
        user: Employee = Depends(get_current_user),
        ctx: TenantContext = Depends(get_tenant_context),
        session: Session = Depends(get_session),
    ) -> Employee:
        if not can_write_action(session, user, ctx.tenant.id, module, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return user

    return checker


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
