"""Resolve natural-key references (code, phone, email) to internal UUIDs.

API consumers rarely know internal UUIDs. These helpers let them pass
employee_code, phone, or email instead of employee_id, and leave_type_name
instead of leave_type_id, etc.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.models import Employee, LeaveType
from app.models.organization import Department


def resolve_employee_ref(
    session: Session,
    company_id: UUID,
    employee_id: UUID | None = None,
    employee_ref: str | None = None,
) -> UUID:
    """Return employee UUID from either a direct UUID or a natural ref.

    employee_ref accepts: UUID string, employee_code, phone, or email.
    Raises 422 if neither argument is provided, 404 if ref is unresolvable.
    """
    if employee_id and not employee_ref:
        return employee_id

    if not employee_ref:
        raise HTTPException(
            status_code=422,
            detail="Se requiere employee_id o employee_ref",
        )

    # Try as raw UUID
    try:
        return UUID(employee_ref)
    except ValueError:
        pass

    # Try employee_code (exact, case-insensitive)
    emp = session.exec(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.employee_code.ilike(employee_ref),  # type: ignore[attr-defined]
        )
    ).first()
    if emp:
        return emp.id

    # Try email
    emp = session.exec(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.email.ilike(employee_ref),  # type: ignore[attr-defined]
        )
    ).first()
    if emp:
        return emp.id

    # Try phone (exact match — phones are normalized on creation)
    emp = session.exec(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.phone == employee_ref,
        )
    ).first()
    if emp:
        return emp.id

    raise HTTPException(
        status_code=404,
        detail=f"No se encontró ningún empleado con referencia '{employee_ref}'",
    )


def resolve_leave_type_ref(
    session: Session,
    tenant_id: UUID,
    leave_type_id: UUID | None = None,
    leave_type_name: str | None = None,
) -> UUID | None:
    """Return leave-type UUID from direct UUID or name (case-insensitive)."""
    if leave_type_id:
        return leave_type_id
    if not leave_type_name:
        return None

    lt = session.exec(
        select(LeaveType).where(
            LeaveType.tenant_id == tenant_id,
            LeaveType.name.ilike(leave_type_name),  # type: ignore[attr-defined]
        )
    ).first()
    if not lt:
        raise HTTPException(
            status_code=404,
            detail=f"Tipo de permiso no encontrado: '{leave_type_name}'",
        )
    return lt.id


def resolve_department_ref(
    session: Session,
    company_id: UUID,
    department_id: UUID | None = None,
    department_name: str | None = None,
) -> UUID | None:
    """Return department UUID from direct UUID or name (case-insensitive)."""
    if department_id:
        return department_id
    if not department_name:
        return None

    dept = session.exec(
        select(Department).where(
            Department.company_id == company_id,
            Department.name.ilike(department_name),  # type: ignore[attr-defined]
        )
    ).first()
    if not dept:
        raise HTTPException(
            status_code=404,
            detail=f"Departamento no encontrado: '{department_name}'",
        )
    return dept.id
