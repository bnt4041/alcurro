from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class NotificationPreference(SQLModel, table=True):
    """Preferencias de notificación por empleado, evento y canal."""

    __tablename__ = "notification_preferences"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    event_type: str = Field(max_length=50)   # clock_in | clock_out | leave_request | incident | document
    channel: str = Field(max_length=20)       # inapp | whatsapp | email
    enabled: bool = Field(default=True)


class Notification(SQLModel, table=True):
    """Registro de una notificación enviada a un empleado."""

    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    event_type: str = Field(max_length=50)
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    link: str | None = Field(default=None, max_length=500)
    actor_name: str | None = Field(default=None, max_length=200)
    read_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
