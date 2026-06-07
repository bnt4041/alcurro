from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.models import Employee, LeaveType
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import LeaveTypeCreate, LeaveTypeRead, LeaveTypeUpdate

router = APIRouter(prefix="/leave-types", tags=["leave-types"])


def _tenant_id(ctx: OrgContext) -> UUID:
    return ctx.tenant.id


@router.get("", response_model=list[LeaveTypeRead])
def list_leave_types(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "leave")),
) -> list[LeaveType]:
    return list(
        session.exec(
            select(LeaveType)
            .where(LeaveType.tenant_id == _tenant_id(ctx), LeaveType.is_active == True)  # noqa: E712
            .order_by(LeaveType.sort_order, LeaveType.name)  # type: ignore[arg-type]
        ).all()
    )


@router.post("", response_model=LeaveTypeRead, status_code=201)
def create_leave_type(
    data: LeaveTypeCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> LeaveType:
    lt = LeaveType(
        tenant_id=_tenant_id(ctx),
        name=data.name,
        deducts_balance=data.deducts_balance,
        is_default=False,
    )
    session.add(lt)
    session.commit()
    session.refresh(lt)
    return lt


@router.patch("/{leave_type_id}", response_model=LeaveTypeRead)
def update_leave_type(
    leave_type_id: UUID,
    data: LeaveTypeUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> LeaveType:
    lt = get_or_404(session, LeaveType, leave_type_id)
    if lt.tenant_id != _tenant_id(ctx):
        raise HTTPException(status_code=404, detail="Tipo de permiso no encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(lt, key, value)
    session.add(lt)
    session.commit()
    session.refresh(lt)
    return lt


@router.delete("/{leave_type_id}", status_code=204)
def delete_leave_type(
    leave_type_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> None:
    lt = get_or_404(session, LeaveType, leave_type_id)
    if lt.tenant_id != _tenant_id(ctx):
        raise HTTPException(status_code=404, detail="Tipo de permiso no encontrado")
    if lt.is_default:
        raise HTTPException(status_code=400, detail="No se pueden eliminar los tipos predeterminados")
    session.delete(lt)
    session.commit()
