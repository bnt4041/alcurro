"""Incidencias de fichaje y vacaciones/permisos."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class IncidentAutoRule(SQLModel, table=True):
    """Reglas automáticas de incidencias por tenant."""

    __tablename__ = "incident_auto_rules"

    tenant_id: UUID = Field(foreign_key="tenants.id", primary_key=True)
    late_entrada_enabled: bool = Field(default=False)
    late_entrada_grace_minutes: int = Field(default=10)
    late_entrada_notify_whatsapp: bool = Field(default=True)
    late_entrada_require_justification: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Incident(SQLModel, table=True):
    __tablename__ = "incidents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    category: str = Field(
        max_length=30,
        description="fichaje | vacaciones | permiso",
    )
    incident_type: str = Field(
        max_length=50,
        description="late_clock_in | manual | leave_adjustment | other",
    )
    status: str = Field(
        default="pending_justification",
        max_length=30,
        description="pending_justification | open | resolved | dismissed",
    )
    source: str = Field(default="auto", max_length=20)
    title: str = Field(max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    clock_in_id: UUID | None = Field(default=None, foreign_key="clock_ins.id", index=True)
    leave_request_id: UUID | None = Field(
        default=None, foreign_key="leave_requests.id", index=True
    )
    minutes_late: int | None = Field(default=None)
    original_data: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    modified_data: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    employee_justification: str | None = Field(default=None, max_length=3000)
    internal_notes: str | None = Field(default=None, max_length=2000)
    public_token: str | None = Field(default=None, max_length=64, index=True)
    whatsapp_notified_at: datetime | None = Field(default=None)
    justified_at: datetime | None = Field(default=None)
    resolved_at: datetime | None = Field(default=None)
    resolved_by_id: UUID | None = Field(default=None, foreign_key="employees.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
