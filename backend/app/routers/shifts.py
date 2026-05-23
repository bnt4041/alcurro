from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.permissions import Permission, require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.models import Employee, ShiftAssignment, ShiftConfiguration, ShiftPatternType
from app.routers.crud_helpers import get_or_404
from app.routers.search_helpers import ilike_filter
from app.schemas.crud import (
    ShiftAssignmentCreate,
    ShiftAssignmentRead,
    ShiftAssignmentUpdate,
    ShiftConfigurationCreate,
    ShiftConfigurationRead,
    ShiftConfigurationUpdate,
)

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("/configurations", response_model=list[ShiftConfigurationRead])
def list_configurations(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    q: str | None = None,
    pattern_type: ShiftPatternType | None = None,
    _: object = Depends(require_permission(Permission.READ, "shifts")),
) -> list[ShiftConfiguration]:
    stmt = select(ShiftConfiguration).where(
        ShiftConfiguration.company_id == ctx.company.id
    )
    stmt = stmt.order_by(ShiftConfiguration.name)
    filt = ilike_filter(ShiftConfiguration.name, ShiftConfiguration.description, term=q)
    if filt is not None:
        stmt = stmt.where(filt)
    if pattern_type:
        stmt = stmt.where(ShiftConfiguration.pattern_type == pattern_type)
    return list(session.exec(stmt).all())


@router.post("/configurations", response_model=ShiftConfigurationRead, status_code=201)
def create_configuration(
    data: ShiftConfigurationCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "shifts")),
) -> ShiftConfiguration:
    row = ShiftConfiguration.model_validate(
        {**data.model_dump(), "company_id": ctx.company.id}
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/configurations/{config_id}", response_model=ShiftConfigurationRead)
def update_configuration(
    config_id: UUID,
    data: ShiftConfigurationUpdate,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "shifts")),
) -> ShiftConfiguration:
    row = get_or_404(session, ShiftConfiguration, config_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/configurations/{config_id}", status_code=204)
def delete_configuration(
    config_id: UUID,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "shifts")),
) -> None:
    row = get_or_404(session, ShiftConfiguration, config_id)
    session.delete(row)
    session.commit()


@router.get("/assignments", response_model=list[ShiftAssignmentRead])
def list_assignments(
    session: Session = Depends(get_session),
    employee_id: UUID | None = None,
    _: object = Depends(require_permission(Permission.READ, "shifts")),
) -> list[ShiftAssignment]:
    stmt = select(ShiftAssignment)
    if employee_id:
        stmt = stmt.where(ShiftAssignment.employee_id == employee_id)
    return list(session.exec(stmt).all())


@router.post("/assignments", response_model=ShiftAssignmentRead, status_code=201)
def create_assignment(
    data: ShiftAssignmentCreate,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "shifts")),
) -> ShiftAssignment:
    if not session.get(Employee, data.employee_id):
        raise HTTPException(status_code=400, detail="Empleado no existe")
    if not session.get(ShiftConfiguration, data.shift_configuration_id):
        raise HTTPException(status_code=400, detail="Configuración de turno no existe")
    row = ShiftAssignment.model_validate(data)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/assignments/{assignment_id}", response_model=ShiftAssignmentRead)
def update_assignment(
    assignment_id: UUID,
    data: ShiftAssignmentUpdate,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "shifts")),
) -> ShiftAssignment:
    row = get_or_404(session, ShiftAssignment, assignment_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: UUID,
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.ADMIN, "shifts")),
) -> None:
    row = get_or_404(session, ShiftAssignment, assignment_id)
    session.delete(row)
    session.commit()
