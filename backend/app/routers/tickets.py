"""Tickets de soporte — lado cuenta (clientes). Solo administradores de cuenta."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.deps import get_current_user
from app.core.org_context import OrgContext, get_org_context
from app.database import get_session
from app.models.models import Employee, Role
from app.models.ticket import TicketSource
from app.schemas.ticket import (
    KbSearchResult,
    TicketCreate,
    TicketDetailRead,
    TicketMessageCreate,
    TicketRead,
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])

_ADMIN_ROLES = {Role.TENANT_ADMIN, Role.ADMIN}


def require_account_admin(user: Employee = Depends(get_current_user)) -> Employee:
    if user.role not in _ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores de la cuenta pueden gestionar tickets",
        )
    return user


@router.get("/kb-search", response_model=list[KbSearchResult])
def kb_search(
    q: str = Query(..., min_length=2),
    _: Employee = Depends(require_account_admin),
) -> list[KbSearchResult]:
    return ticket_service.precheck_docs(q)


@router.get("", response_model=list[TicketRead])
def list_my_tickets(
    status: str | None = None,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: Employee = Depends(require_account_admin),
) -> list[TicketRead]:
    return ticket_service.list_tickets(session, tenant_id=ctx.tenant.id, status=status)


@router.post("", response_model=TicketDetailRead, status_code=201)
def create_ticket(
    data: TicketCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(require_account_admin),
) -> TicketDetailRead:
    ticket = ticket_service.create_ticket(
        session,
        tenant_id=ctx.tenant.id,
        employee=user,
        subject=data.subject,
        body=data.body,
        priority=data.priority,
        category=data.category,
        source=TicketSource.WEB,
    )
    return ticket_service.to_detail(session, ticket, include_internal=False)


@router.get("/{ticket_id}", response_model=TicketDetailRead)
def get_ticket(
    ticket_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: Employee = Depends(require_account_admin),
) -> TicketDetailRead:
    ticket = ticket_service.get_ticket(session, ticket_id, tenant_id=ctx.tenant.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket_service.to_detail(session, ticket, include_internal=False)


@router.post("/{ticket_id}/messages", response_model=TicketDetailRead)
def add_message(
    ticket_id: UUID,
    data: TicketMessageCreate,
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    user: Employee = Depends(require_account_admin),
) -> TicketDetailRead:
    ticket = ticket_service.get_ticket(session, ticket_id, tenant_id=ctx.tenant.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket_service.add_client_message(session, ticket, user, data.body)
    return ticket_service.to_detail(session, ticket, include_internal=False)
