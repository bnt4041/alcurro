from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.billing import Discount, PricingPlan
from app.models.rbac import PlatformUser
from app.models.billing import BillingCycle
from app.schemas.pricing import (
    DiscountCreate,
    DiscountRead,
    DiscountUpdate,
    PricePreview,
    PricePreviewRequest,
    PricingPlanCreate,
    PricingPlanRead,
    PricingPlanUpdate,
)
from app.services.pricing_service import (
    calculate_subscription_amount,
    get_active_discount,
    plan_base_amount_cents,
    plan_display_monthly_cents,
)
router = APIRouter(prefix="/platform", tags=["platform-catalog"])


@router.get("/pricing-plans", response_model=list[PricingPlanRead])
def list_pricing_plans(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    active_only: bool = Query(False),
) -> list[PricingPlan]:
    stmt = select(PricingPlan).order_by(PricingPlan.sort_order, PricingPlan.name)
    if active_only:
        stmt = stmt.where(PricingPlan.is_active == True)  # noqa: E712
    return list(session.exec(stmt).all())


@router.post("/pricing-plans", response_model=PricingPlanRead, status_code=201)
def create_pricing_plan(
    data: PricingPlanCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PricingPlan:
    if session.exec(select(PricingPlan).where(PricingPlan.code == data.code)).first():
        raise HTTPException(status_code=409, detail="Ya existe una tarifa con ese código")
    row = PricingPlan(**data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/pricing-plans/{plan_id}", response_model=PricingPlanRead)
def update_pricing_plan(
    plan_id: UUID,
    data: PricingPlanUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PricingPlan:
    row = session.get(PricingPlan, plan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/pricing-plans/{plan_id}", status_code=204)
def delete_pricing_plan(
    plan_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> None:
    row = session.get(PricingPlan, plan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    session.delete(row)
    session.commit()


@router.get("/discounts", response_model=list[DiscountRead])
def list_discounts(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> list[Discount]:
    return list(
        session.exec(select(Discount).order_by(Discount.valid_from.desc())).all()
    )


@router.post("/discounts", response_model=DiscountRead, status_code=201)
def create_discount(
    data: DiscountCreate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Discount:
    if data.valid_until < data.valid_from:
        raise HTTPException(status_code=400, detail="La fecha fin debe ser posterior al inicio")
    if session.exec(select(Discount).where(Discount.code == data.code)).first():
        raise HTTPException(status_code=409, detail="Ya existe un descuento con ese código")
    if data.pricing_plan_id and not session.get(PricingPlan, data.pricing_plan_id):
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    row = Discount(**data.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/discounts/{discount_id}", response_model=DiscountRead)
def update_discount(
    discount_id: UUID,
    data: DiscountUpdate,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> Discount:
    row = session.get(Discount, discount_id)
    if not row:
        raise HTTPException(status_code=404, detail="Descuento no encontrado")
    payload = data.model_dump(exclude_unset=True)
    vf = payload.get("valid_from", row.valid_from)
    vu = payload.get("valid_until", row.valid_until)
    if vu < vf:
        raise HTTPException(status_code=400, detail="La fecha fin debe ser posterior al inicio")
    for key, value in payload.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/discounts/{discount_id}", status_code=204)
def delete_discount(
    discount_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> None:
    row = session.get(Discount, discount_id)
    if not row:
        raise HTTPException(status_code=404, detail="Descuento no encontrado")
    session.delete(row)
    session.commit()


@router.post("/pricing/preview", response_model=PricePreview)
def preview_price(
    data: PricePreviewRequest,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> PricePreview:
    plan = session.get(PricingPlan, data.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    discount = get_active_discount(session, data.discount_id, plan.id)
    cycle = data.billing_cycle.value
    return PricePreview(
        plan_id=plan.id,
        billing_cycle=data.billing_cycle,
        discount_id=discount.id if discount else None,
        base_amount_cents=plan_base_amount_cents(plan, cycle),
        final_amount_cents=calculate_subscription_amount(plan, cycle, discount),
        monthly_display_cents=plan_display_monthly_cents(plan, cycle),
        currency=plan.currency,
    )
