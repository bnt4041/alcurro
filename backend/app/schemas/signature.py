from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SignerInput(BaseModel):
    employee_id: UUID | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    id_document: str | None = None
    sign_order: int = Field(default=1, ge=1)


class SignatureEnvelopeCreate(BaseModel):
    document_delivery_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    signers: list[SignerInput] = Field(min_length=1)
    expires_in_days: int = Field(default=14, ge=1, le=90)
    send_notifications: bool = True


class SignatureSignerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    envelope_id: UUID
    employee_id: UUID | None
    full_name: str
    email: str | None
    phone: str | None
    id_document: str
    sign_order: int
    status: str
    signed_at: datetime | None
    signer_name: str | None
    ip_address: str | None


class SignatureEnvelopeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    document_delivery_id: UUID | None
    reference: str
    title: str
    status: str
    original_hash: str
    signed_path: str | None
    signed_hash: str | None
    certificate_path: str | None
    expires_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime
    signers: list[SignatureSignerRead] = Field(default_factory=list)


class SignatureEnvelopeCancel(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class PublicSignerMeta(BaseModel):
    full_name: str
    document_title: str
    company_name: str
    email_hint: str | None
    phone_hint: str | None
    status: str
    envelope_status: str
    requires_otp: bool


class PublicStartRequest(BaseModel):
    id_document: str
    email: str | None = None
    phone: str | None = None


class PublicVerifyOtpRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class PublicSignRequest(BaseModel):
    signature_base64: str = Field(min_length=20)
    signer_name: str = Field(min_length=2, max_length=200)
    accept_terms: bool = True
