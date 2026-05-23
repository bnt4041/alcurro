from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission
from app.database import get_session
from app.models.organization import Department, WorkCenter
from app.models.tenant import Company
from app.routers.crud_helpers import get_or_404
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentRead,
    OrgTreeCompany,
    OrgTreeWorkCenter,
    WorkCenterCreate,
    WorkCenterRead,
)

router = APIRouter(prefix="/org", tags=["organization"])


@router.get("/tree", response_model=list[OrgTreeCompany])
def org_tree(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "companies")),
) -> list[OrgTreeCompany]:
    companies = session.exec(
        select(Company)
        .where(Company.tenant_id == ctx.tenant.id, Company.is_active == True)  # noqa: E712
        .order_by(Company.name)
    ).all()
    result: list[OrgTreeCompany] = []
    for c in companies:
        wcs = session.exec(
            select(WorkCenter)
            .where(WorkCenter.company_id == c.id, WorkCenter.is_active == True)  # noqa: E712
            .order_by(WorkCenter.name)
        ).all()
        wc_nodes: list[OrgTreeWorkCenter] = []
        for wc in wcs:
            depts = session.exec(
                select(Department)
                .where(
                    Department.work_center_id == wc.id,
                    Department.is_active == True,  # noqa: E712
                )
                .order_by(Department.name)
            ).all()
            wc_nodes.append(
                OrgTreeWorkCenter(
                    id=wc.id,
                    name=wc.name,
                    code=wc.code,
                    departments=[DepartmentRead.model_validate(d) for d in depts],
                )
            )
        result.append(OrgTreeCompany(id=c.id, name=c.name, work_centers=wc_nodes))
    return result


@router.get("/work-centers", response_model=list[WorkCenterRead])
def list_work_centers(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "work_centers")),
) -> list[WorkCenter]:
    stmt = select(WorkCenter).where(
        WorkCenter.company_id == ctx.company.id,
        WorkCenter.is_active == True,  # noqa: E712
    )
    return list(session.exec(stmt.order_by(WorkCenter.name)).all())


@router.post("/work-centers", response_model=WorkCenterRead, status_code=201)
def create_work_center(
    data: WorkCenterCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "work_centers")),
) -> WorkCenter:
    if session.exec(
        select(WorkCenter).where(
            WorkCenter.company_id == ctx.company.id,
            WorkCenter.code == data.code,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Código de centro duplicado")
    row = WorkCenter(company_id=ctx.company.id, **data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(
    work_center_id: UUID | None = None,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "departments")),
) -> list[Department]:
    wc_id = work_center_id or (ctx.work_center.id if ctx.work_center else None)
    if not wc_id:
        raise HTTPException(status_code=400, detail="Indica centro de trabajo")
    wc = session.get(WorkCenter, wc_id)
    if not wc or wc.company_id != ctx.company.id:
        raise HTTPException(status_code=404, detail="Centro no encontrado")
    return list(
        session.exec(
            select(Department)
            .where(Department.work_center_id == wc_id, Department.is_active == True)  # noqa: E712
            .order_by(Department.name)
        ).all()
    )


@router.post("/departments", response_model=DepartmentRead, status_code=201)
def create_department(
    data: DepartmentCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "departments")),
) -> Department:
    wc_id = data.work_center_id or (ctx.work_center.id if ctx.work_center else None)
    if not wc_id:
        raise HTTPException(status_code=400, detail="Indica centro de trabajo")
    wc = session.get(WorkCenter, wc_id)
    if not wc or wc.company_id != ctx.company.id:
        raise HTTPException(status_code=404, detail="Centro no encontrado")
    if session.exec(
        select(Department).where(
            Department.work_center_id == wc_id,
            Department.code == data.code,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Código de departamento duplicado")
    row = Department(
        work_center_id=wc_id,
        name=data.name,
        code=data.code,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
