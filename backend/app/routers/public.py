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
)
from app.services.signup_service import register_tenant

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
    return PublicStripeConfig(
        enabled=bool(settings.stripe_secret_key.strip()),
        publishable_key=settings.stripe_publishable_key or None,
    )


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
