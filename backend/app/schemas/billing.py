from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.billing import BillingMethodType, SubscriptionStatus


class BillingMethodRead(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID | None
    label: str
    method_type: BillingMethodType
    is_default: bool
    holder_name: str | None
    iban_masked: str | None
    card_brand: str | None
    card_last4: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingMethodCreate(BaseModel):
    company_id: UUID | None = None
    label: str = Field(min_length=1, max_length=120)
    method_type: BillingMethodType = BillingMethodType.BANK_TRANSFER
    is_default: bool = False
    holder_name: str | None = None
    iban_masked: str | None = None
    card_brand: str | None = None
    card_last4: str | None = None
    notes: str | None = None


class BillingMethodUpdate(BaseModel):
    label: str | None = None
    method_type: BillingMethodType | None = None
    is_default: bool | None = None
    holder_name: str | None = None
    iban_masked: str | None = None
    card_brand: str | None = None
    card_last4: str | None = None
    notes: str | None = None


class SubscriptionRead(BaseModel):
    id: UUID
    tenant_id: UUID
    company_id: UUID
    pricing_plan_id: UUID | None
    discount_id: UUID | None
    plan_code: str
    plan_name: str
    status: SubscriptionStatus
    amount_cents: int
    currency: str
    billing_cycle: str
    max_active_users: int | None = None
    billing_method_id: UUID | None
    current_period_start: date | None
    current_period_end: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionUpdate(BaseModel):
    pricing_plan_id: UUID | None = None
    discount_id: UUID | None = None
    plan_code: str | None = None
    plan_name: str | None = None
    status: SubscriptionStatus | None = None
    amount_cents: int | None = Field(default=None, ge=0)
    currency: str | None = None
    billing_cycle: str | None = None
    billing_method_id: UUID | None = None
    current_period_start: date | None = None
    current_period_end: date | None = None


class CompanyBillingRead(BaseModel):
    id: UUID
    name: str
    tax_id: str | None
    is_active: bool
    legal_name: str | None
    billing_email: str | None
    billing_phone: str | None
    billing_address: str | None
    billing_city: str | None
    billing_postal_code: str | None
    billing_province: str | None
    billing_country: str
    subscription: SubscriptionRead | None
    billing_methods: list[BillingMethodRead]


class CompanyBillingUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    is_active: bool | None = None
    legal_name: str | None = None
    billing_email: str | None = None
    billing_phone: str | None = None
    billing_address: str | None = None
    billing_city: str | None = None
    billing_postal_code: str | None = None
    billing_province: str | None = None
    billing_country: str | None = None


class CompanyBillingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    tax_id: str | None = None
    legal_name: str | None = None
    billing_email: str | None = None
    billing_phone: str | None = None


class TenantBillingOverview(BaseModel):
    tenant_id: UUID
    tenant_name: str
    legal_name: str | None
    tax_id: str | None
    billing_email: str | None
    billing_phone: str | None
    billing_address: str | None
    billing_city: str | None
    billing_postal_code: str | None
    billing_province: str | None
    billing_country: str
    account_billing_methods: list[BillingMethodRead]
    companies: list[CompanyBillingRead]
