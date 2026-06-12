"""Facturas emitidas por Alcurro a sus clientes (tenants)."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    CANCELLED = "cancelled"
    CREDIT_NOTE = "credit_note"


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)

    # Número de factura único (ej. ALC-2024-0001)
    number: str = Field(max_length=50, unique=True, index=True)

    # Datos del receptor en el momento de emitir la factura (snapshot)
    recipient_legal_name: str | None = Field(default=None, max_length=200)
    recipient_tax_id: str | None = Field(default=None, max_length=30)
    recipient_address: str | None = Field(default=None, max_length=300)
    recipient_city: str | None = Field(default=None, max_length=100)
    recipient_postal_code: str | None = Field(default=None, max_length=10)
    recipient_province: str | None = Field(default=None, max_length=100)
    recipient_country: str = Field(default="ES", max_length=2)
    recipient_email: str | None = Field(default=None, max_length=200)

    # Concepto e importes
    concept: str = Field(default="Suscripción alcurro", max_length=500)
    base_cents: int = Field(default=0, ge=0)
    vat_rate: int = Field(default=21, ge=0, le=100)
    vat_cents: int = Field(default=0, ge=0)
    total_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="EUR", max_length=3)

    # Fechas
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = Field(default=None)

    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)

    # Relaciones opcionales
    stripe_payment_id: UUID | None = Field(
        default=None, foreign_key="stripe_payments.id", index=True
    )
    credit_note_for_id: UUID | None = Field(
        default=None, foreign_key="invoices.id"
    )

    # PDF generado y almacenado
    pdf_url: str | None = Field(default=None)

    # Email
    email_sent_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
