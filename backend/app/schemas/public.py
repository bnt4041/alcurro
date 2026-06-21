from uuid import UUID

from pydantic import BaseModel, Field

from app.models.billing import BillingCycle


class PublicPricingPlanRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    monthly_price_cents: int
    annual_price_cents: int
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


class PublicPaddleConfig(BaseModel):
    enabled: bool
    client_token: str | None
    env: str


class PublicSignupResponse(BaseModel):
    tenant_id: UUID | None = None
    tenant_slug: str | None = None
    company_name: str | None = None
    checkout_url: str | None = None
    admin_login_hint: str | None = None
    pending_signup_id: UUID | None = None
    # Parámetros para el overlay de Paddle.js (cuando hay que pagar)
    paddle_price_id: str | None = None
    paddle_client_token: str | None = None
    paddle_env: str | None = None
    paddle_discount_code: str | None = None
    customer_email: str | None = None
    success_url: str | None = None
