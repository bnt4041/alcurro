"""Schemas Pydantic para tickets de soporte."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KbSearchResult(BaseModel):
    title: str
    source: str
    snippet: str


class TicketMessageRead(BaseModel):
    id: UUID
    author_type: str
    author_name: str | None = None
    body: str
    is_internal: bool
    created_at: datetime


class TicketMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    is_internal: bool = False


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=4000)
    priority: str = "normal"
    category: str | None = None


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_platform_user_id: UUID | None = None


class TicketRead(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: str | None = None
    created_by_employee_id: UUID
    created_by_name: str | None = None
    subject: str
    body: str
    status: str
    priority: str
    category: str | None = None
    source: str
    assigned_platform_user_id: UUID | None = None
    assigned_to_name: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None


class TicketDetailRead(TicketRead):
    messages: list[TicketMessageRead] = []
