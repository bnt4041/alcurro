from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.invoice import InvoiceStatus


class InvoiceListItem(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: str | None = None
    number: str
    concept: str
    base_cents: int
    vat_rate: int
    vat_cents: int
    total_cents: int
    currency: str
    issue_date: date
    due_date: date | None
    status: InvoiceStatus
    pdf_url: str | None
    email_sent_at: datetime | None
    stripe_payment_id: UUID | None
    ls_payment_id: UUID | None
    ls_invoice_ref: str | None = None
    credit_note_for_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceDetail(InvoiceListItem):
    recipient_legal_name: str | None
    recipient_tax_id: str | None
    recipient_address: str | None
    recipient_city: str | None
    recipient_postal_code: str | None
    recipient_province: str | None
    recipient_country: str
    recipient_email: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    tenant_id: UUID
    concept: str
    total_cents: int
    currency: str = "EUR"
    vat_rate: int | None = None
    due_date: date | None = None
    stripe_payment_id: UUID | None = None


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


class InvoiceUpdate(BaseModel):
    concept: str | None = None
    due_date: date | None = None
    recipient_legal_name: str | None = None
    recipient_tax_id: str | None = None
    recipient_address: str | None = None
    recipient_city: str | None = None
    recipient_postal_code: str | None = None
    recipient_province: str | None = None
    recipient_country: str | None = None
    recipient_email: str | None = None
