from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.models import Employee, LeaveRequest, LeaveStatus
from app.routers.crud_helpers import get_or_404
from app.schemas.crud import LeaveRequestCreate, LeaveRequestRead, LeaveRequestUpdate

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])


@router.get("", response_model=list[LeaveRequestRead])
def list_leave_requests(
    session: Session = Depends(get_session),
    employee_id: UUID | None = None,
    status: LeaveStatus | None = None,
    q: str | None = None,
    _: object = Depends(require_permission(Permission.READ, "leave")),
) -> list[LeaveRequest]:
    stmt = select(LeaveRequest).order_by(LeaveRequest.created_at.desc())  # type: ignore[attr-defined]
    if employee_id:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    rows = list(session.exec(stmt).all())
    if q and q.strip():
        term = q.lower()
        emp_map = {e.id: e for e in session.exec(select(Employee)).all()}
        rows = [
            r
            for r in rows
            if (emp := emp_map.get(r.employee_id))
            and (term in emp.full_name.lower() or term in emp.employee_code.lower())
        ]
    return rows


@router.get("/{request_id}", response_model=LeaveRequestRead)
def get_leave_request(
    request_id: UUID,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "leave")),
) -> LeaveRequest:
    return get_or_404(session, LeaveRequest, request_id)


@router.post("", response_model=LeaveRequestRead, status_code=201)
def create_leave_request(
    data: LeaveRequestCreate,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "leave")),
) -> LeaveRequest:
    if not session.get(Employee, data.employee_id):
        raise HTTPException(status_code=400, detail="Empleado no existe")
    row = LeaveRequest.model_validate(data)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{request_id}", response_model=LeaveRequestRead)
def update_leave_request(
    request_id: UUID,
    data: LeaveRequestUpdate,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "leave")),
) -> LeaveRequest:
    row = get_or_404(session, LeaveRequest, request_id)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("status") in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
        row.reviewed_at = datetime.utcnow()
    for key, value in payload.items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{request_id}", status_code=204)
def delete_leave_request(
    request_id: UUID,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "leave")),
) -> None:
    row = get_or_404(session, LeaveRequest, request_id)
    session.delete(row)
    session.commit()
