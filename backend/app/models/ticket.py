"""Tickets de soporte/producto entre cuentas (clientes) y plataforma (Alcurro)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TicketStatus(StrEnum):
    OPEN = "open"          # abierto, pendiente de plataforma
    PENDING = "pending"    # esperando respuesta del cliente
    RESOLVED = "resolved"  # resuelto (a confirmar/cerrar)
    CLOSED = "closed"      # cerrado


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TicketSource(StrEnum):
    WEB = "web"
    WHATSAPP = "whatsapp"


class TicketAuthorType(StrEnum):
    CLIENT = "client"      # admin de cuenta
    PLATFORM = "platform"  # admin de plataforma


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    created_by_employee_id: UUID = Field(foreign_key="employees.id", index=True)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=4000)
    status: str = Field(default=TicketStatus.OPEN, max_length=20, index=True)
    priority: str = Field(default=TicketPriority.NORMAL, max_length=20)
    category: str | None = Field(default=None, max_length=80)
    source: str = Field(default=TicketSource.WEB, max_length=20)
    assigned_platform_user_id: UUID | None = Field(
        default=None, foreign_key="platform_users.id", index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: datetime | None = Field(default=None)


class TicketMessage(SQLModel, table=True):
    __tablename__ = "ticket_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="tickets.id", index=True)
    author_type: str = Field(max_length=20)  # client | platform
    author_employee_id: UUID | None = Field(
        default=None, foreign_key="employees.id"
    )
    author_platform_user_id: UUID | None = Field(
        default=None, foreign_key="platform_users.id"
    )
    body: str = Field(max_length=4000)
    is_internal: bool = Field(
        default=False, description="Nota interna de plataforma, no visible al cliente"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
