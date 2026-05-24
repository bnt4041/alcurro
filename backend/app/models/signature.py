"""Firma electrónica de documentos (envelope + firmantes + auditoría)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class EnvelopeStatus(StrEnum):
    DRAFT = "borrador"
    SENT = "enviado"
    PARTIAL = "parcial"
    COMPLETED = "completado"
    CANCELLED = "cancelado"
    EXPIRED = "expirado"


class SignerStatus(StrEnum):
    PENDING = "pendiente"
    AUTHENTICATED = "autenticado"
    SIGNED = "firmado"
    EXPIRED = "expirado"


class SignatureEnvelope(SQLModel, table=True):
    __tablename__ = "signature_envelopes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    document_delivery_id: UUID | None = Field(
        default=None, foreign_key="document_deliveries.id", index=True
    )
    reference: str = Field(max_length=32, index=True)
    title: str = Field(max_length=255)
    status: str = Field(default=EnvelopeStatus.DRAFT, max_length=20, index=True)
    original_path: str = Field(max_length=500)
    original_hash: str = Field(max_length=64)
    signed_path: str | None = Field(default=None, max_length=500)
    signed_hash: str | None = Field(default=None, max_length=64)
    certificate_path: str | None = Field(default=None, max_length=500)
    certificate_json_path: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    cancelled_at: datetime | None = Field(default=None)
    cancel_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SignatureSigner(SQLModel, table=True):
    __tablename__ = "signature_signers"
    __table_args__ = (
        UniqueConstraint("envelope_id", "sign_order", name="uq_signer_envelope_order"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    envelope_id: UUID = Field(foreign_key="signature_envelopes.id", index=True)
    employee_id: UUID | None = Field(default=None, foreign_key="employees.id", index=True)
    full_name: str = Field(max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    id_document: str = Field(max_length=20, index=True)
    sign_order: int = Field(default=1, ge=1)
    status: str = Field(default=SignerStatus.PENDING, max_length=20)
    token_hash: str = Field(max_length=64, index=True)
    token_plain: str | None = Field(
        default=None,
        max_length=64,
        description="Solo se guarda hasta el primer envío; luego null",
    )
    otp_verified_at: datetime | None = Field(default=None)
    signed_at: datetime | None = Field(default=None)
    signature_path: str | None = Field(default=None, max_length=500)
    signer_name: str | None = Field(
        default=None, max_length=200, description="Nombre escrito al firmar"
    )
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignatureOtp(SQLModel, table=True):
    __tablename__ = "signature_otps"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    signer_id: UUID = Field(foreign_key="signature_signers.id", index=True)
    code_hash: str = Field(max_length=64)
    expires_at: datetime
    attempts: int = Field(default=0)
    used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignatureEvent(SQLModel, table=True):
    __tablename__ = "signature_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    envelope_id: UUID = Field(foreign_key="signature_envelopes.id", index=True)
    event_type: str = Field(max_length=50, index=True)
    payload_json: str = Field(default="{}")
    prev_hash: str | None = Field(default=None, max_length=64)
    event_hash: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignatureNotification(SQLModel, table=True):
    __tablename__ = "signature_notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    envelope_id: UUID = Field(foreign_key="signature_envelopes.id", index=True)
    signer_id: UUID | None = Field(default=None, foreign_key="signature_signers.id")
    channel: str = Field(max_length=20)
    event_type: str = Field(max_length=30)
    success: bool = Field(default=True)
    detail: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
