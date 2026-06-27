"""Tickets de soporte — lado plataforma (admins de Alcurro)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.rbac import PlatformUser
from app.schemas.ticket import (
    TicketDetailRead,
    TicketMessageCreate,
    TicketRead,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter(prefix="/platform/tickets", tags=["platform-tickets"])


class PlatformAdminOption(BaseModel):
    id: UUID
    full_name: str


@router.get("", response_model=list[TicketRead])
def list_all_tickets(
    status: str | None = None,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[TicketRead]:
    return ticket_service.list_tickets(session, status=status)


@router.get("/admins", response_model=list[PlatformAdminOption])
def list_platform_admins(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[PlatformAdminOption]:
    rows = session.exec(
        select(PlatformUser).where(PlatformUser.is_active == True)  # noqa: E712
    ).all()
    return [PlatformAdminOption(id=p.id, full_name=p.full_name) for p in rows]


@router.get("/{ticket_id}", response_model=TicketDetailRead)
def get_ticket(
    ticket_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> TicketDetailRead:
    ticket = ticket_service.get_ticket(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket_service.to_detail(session, ticket, include_internal=True)


@router.patch("/{ticket_id}", response_model=TicketDetailRead)
def update_ticket(
    ticket_id: UUID,
    data: TicketUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> TicketDetailRead:
    ticket = ticket_service.get_ticket(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    fields = data.model_dump(exclude_unset=True)
    ticket = ticket_service.update_ticket(
        session,
        ticket,
        status=fields.get("status"),
        priority=fields.get("priority"),
        assigned_platform_user_id=(
            fields["assigned_platform_user_id"]
            if "assigned_platform_user_id" in fields
            else ...
        ),
    )
    return ticket_service.to_detail(session, ticket, include_internal=True)


@router.post("/{ticket_id}/messages", response_model=TicketDetailRead)
def add_message(
    ticket_id: UUID,
    data: TicketMessageCreate,
    session: Session = Depends(get_session),
    platform_user: PlatformUser = Depends(get_platform_user),
) -> TicketDetailRead:
    ticket = ticket_service.get_ticket(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket_service.add_platform_message(
        session, ticket, platform_user, data.body, is_internal=data.is_internal
    )
    return ticket_service.to_detail(session, ticket, include_internal=True)
