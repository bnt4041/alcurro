"""Alcance de lectura y escritura: organización completa o solo el propio usuario."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.org_context import OrgContext
from app.core.permissions import (
    Permission,
    WriteAction,
    can_write_action,
    create_own_perm,
    get_employee_permissions,
    has_coarse,
    has_full_write,
    read_own_perm,
    update_own_perm,
)
from app.models.models import Employee
from app.models.tenant import Company
from app.services.org_service import employee_ids_in_scope


def read_scope_employee_ids(
    session: Session,
    user: Employee,
    tenant_id: UUID,
    module: str,
    *,
    company_id: UUID,
    work_center_id: UUID | None = None,
    department_id: UUID | None = None,
) -> list[UUID]:
    """IDs de empleados visibles en listados del módulo (vacío = sin acceso)."""
    if not can_read_module(session, user, tenant_id, module):
        return []
    if has_coarse(session, user, tenant_id, Permission.READ, module):
        return employee_ids_in_scope(
            session,
            tenant_id,
            company_id=company_id,
            work_center_id=work_center_id,
            department_id=department_id,
        )
    if read_own_perm(module) in get_employee_permissions(session, user, tenant_id):
        return [user.id]
    return []


def write_scope_employee_ids(
    session: Session,
    user: Employee,
    tenant_id: UUID,
    module: str,
    *,
    company_id: UUID,
    work_center_id: UUID | None = None,
    department_id: UUID | None = None,
) -> list[UUID]:
    """IDs sobre los que puede crear/modificar con permiso completo de escritura."""
    if has_full_write(session, user, tenant_id, module):
        return employee_ids_in_scope(
            session,
            tenant_id,
            company_id=company_id,
            work_center_id=work_center_id,
            department_id=department_id,
        )
    return []


def can_read_module(session: Session, user: Employee, tenant_id: UUID, module: str) -> bool:
    return has_coarse(session, user, tenant_id, Permission.READ, module)


def is_read_own_only(
    session: Session, user: Employee, tenant_id: UUID, module: str
) -> bool:
    if has_coarse(session, user, tenant_id, Permission.READ, module):
        return False
    perms = get_employee_permissions(session, user, tenant_id)
    if read_own_perm(module) in perms:
        return True
    if module == "signatures" and "documents.read_own" in perms:
        return True
    return False


def is_write_own_only(
    session: Session,
    user: Employee,
    tenant_id: UUID,
    module: str,
    action: WriteAction,
) -> bool:
    if has_full_write(session, user, tenant_id, module):
        return False
    perms = get_employee_permissions(session, user, tenant_id)
    if action in ("create", "any") and create_own_perm(module) in perms:
        return True
    if action in ("update", "any") and update_own_perm(module) in perms:
        return True
    if module == "signatures":
        if action in ("create", "any") and "documents.create_own" in perms:
            return True
        if action in ("update", "any") and "documents.update_own" in perms:
            return True
    return False


def assert_employee_target(
    session: Session,
    user: Employee,
    ctx: OrgContext,
    module: str,
    employee_id: UUID,
    action: WriteAction,
) -> None:
    """Comprueba que el usuario puede crear/modificar datos de ese empleado."""
    if not can_write_action(session, user, ctx.tenant.id, module, action):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
    if is_write_own_only(session, user, ctx.tenant.id, module, action):
        if employee_id != user.id:
            raise HTTPException(
                status_code=400,
                detail="Solo puedes crear o modificar tus propios registros",
            )
        return
    allowed = write_scope_employee_ids(
        session,
        user,
        ctx.tenant.id,
        module,
        company_id=ctx.company.id,
        work_center_id=ctx.work_center.id if ctx.work_center else None,
        department_id=ctx.department.id if ctx.department else None,
    )
    if employee_id not in allowed:
        raise HTTPException(status_code=400, detail="Empleado no válido en el ámbito")


def resolve_write_employee_id(
    session: Session,
    user: Employee,
    ctx: OrgContext,
    module: str,
    employee_id: UUID | None,
    action: WriteAction,
) -> UUID:
    """Devuelve el employee_id efectivo para altas (por defecto el propio usuario)."""
    if employee_id is None:
        if not can_write_action(session, user, ctx.tenant.id, module, action):
            raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
        if is_write_own_only(session, user, ctx.tenant.id, module, action):
            return user.id
        raise HTTPException(status_code=400, detail="Indica el empleado")
    assert_employee_target(session, user, ctx, module, employee_id, action)
    return employee_id


def tenant_company_ids(session: Session, tenant_id: UUID) -> list[UUID]:
    return list(
        session.exec(select(Company.id).where(Company.tenant_id == tenant_id)).all()
    )
