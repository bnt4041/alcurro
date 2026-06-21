"""Facturación: tarifas, descuentos, suscripciones y métodos de pago."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class BillingCycle(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class BillingMethodType(StrEnum):
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    SEPA = "sepa_direct_debit"
    OTHER = "other"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


class PricingPlan(SQLModel, table=True):
    """
    Tarifa del catálogo (ej. Básica: 18€/mes o 15€/mes en contrato anual, 3 usuarios).
    """

    __tablename__ = "pricing_plans"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    monthly_price_cents: int = Field(ge=0, description="Precio mensual sin compromiso anual")
    annual_price_cents: int = Field(
        ge=0,
        description="Precio total del contrato anual (pago único, ej. 18000 = 180€/año)",
    )
    max_active_users: int = Field(ge=1, default=3)
    currency: str = Field(default="EUR", max_length=3)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    stripe_product_id: str | None = Field(default=None, max_length=120)
    stripe_price_monthly_id: str | None = Field(default=None, max_length=120)
    stripe_price_annual_id: str | None = Field(default=None, max_length=120)
    paddle_product_id: str | None = Field(default=None, max_length=80)
    paddle_price_id_monthly: str | None = Field(default=None, max_length=80)
    paddle_price_id_annual: str | None = Field(default=None, max_length=80)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Discount(SQLModel, table=True):
    """Descuento temporal (% o importe fijo) aplicable a tarifas."""

    __tablename__ = "discounts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    discount_type: DiscountType = Field(default=DiscountType.PERCENT)
    value: int = Field(
        ge=0,
        description="Porcentaje 0-100 o céntimos si es fijo",
    )
    valid_from: date
    valid_until: date
    pricing_plan_id: UUID | None = Field(
        default=None,
        foreign_key="pricing_plans.id",
        description="Null = aplica a todas las tarifas",
    )
    is_active: bool = Field(default=True)
    paddle_discount_id: str | None = Field(default=None, max_length=80)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BillingMethod(SQLModel, table=True):
    """Método de pago de la cuenta (tenant). company_id es legacy, ignorar."""

    __tablename__ = "billing_methods"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    company_id: UUID | None = Field(default=None, foreign_key="companies.id", index=True)
    label: str = Field(max_length=120)
    method_type: BillingMethodType = Field(default=BillingMethodType.BANK_TRANSFER)
    is_default: bool = Field(default=False)
    holder_name: str | None = Field(default=None, max_length=200)
    iban_masked: str | None = Field(default=None, max_length=40)
    card_brand: str | None = Field(default=None, max_length=30)
    card_last4: str | None = Field(default=None, max_length=4)
    notes: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Subscription(SQLModel, table=True):
    """Suscripción de la cuenta (tenant) a una tarifa (con descuento opcional)."""

    __tablename__ = "subscriptions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    company_id: UUID | None = Field(default=None, foreign_key="companies.id", index=True)
    pricing_plan_id: UUID | None = Field(default=None, foreign_key="pricing_plans.id")
    discount_id: UUID | None = Field(default=None, foreign_key="discounts.id")
    plan_code: str = Field(default="basica", max_length=50)
    plan_name: str = Field(default="Básica", max_length=120)
    status: SubscriptionStatus = Field(default=SubscriptionStatus.TRIALING)
    amount_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="EUR", max_length=3)
    billing_cycle: str = Field(default=BillingCycle.MONTHLY, max_length=20)
    billing_method_id: UUID | None = Field(default=None, foreign_key="billing_methods.id")
    current_period_start: date | None = Field(default=None)
    current_period_end: date | None = Field(default=None)
    stripe_subscription_id: str | None = Field(default=None, max_length=120, index=True)
    stripe_checkout_session_id: str | None = Field(default=None, max_length=120)
    paddle_subscription_id: str | None = Field(default=None, max_length=80, index=True)
    payment_failure_count: int = Field(default=0, ge=0)
    last_payment_failure_at: datetime | None = Field(default=None)
    pending_plan_id: UUID | None = Field(default=None, foreign_key="pricing_plans.id")
    pending_billing_cycle: str | None = Field(default=None, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StripePaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class StripePayment(SQLModel, table=True):
    """Registro de cobros recibidos vía Stripe."""

    __tablename__ = "stripe_payments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    subscription_id: UUID | None = Field(default=None, foreign_key="subscriptions.id")
    stripe_payment_intent_id: str | None = Field(default=None, max_length=120, index=True)
    stripe_invoice_id: str | None = Field(default=None, max_length=120, index=True)
    stripe_checkout_session_id: str | None = Field(default=None, max_length=120)
    amount_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="EUR", max_length=3)
    status: StripePaymentStatus = Field(default=StripePaymentStatus.PENDING)
    description: str | None = Field(default=None, max_length=500)
    invoice_number: str | None = Field(default=None, max_length=50)
    invoice_pdf_url: str | None = Field(default=None)
    invoice_url: str | None = Field(default=None)
    paid_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaddlePaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaddlePayment(SQLModel, table=True):
    """Registro de cobros recibidos vía Paddle."""

    __tablename__ = "paddle_payments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    subscription_id: UUID | None = Field(default=None, foreign_key="subscriptions.id")
    paddle_invoice_id: str | None = Field(default=None, max_length=80, index=True)
    paddle_subscription_id: str | None = Field(default=None, max_length=80, index=True)
    paddle_transaction_id: str | None = Field(default=None, max_length=80, index=True)
    amount_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="EUR", max_length=3)
    status: PaddlePaymentStatus = Field(default=PaddlePaymentStatus.PENDING)
    description: str | None = Field(default=None, max_length=500)
    invoice_number: str | None = Field(default=None, max_length=50)
    receipt_url: str | None = Field(default=None)
    paid_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PendingSignupStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"


class PendingSignup(SQLModel, table=True):
    """Registro temporal de alta pendiente de confirmación de pago."""

    __tablename__ = "pending_signups"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    data_json: str = Field(description="JSON serializado del formulario de alta")
    tenant_id: UUID | None = Field(default=None, foreign_key="tenants.id", nullable=True)
    paddle_subscription_id: str | None = Field(default=None, max_length=80, index=True)
    status: PendingSignupStatus = Field(default=PendingSignupStatus.PENDING)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
