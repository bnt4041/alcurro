"""Contexto de organización: tenant → empresa → centro → departamento."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.core.deps import get_current_user
from app.database import get_session
from app.models.models import Employee
from app.models.organization import Department, WorkCenter
from app.models.tenant import Company, Tenant


def resolve_department_chain(
    session: Session, department_id: UUID
) -> tuple[Department, WorkCenter, Company]:
    dept = session.get(Department, department_id)
    if not dept or not dept.is_active:
        raise ValueError("department")
    wc = session.get(WorkCenter, dept.work_center_id)
    if not wc or not wc.is_active:
        raise ValueError("work_center")
    company = session.get(Company, wc.company_id)
    if not company or not company.is_active:
        raise ValueError("company")
    return dept, wc, company


def get_company_for_user(
    session: Session, user: Employee, company_id: UUID | None
) -> Company:
    if company_id:
        company = session.get(Company, company_id)
        if not company or not company.is_active:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        user_company = session.get(Company, user.company_id)
        if not user_company or company.tenant_id != user_company.tenant_id:
            raise HTTPException(status_code=403, detail="Empresa fuera de tu cuenta")
        return company
    company = session.get(Company, user.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Empleado sin empresa asignada")
    return company


_ALL_COMPANY_ROLES = {"tenant_admin", "manager", "admin"}


@dataclass
class OrgContext:
    tenant: Tenant
    company: Company
    work_center: WorkCenter | None
    department: Department | None
    user: Employee
    company_scoped: bool = True  # False when no X-Company-Id was sent

    def scope_company_id(self) -> "UUID | None":
        """None = tenant-wide scope (all companies). Used by list endpoints."""
        if self.company_scoped:
            return self.company.id
        if str(self.user.role) in _ALL_COMPANY_ROLES:
            return None
        return self.company.id


def _resolve_work_center(
    session: Session, company: Company, work_center_id: UUID | None
) -> WorkCenter | None:
    if not work_center_id:
        return None
    wc = session.get(WorkCenter, work_center_id)
    if not wc or not wc.is_active or wc.company_id != company.id:
        raise HTTPException(status_code=404, detail="Centro de trabajo no encontrado")
    return wc


def _resolve_department(
    session: Session,
    work_center: WorkCenter | None,
    department_id: UUID | None,
) -> Department | None:
    if not department_id:
        return None
    dept = session.get(Department, department_id)
    if not dept or not dept.is_active:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    if work_center and dept.work_center_id != work_center.id:
        raise HTTPException(status_code=400, detail="Departamento no pertenece al centro")
    if not work_center:
        wc = session.get(WorkCenter, dept.work_center_id)
        if not wc:
            raise HTTPException(status_code=404, detail="Centro de trabajo no encontrado")
    return dept


def get_org_context(
    user: Employee = Depends(get_current_user),
    session: Session = Depends(get_session),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_work_center_id: str | None = Header(default=None, alias="X-Work-Center-Id"),
    x_department_id: str | None = Header(default=None, alias="X-Department-Id"),
) -> OrgContext:
    cid = UUID(x_company_id) if x_company_id else None
    wcid = UUID(x_work_center_id) if x_work_center_id else None
    did = UUID(x_department_id) if x_department_id else None

    company_scoped = cid is not None
    company = get_company_for_user(session, user, cid)
    tenant = session.get(Tenant, company.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Cuenta inactiva")

    work_center = _resolve_work_center(session, company, wcid)
    department = _resolve_department(session, work_center, did)

    if department and not work_center:
        work_center = session.get(WorkCenter, department.work_center_id)

    return OrgContext(
        tenant=tenant,
        company=company,
        work_center=work_center,
        department=department,
        user=user,
        company_scoped=company_scoped,
    )

