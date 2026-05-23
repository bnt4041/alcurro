"""Cálculo de precios, tarifas y descuentos."""

from datetime import date

from sqlmodel import Session, select

from app.models.billing import (
    BillingCycle,
    Discount,
    DiscountType,
    PricingPlan,
    Subscription,
)


def plan_base_amount_cents(plan: PricingPlan, cycle: str) -> int:
    if cycle == BillingCycle.ANNUAL:
        return plan.annual_price_per_month_cents * 12
    return plan.monthly_price_cents


def plan_display_monthly_cents(plan: PricingPlan, cycle: str) -> int:
    if cycle == BillingCycle.ANNUAL:
        return plan.annual_price_per_month_cents
    return plan.monthly_price_cents


def apply_discount(base_cents: int, discount: Discount | None) -> int:
    if not discount or not discount.is_active:
        return base_cents
    today = date.today()
    if today < discount.valid_from or today > discount.valid_until:
        return base_cents
    if discount.discount_type == DiscountType.PERCENT:
        pct = min(100, max(0, discount.value))
        return max(0, int(base_cents * (100 - pct) / 100))
    return max(0, base_cents - discount.value)


def calculate_subscription_amount(
    plan: PricingPlan,
    cycle: str,
    discount: Discount | None = None,
) -> int:
    base = plan_base_amount_cents(plan, cycle)
    return apply_discount(base, discount)


def discount_applies_to_plan(discount: Discount, plan_id) -> bool:
    if discount.pricing_plan_id is None:
        return True
    return discount.pricing_plan_id == plan_id


def get_active_discount(
    session: Session, discount_id, plan_id
) -> Discount | None:
    if not discount_id:
        return None
    discount = session.get(Discount, discount_id)
    if not discount or not discount.is_active:
        return None
    today = date.today()
    if today < discount.valid_from or today > discount.valid_until:
        return None
    if not discount_applies_to_plan(discount, plan_id):
        return None
    return discount


def get_active_discount_by_code(
    session: Session, code: str | None, plan_id
) -> Discount | None:
    if not code or not code.strip():
        return None
    discount = session.exec(
        select(Discount).where(Discount.code == code.strip().upper())
    ).first()
    if not discount:
        return None
    return get_active_discount(session, discount.id, plan_id)


def sync_subscription_pricing(
    session: Session,
    sub: Subscription,
    plan: PricingPlan,
    cycle: str,
    discount: Discount | None = None,
) -> None:
    sub.pricing_plan_id = plan.id
    sub.discount_id = discount.id if discount else None
    sub.plan_code = plan.code
    sub.plan_name = plan.name
    sub.billing_cycle = cycle
    sub.currency = plan.currency
    sub.amount_cents = calculate_subscription_amount(plan, cycle, discount)


def get_default_plan(session: Session) -> PricingPlan | None:
    plan = session.exec(
        select(PricingPlan)
        .where(PricingPlan.is_active == True)  # noqa: E712
        .order_by(PricingPlan.sort_order)
    ).first()
    if plan:
        return plan
    return session.exec(
        select(PricingPlan).where(PricingPlan.code == "basica")
    ).first()
