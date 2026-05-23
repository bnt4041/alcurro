from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.billing import StripePaymentStatus


class StripePlatformStatus(BaseModel):
    configured: bool
    publishable_key_set: bool
    webhook_secret_set: bool
    public_app_url: str


class StripePaymentRead(BaseModel):
    id: UUID
    tenant_id: UUID | None
    tenant_name: str | None
    subscription_id: UUID | None
    amount_cents: int
    currency: str
    status: StripePaymentStatus
    description: str | None
    stripe_invoice_id: str | None
    stripe_checkout_session_id: str | None
    paid_at: datetime | None
    created_at: datetime


class StripeSyncPlanResult(BaseModel):
    plan_id: UUID
    stripe_product_id: str | None
    stripe_price_monthly_id: str | None
    stripe_price_annual_id: str | None
