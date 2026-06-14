from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlatformSettingsRead(BaseModel):
    id: UUID
    legal_name: str
    tax_id: str
    billing_address: str | None
    billing_city: str | None
    billing_postal_code: str | None
    billing_province: str | None
    billing_country: str
    billing_email: str | None
    billing_phone: str | None
    website: str | None
    iban: str | None
    bank_name: str | None
    swift_bic: str | None
    invoice_prefix: str
    invoice_next_number: int
    invoice_current_year: int
    vat_rate: int
    invoice_footer_text: str | None
    credit_note_prefix: str
    credit_note_next_number: int
    credit_note_current_year: int
    auto_send_invoice_email: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformSettingsUpdate(BaseModel):
    legal_name: str | None = None
    tax_id: str | None = None
    billing_address: str | None = None
    billing_city: str | None = None
    billing_postal_code: str | None = None
    billing_province: str | None = None
    billing_country: str | None = None
    billing_email: str | None = None
    billing_phone: str | None = None
    website: str | None = None
    iban: str | None = None
    bank_name: str | None = None
    swift_bic: str | None = None
    invoice_prefix: str | None = None
    invoice_next_number: int | None = None
    vat_rate: int | None = None
    invoice_footer_text: str | None = None
    credit_note_prefix: str | None = None
    credit_note_next_number: int | None = None
    auto_send_invoice_email: bool | None = None
