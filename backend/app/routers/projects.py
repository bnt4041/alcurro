from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.org_context import OrgContext, get_org_context
from app.core.permissions import Permission, require_permission, require_write
from app.database import get_session
from app.models.project import Project
from app.models.tenant import Company
from app.routers.crud_helpers import get_or_404
from app.schemas.project import (
    ProjectBulkImportRequest,
    ProjectBulkImportResponse,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.code_generator import next_project_code
from app.services.project_bulk_import_service import bulk_import_projects

router = APIRouter(prefix="/projects", tags=["projects"])


def _company_in_tenant(session: Session, company_id: UUID, tenant_id: UUID) -> Company:
    company = session.get(Company, company_id)
    if not company or company.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="Empresa no válida")
    return company


@router.get("", response_model=list[ProjectRead])
def list_projects(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    include_inactive: bool = False,
    _: object = Depends(require_permission(Permission.READ, "companies")),
) -> list[Project]:
    _company_in_tenant(session, ctx.company.id, ctx.tenant.id)
    stmt = select(Project).where(Project.company_id == ctx.company.id)
    if not include_inactive:
        stmt = stmt.where(Project.is_active == True)  # noqa: E712
    return list(session.exec(stmt.order_by(Project.name)).all())


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    data: ProjectCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("companies", "write")),
) -> Project:
    _company_in_tenant(session, ctx.company.id, ctx.tenant.id)
    row = Project(
        company_id=ctx.company.id,
        name=data.name.strip(),
        code=next_project_code(session, ctx.company.id),
        address=(data.address or "").strip() or None,
        planned_hours=data.planned_hours,
        is_active=data.is_active,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("companies", "write")),
) -> Project:
    row = get_or_404(session, Project, project_id)
    if row.company_id != ctx.company.id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    _company_in_tenant(session, row.company_id, ctx.tenant.id)
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"]:
        payload["name"] = str(payload["name"]).strip()
    if "address" in payload:
        payload["address"] = (payload["address"] or "").strip() or None
    for key, value in payload.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.post("/bulk-import", response_model=ProjectBulkImportResponse)
def bulk_import_projects_route(
    data: ProjectBulkImportRequest,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("companies", "write")),
) -> ProjectBulkImportResponse:
    _company_in_tenant(session, ctx.company.id, ctx.tenant.id)
    try:
        return bulk_import_projects(
            session,
            tenant_id=ctx.tenant.id,
            company_id=ctx.company.id,
            rows=data.rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{project_id}", status_code=204)
def deactivate_project(
    project_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_write("companies", "write")),
) -> None:
    row = get_or_404(session, Project, project_id)
    if row.company_id != ctx.company.id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    row.is_active = False
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
