"""Comunicaciones: envío masivo de textos (+ adjuntos) a empleados y externos.

Dos modos:
- open: solo envío por WhatsApp (texto + adjuntos).
- signature: cada destinatario firma como en Documentos (envelope + OTP), con
  trazabilidad completa.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class CommunicationMode(StrEnum):
    OPEN = "open"
    SIGNATURE = "signature"


class CommunicationStatus(StrEnum):
    DRAFT = "draft"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"


class RecipientStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"          # autenticado (abrió/identificó) en modo firma
    SIGNED = "signed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Communication(SQLModel, table=True):
    __tablename__ = "communications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    company_id: UUID = Field(foreign_key="companies.id", index=True)
    title: str = Field(max_length=255)
    body: str = Field(sa_column=Column(Text, nullable=False))
    mode: str = Field(default=CommunicationMode.OPEN, max_length=20)
    status: str = Field(default=CommunicationStatus.DRAFT, max_length=20, index=True)
    audience_filter: dict | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="employees.id")
    expires_in_days: int = Field(default=14, ge=1, le=90)
    sent_at: datetime | None = Field(default=None)
    cancelled_at: datetime | None = Field(default=None)
    cancel_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CommunicationRecipient(SQLModel, table=True):
    __tablename__ = "communication_recipients"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    communication_id: UUID = Field(foreign_key="communications.id", index=True)
    employee_id: UUID | None = Field(default=None, foreign_key="employees.id", index=True)
    is_external: bool = Field(default=False)
    full_name: str = Field(max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    id_document: str | None = Field(default=None, max_length=20)
    status: str = Field(default=RecipientStatus.PENDING, max_length=20, index=True)
    whatsapp_message_id: str | None = Field(default=None, max_length=100)
    envelope_id: UUID | None = Field(
        default=None, foreign_key="signature_envelopes.id", index=True
    )
    signer_id: UUID | None = Field(default=None, foreign_key="signature_signers.id")
    sent_at: datetime | None = Field(default=None)
    read_at: datetime | None = Field(default=None)
    signed_at: datetime | None = Field(default=None)
    error: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CommunicationAttachment(SQLModel, table=True):
    __tablename__ = "communication_attachments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    communication_id: UUID = Field(foreign_key="communications.id", index=True)
    file_path: str = Field(max_length=500)
    file_name: str = Field(max_length=255)
    mimetype: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
