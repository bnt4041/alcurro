from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.models import Employee, EmployeeLeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import EmployeeLeaveBalanceRead, EmployeeLeaveBalanceUpdate
from app.services.leave_service import get_remaining_days

router = APIRouter(tags=["leave-balances"])


def _enrich_balance(session: Session, bal: EmployeeLeaveBalance) -> EmployeeLeaveBalanceRead:
    lt = session.get(LeaveType, bal.leave_type_id)
    remaining = get_remaining_days(session, bal.employee_id, bal.leave_type_id, bal)
    used = float(bal.total_days) - remaining
    return EmployeeLeaveBalanceRead(
        id=bal.id,
        employee_id=bal.employee_id,
        leave_type_id=bal.leave_type_id,
        leave_type_name=lt.name if lt else None,
        total_days=bal.total_days,
        used_days=round(used, 2),
        remaining_days=round(remaining, 2),
        notes=bal.notes,
    )


@router.get("/employees/{employee_id}/leave-balances", response_model=list[EmployeeLeaveBalanceRead])
def list_employee_balances(
    employee_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "leave")),
) -> list[EmployeeLeaveBalanceRead]:
    balances = session.exec(
        select(EmployeeLeaveBalance).where(
            EmployeeLeaveBalance.employee_id == employee_id
        )
    ).all()
    # Also include types with has_own_balance that have no record yet
    types_with_own = session.exec(
        select(LeaveType).where(
            LeaveType.tenant_id == ctx.tenant.id,
            LeaveType.has_own_balance == True,  # noqa: E712
            LeaveType.is_active == True,  # noqa: E712
        )
    ).all()
    existing_type_ids = {b.leave_type_id for b in balances}
    result = [_enrich_balance(session, b) for b in balances]
    for lt in types_with_own:
        if lt.id not in existing_type_ids:
            result.append(EmployeeLeaveBalanceRead(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                employee_id=employee_id,
                leave_type_id=lt.id,
                leave_type_name=lt.name,
                total_days=0.0,
                used_days=0.0,
                remaining_days=0.0,
                notes=None,
            ))
    return result


@router.put("/employees/{employee_id}/leave-balances/{leave_type_id}", response_model=EmployeeLeaveBalanceRead)
def set_employee_balance(
    employee_id: UUID,
    leave_type_id: UUID,
    data: EmployeeLeaveBalanceUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> EmployeeLeaveBalanceRead:
    lt = get_or_404(session, LeaveType, leave_type_id)
    if lt.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Tipo de permiso no encontrado")

    bal = session.exec(
        select(EmployeeLeaveBalance).where(
            EmployeeLeaveBalance.employee_id == employee_id,
            EmployeeLeaveBalance.leave_type_id == leave_type_id,
        )
    ).first()
    if bal:
        bal.total_days = data.total_days
        if data.notes is not None:
            bal.notes = data.notes
    else:
        bal = EmployeeLeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            total_days=data.total_days,
            notes=data.notes,
        )
        session.add(bal)
    session.commit()
    session.refresh(bal)
    return _enrich_balance(session, bal)


@router.get("/leave-types/{leave_type_id}/balances", response_model=list[EmployeeLeaveBalanceRead])
def list_type_balances(
    leave_type_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> list[EmployeeLeaveBalanceRead]:
    lt = get_or_404(session, LeaveType, leave_type_id)
    if lt.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    balances = session.exec(
        select(EmployeeLeaveBalance).where(
            EmployeeLeaveBalance.leave_type_id == leave_type_id
        )
    ).all()
    return [_enrich_balance(session, b) for b in balances]
