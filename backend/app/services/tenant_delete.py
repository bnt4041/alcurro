"""Eliminación permanente de una cuenta (tenant) y datos asociados."""

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.models.models import Employee, ShiftConfiguration
from app.models.organization import Department, WorkCenter
from app.models.rbac import UserGroup
from app.models.tenant import Company, Tenant


def _purge_company(session: Session, company_id: UUID) -> None:
    employees = list(
        session.exec(select(Employee).where(Employee.company_id == company_id)).all()
    )
    if employees:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: la cuenta tiene empleados",
        )

    for wc in session.exec(
        select(WorkCenter).where(WorkCenter.company_id == company_id)
    ).all():
        for dept in session.exec(
            select(Department).where(Department.work_center_id == wc.id)
        ).all():
            session.delete(dept)
        session.delete(wc)

    for sc in session.exec(
        select(ShiftConfiguration).where(ShiftConfiguration.company_id == company_id)
    ).all():
        session.delete(sc)

    company = session.get(Company, company_id)
    if company:
        session.delete(company)


def delete_tenant_permanent(session: Session, tenant_id: UUID) -> None:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    companies = list(
        session.exec(select(Company).where(Company.tenant_id == tenant_id)).all()
    )
    company_ids = [c.id for c in companies]
    if company_ids:
        stray = session.exec(
            select(Employee).where(col(Employee.company_id).in_(company_ids))
        ).first()
        if stray:
            raise HTTPException(
                status_code=409,
                detail="No se puede eliminar: la cuenta tiene empleados",
            )

    for company in companies:
        _purge_company(session, company.id)

    for group in session.exec(
        select(UserGroup).where(UserGroup.tenant_id == tenant_id)
    ).all():
        session.delete(group)

    session.delete(tenant)
    session.flush()
