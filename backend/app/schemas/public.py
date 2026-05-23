from uuid import UUID

from pydantic import BaseModel, Field

from app.models.billing import BillingCycle


class PublicPricingPlanRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    monthly_price_cents: int
    annual_price_per_month_cents: int
    max_active_users: int
    currency: str

    model_config = {"from_attributes": True}


class PublicSignupRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    legal_name: str = Field(min_length=2, max_length=200)
    tax_id: str = Field(min_length=1, max_length=50)
    billing_email: str = Field(min_length=5, max_length=255)
    billing_phone: str = Field(min_length=9, max_length=30)
    billing_address: str | None = None
    billing_city: str | None = None
    billing_postal_code: str | None = None
    billing_province: str | None = None
    billing_country: str = "ES"
    account_code: str | None = Field(default=None, max_length=80)
    pricing_plan_id: UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    discount_code: str | None = None
    admin_name: str = Field(min_length=2, max_length=200)
    admin_email: str = Field(min_length=5, max_length=255)
    admin_phone: str = Field(min_length=9, max_length=20)
    admin_password: str = Field(min_length=8, max_length=128)
    accept_terms: bool = Field(description="Debe aceptar términos")


class PublicStripeConfig(BaseModel):
    enabled: bool
    publishable_key: str | None
    simulation_mode: bool
    checkout_mode: str


class SimulateCheckoutPreview(BaseModel):
    token: str
    company_name: str
    tenant_slug: str
    amount_cents: int
    currency: str
    plan_name: str
    billing_cycle: str
    subscription_status: str


class SimulatePaymentRequest(BaseModel):
    token: str


class SimulatePaymentResponse(BaseModel):
    tenant_id: UUID
    tenant_slug: str
    company_name: str
    subscription_status: str
    amount_cents: int
    currency: str
    already_completed: bool
    gowa_status: str
    gowa_ui_url: str | None = None
    gowa_port: int | None = None
    gowa_container_name: str | None = None
    gowa_error: str | None = None
    simulated: bool = True


class PublicSignupResponse(BaseModel):
    tenant_id: UUID
    tenant_slug: str
    company_name: str
    checkout_url: str | None
    stripe_enabled: bool
    simulation_mode: bool = False
    admin_login_hint: str
