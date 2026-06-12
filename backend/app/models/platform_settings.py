"""Configuración global de la plataforma Alcurro (singleton)."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

PLATFORM_SETTINGS_ID = UUID("00000000-0000-0000-0000-000000000001")


class PlatformSettings(SQLModel, table=True):
    __tablename__ = "platform_settings"

    id: UUID = Field(default=PLATFORM_SETTINGS_ID, primary_key=True)

    # Datos fiscales del emisor (Alcurro como proveedor de facturas)
    legal_name: str = Field(default="Alcurro SL", max_length=200)
    tax_id: str = Field(default="", max_length=30)
    billing_address: str | None = Field(default=None, max_length=300)
    billing_city: str | None = Field(default=None, max_length=100)
    billing_postal_code: str | None = Field(default=None, max_length=10)
    billing_province: str | None = Field(default=None, max_length=100)
    billing_country: str = Field(default="ES", max_length=2)
    billing_email: str | None = Field(default=None, max_length=200)
    billing_phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=200)

    # Datos bancarios para transferencias
    iban: str | None = Field(default=None, max_length=40)
    bank_name: str | None = Field(default=None, max_length=200)
    swift_bic: str | None = Field(default=None, max_length=20)

    # Configuración de facturación
    invoice_prefix: str = Field(default="ALC", max_length=10)
    invoice_next_number: int = Field(default=1, ge=1)
    invoice_current_year: int = Field(default_factory=lambda: datetime.utcnow().year)
    vat_rate: int = Field(default=21, ge=0, le=100)
    invoice_footer_text: str | None = Field(default=None, max_length=500)

    # Automatizaciones
    auto_send_invoice_email: bool = Field(default=False)

    updated_at: datetime = Field(default_factory=datetime.utcnow)
