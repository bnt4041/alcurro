"""Configuración de fichajes y documentos inbound por cuenta."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class ClockSettings(SQLModel, table=True):
    """Preferencias de fichaje WhatsApp / panel por tenant."""

    __tablename__ = "clock_settings"

    tenant_id: UUID = Field(foreign_key="tenants.id", primary_key=True)
    require_geolocation: bool = Field(
        default=False,
        description="Solicitar ubicación al fichar (recomendado por WhatsApp)",
    )
    clock_reminder_minutes: int | None = Field(
        default=None,
        description="Recordatorio si no ha fichado entrada tras X min del inicio de jornada",
    )
    incident_reminder_enabled: bool = Field(
        default=False,
        description="Reservado: recordatorio de incidencias",
    )
    incident_reminder_minutes: int | None = Field(default=None)
    inbound_documents_enabled: bool = Field(default=True)
    inbound_document_codes: list[str] = Field(
        default_factory=lambda: ["dni", "photo", "driving_license", "legal_terms"],
        sa_column=Column(JSON, nullable=False),
    )
    inbound_signature_delivery_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
        description="IDs de document_deliveries de empresa para firma en el alta",
    )
    send_welcome_with_documents: bool = Field(
        default=True,
        description="Incluir solicitud de documentos en mensaje de bienvenida",
    )
    welcome_message_extra: str | None = Field(default=None, max_length=1000)
    daily_summary_enabled: bool = Field(
        default=True,
        description="Permite solicitar resumen del día por WhatsApp",
    )
    require_project_on_clock_in: bool = Field(
        default=False,
        description="Al fichar, el empleado debe indicar el proyecto (WhatsApp y panel)",
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InboundPendingUpload(SQLModel, table=True):
    """Archivo recibido por WhatsApp pendiente de indicar tipo de documento."""

    __tablename__ = "inbound_pending_uploads"

    employee_id: UUID = Field(foreign_key="employees.id", primary_key=True)
    file_path: str = Field(max_length=500)
    filename: str = Field(max_length=255)
    whatsapp_message_id: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeInboundDocument(SQLModel, table=True):
    """Documentación pendiente/recibida del empleado (alta / WhatsApp)."""

    __tablename__ = "employee_inbound_documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", index=True)
    document_code: str = Field(max_length=50, index=True)
    status: str = Field(
        default="pending",
        max_length=20,
        description="pending | received | waived",
    )
    document_delivery_id: UUID | None = Field(
        default=None, foreign_key="document_deliveries.id", index=True
    )
    signature_envelope_id: UUID | None = Field(
        default=None, foreign_key="signature_envelopes.id", index=True
    )
    received_at: datetime | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
