from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.billing import BillingCycle, DiscountType


class PricingPlanRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    monthly_price_cents: int
    annual_price_cents: int
    max_active_users: int
    currency: str
    is_active: bool
    sort_order: int
    stripe_product_id: str | None = None
    stripe_price_monthly_id: str | None = None
    stripe_price_annual_id: str | None = None
    ls_product_id: str | None = None
    ls_variant_id_monthly: str | None = None
    ls_variant_id_annual: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PricingPlanCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    monthly_price_cents: int = Field(ge=0)
    annual_price_cents: int = Field(ge=0)
    max_active_users: int = Field(ge=1, default=3)
    currency: str = "EUR"
    is_active: bool = True
    sort_order: int = 0
    ls_variant_id_monthly: str | None = None
    ls_variant_id_annual: str | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: object) -> str:
        return str(v).lower().strip()


class PricingPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    monthly_price_cents: int | None = Field(default=None, ge=0)
    annual_price_cents: int | None = Field(default=None, ge=0)
    max_active_users: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    sort_order: int | None = None
    ls_variant_id_monthly: str | None = None
    ls_variant_id_annual: str | None = None


class DiscountRead(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    discount_type: DiscountType
    value: int
    valid_from: date
    valid_until: date
    pricing_plan_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscountCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    discount_type: DiscountType = DiscountType.PERCENT
    value: int = Field(ge=0)
    valid_from: date
    valid_until: date
    pricing_plan_id: UUID | None = None
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: object) -> str:
        return str(v).lower().strip()

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: int, info) -> int:
        dtype = info.data.get("discount_type")
        if dtype == DiscountType.PERCENT and v > 100:
            raise ValueError("El porcentaje no puede superar 100")
        return v


class DiscountUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    discount_type: DiscountType | None = None
    value: int | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_until: date | None = None
    pricing_plan_id: UUID | None = None
    is_active: bool | None = None


class PricePreviewRequest(BaseModel):
    plan_id: UUID
    billing_cycle: BillingCycle
    discount_id: UUID | None = None


class PricePreview(BaseModel):
    plan_id: UUID
    billing_cycle: BillingCycle
    discount_id: UUID | None = None
    base_amount_cents: int
    final_amount_cents: int
    monthly_display_cents: int
    currency: str
