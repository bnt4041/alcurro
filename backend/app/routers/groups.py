from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.core.permissions import (
    ALL_PERMS,
    PERM_LABELS,
    Permission,
    require_permission,
)
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.models import Employee
from app.models.rbac import EmployeeGroup, UserGroup
from app.routers.crud_helpers import get_or_404
from app.schemas.rbac import (
    GroupCreate,
    GroupMemberUpdate,
    GroupRead,
    GroupUpdate,
    PermCatalogItem,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def _group_read(session: Session, group: UserGroup) -> GroupRead:
    count = session.exec(
        select(func.count())
        .select_from(EmployeeGroup)
        .where(EmployeeGroup.group_id == group.id)
    ).one()
    return GroupRead(
        id=group.id,
        tenant_id=group.tenant_id,
        name=group.name,
        description=group.description,
        is_system=group.is_system,
        permissions=group.permissions,
        member_count=count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.get("/catalog", response_model=list[PermCatalogItem])
def permission_catalog(
    _: object = Depends(require_permission(Permission.READ, "groups")),
) -> list[PermCatalogItem]:
    return [
        PermCatalogItem(key=p, label=PERM_LABELS.get(p, p))
        for p in sorted(ALL_PERMS)
    ]


@router.get("", response_model=list[GroupRead])
def list_groups(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "groups")),
) -> list[GroupRead]:
    groups = session.exec(
        select(UserGroup)
        .where(UserGroup.tenant_id == ctx.tenant.id)
        .order_by(UserGroup.name)
    ).all()
    return [_group_read(session, g) for g in groups]


@router.post("", response_model=GroupRead, status_code=201)
def create_group(
    data: GroupCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "groups")),
) -> GroupRead:
    invalid = set(data.permissions) - ALL_PERMS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Permisos inválidos: {invalid}")
    if session.exec(
        select(UserGroup).where(
            UserGroup.tenant_id == ctx.tenant.id,
            UserGroup.name == data.name,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Ya existe un grupo con ese nombre")
    row = UserGroup(
        tenant_id=ctx.tenant.id,
        name=data.name,
        description=data.description,
        permissions=sorted(set(data.permissions)),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _group_read(session, row)


@router.patch("/{group_id}", response_model=GroupRead)
def update_group(
    group_id: UUID,
    data: GroupUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "groups")),
) -> GroupRead:
    row = get_or_404(session, UserGroup, group_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if data.permissions is not None:
        invalid = set(data.permissions) - ALL_PERMS
        if invalid:
            raise HTTPException(status_code=400, detail=f"Permisos inválidos: {invalid}")
        row.permissions = sorted(set(data.permissions))
    if data.name is not None:
        row.name = data.name
    if data.description is not None:
        row.description = data.description
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return _group_read(session, row)


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "groups")),
) -> None:
    row = get_or_404(session, UserGroup, group_id)
    if row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if row.is_system:
        raise HTTPException(status_code=400, detail="No se puede eliminar un grupo del sistema")
    for link in session.exec(
        select(EmployeeGroup).where(EmployeeGroup.group_id == row.id)
    ).all():
        session.delete(link)
    session.delete(row)
    session.commit()


@router.get("/employees/{employee_id}/groups", response_model=list[UUID])
def get_employee_groups(
    employee_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "groups")),
) -> list[UUID]:
    from app.models.tenant import Company

    emp = get_or_404(session, Employee, employee_id)
    company = session.get(Company, emp.company_id)
    if not company or company.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return list(
        session.exec(
            select(EmployeeGroup.group_id).where(EmployeeGroup.employee_id == emp.id)
        ).all()
    )


@router.put("/employees/{employee_id}/groups", response_model=list[UUID])
def set_employee_groups(
    employee_id: UUID,
    data: GroupMemberUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "groups")),
) -> list[UUID]:
    from app.models.tenant import Company

    emp = get_or_404(session, Employee, employee_id)
    company = session.get(Company, emp.company_id)
    if not company or company.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    valid_groups = session.exec(
        select(UserGroup).where(
            UserGroup.tenant_id == ctx.tenant.id,
            UserGroup.id.in_(data.group_ids),  # type: ignore[attr-defined]
        )
    ).all()
    if len(valid_groups) != len(set(data.group_ids)):
        raise HTTPException(status_code=400, detail="Grupos no válidos")
    for link in session.exec(
        select(EmployeeGroup).where(EmployeeGroup.employee_id == emp.id)
    ).all():
        session.delete(link)
    for gid in data.group_ids:
        session.add(EmployeeGroup(employee_id=emp.id, group_id=gid))
    session.commit()
    return data.group_ids
