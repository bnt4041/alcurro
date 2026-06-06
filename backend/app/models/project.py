"""Proyectos por empresa y fichajes pendientes de selección de proyecto."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    """Proyecto / obra asociado a una empresa."""

    __tablename__ = "projects"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    company_id: UUID = Field(foreign_key="companies.id", index=True)
    name: str = Field(max_length=200)
    code: str = Field(max_length=50, index=True)
    address: str | None = Field(default=None, max_length=500)
    planned_hours: float | None = Field(
        default=None,
        description="Horas previstas del proyecto (opcional)",
    )
    is_active: bool = Field(default=True)
    active_for_clock: bool = Field(
        default=True,
        description="Si está activo, puede elegirse al fichar por WhatsApp o panel",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ClockPendingFichaje(SQLModel, table=True):
    """Fichaje WhatsApp en espera de que el empleado elija proyecto o confirme."""

    __tablename__ = "clock_pending_fichajes"

    employee_id: UUID = Field(foreign_key="employees.id", primary_key=True)
    record_type: str = Field(max_length=20)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    whatsapp_message_id: str | None = Field(default=None, max_length=100)
    pending_confirmation: bool = Field(
        default=False,
        description="Esperando confirmación sí/no del empleado antes de ejecutar",
    )
    pending_intent: str | None = Field(
        default=None,
        max_length=50,
        description="Intención pendiente de confirmación (fichar_entrada, fichar_salida, etc.)",
    )
    pending_meta: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Metadatos auxiliares para la intención pendiente (título, descripción, etc.)",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
