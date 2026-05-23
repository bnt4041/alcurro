from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.billing import PricingPlan
from app.schemas.public import (
    PublicPricingPlanRead,
    PublicSignupRequest,
    PublicSignupResponse,
    PublicStripeConfig,
    SimulateCheckoutPreview,
    SimulatePaymentRequest,
    SimulatePaymentResponse,
)
from app.services.signup_service import register_tenant
from app.services.stripe_simulation import (
    complete_simulated_checkout,
    get_pending_simulation,
    stripe_simulation_enabled,
    use_real_stripe,
)

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/pricing-plans", response_model=list[PublicPricingPlanRead])
def list_public_pricing_plans(
    session: Session = Depends(get_session),
) -> list[PricingPlan]:
    return list(
        session.exec(
            select(PricingPlan)
            .where(PricingPlan.is_active == True)  # noqa: E712
            .order_by(PricingPlan.sort_order, PricingPlan.name)
        ).all()
    )


@router.get("/stripe-config", response_model=PublicStripeConfig)
def public_stripe_config() -> PublicStripeConfig:
    settings = get_settings()
    real = use_real_stripe()
    sim = stripe_simulation_enabled() and not real
    if real:
        mode = "stripe"
    elif sim:
        mode = "simulation"
    else:
        mode = "none"
    return PublicStripeConfig(
        enabled=real,
        publishable_key=settings.stripe_publishable_key or None,
        simulation_mode=sim,
        checkout_mode=mode,
    )


@router.get("/simulate-checkout/{token}", response_model=SimulateCheckoutPreview)
def preview_simulated_checkout(
    token: str,
    session: Session = Depends(get_session),
) -> SimulateCheckoutPreview:
    if not stripe_simulation_enabled():
        raise HTTPException(status_code=404, detail="Modo simulación no disponible")
    pending = get_pending_simulation(session, token)
    if not pending:
        raise HTTPException(status_code=404, detail="Sesión de pago no encontrada")
    tenant, sub = pending
    return SimulateCheckoutPreview(
        token=token,
        company_name=tenant.name,
        tenant_slug=tenant.slug,
        amount_cents=sub.amount_cents,
        currency=sub.currency,
        plan_name=sub.plan_name,
        billing_cycle=sub.billing_cycle,
        subscription_status=sub.status,
    )


@router.post("/simulate-payment", response_model=SimulatePaymentResponse)
def confirm_simulated_payment(
    data: SimulatePaymentRequest,
    session: Session = Depends(get_session),
) -> SimulatePaymentResponse:
    if not stripe_simulation_enabled():
        raise HTTPException(status_code=404, detail="Modo simulación no disponible")
    try:
        result = complete_simulated_checkout(session, data.token.strip())
        return SimulatePaymentResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/signup", response_model=PublicSignupResponse, status_code=201)
def public_signup(
    data: PublicSignupRequest,
    session: Session = Depends(get_session),
) -> PublicSignupResponse:
    if not data.accept_terms:
        raise HTTPException(
            status_code=400,
            detail="Debes aceptar los términos y condiciones",
        )
    try:
        return register_tenant(session, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
