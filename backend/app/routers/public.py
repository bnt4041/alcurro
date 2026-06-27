from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.billing import PendingSignup, PendingSignupStatus, PricingPlan
from app.schemas.public import (
    PublicPaddleConfig,
    PublicPricingPlanRead,
    PublicSignupRequest,
    PublicSignupResponse,
)
from app.services.paddle_service import paddle_configured
from app.services.signup_service import initiate_signup
from app.services.password_reset_service import (
    request_password_reset,
    validate_and_reset_password,
)
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.config import get_settings
from app.services.pricing_service import (
    calculate_subscription_amount,
    get_active_discount_by_code,
    plan_base_amount_cents,
)


class PublicDiscountPreview(BaseModel):
    valid: bool
    discount_code: str
    discount_type: str
    discount_value: int
    base_amount_cents: int
    final_amount_cents: int
    currency: str

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


@router.get("/discount-preview", response_model=PublicDiscountPreview)
def public_discount_preview(
    plan_id: UUID = Query(...),
    billing_cycle: str = Query(...),
    code: str = Query(...),
    session: Session = Depends(get_session),
) -> PublicDiscountPreview:
    plan = session.get(PricingPlan, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    discount = get_active_discount_by_code(session, code.strip().upper(), plan.id)
    if not discount:
        raise HTTPException(status_code=404, detail="Código de descuento no válido o expirado")
    base = plan_base_amount_cents(plan, billing_cycle)
    final = calculate_subscription_amount(plan, billing_cycle, discount)
    return PublicDiscountPreview(
        valid=True,
        discount_code=code.upper(),
        discount_type=discount.discount_type,
        discount_value=discount.value,
        base_amount_cents=base,
        final_amount_cents=final,
        currency=plan.currency,
    )


class PublicSiteConfig(BaseModel):
    whatsapp_number: str | None = None


@router.get("/site-config", response_model=PublicSiteConfig)
def public_site_config(
    session: Session = Depends(get_session),
) -> PublicSiteConfig:
    from app.services.settings_service import SettingsService

    settings = SettingsService(session).get_or_create()
    number = (getattr(settings, "whatsapp_public_number", None) or "").strip()
    digits = "".join(c for c in number if c.isdigit())
    return PublicSiteConfig(whatsapp_number=digits or None)


@router.get("/paddle-config", response_model=PublicPaddleConfig)
def public_paddle_config() -> PublicPaddleConfig:
    settings = get_settings()
    return PublicPaddleConfig(
        enabled=paddle_configured(),
        client_token=settings.paddle_client_token or None,
        env=settings.paddle_env,
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
        return initiate_signup(session, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    session: Session = Depends(get_session),
) -> ForgotPasswordResponse:
    result = request_password_reset(
        session,
        email=data.email.strip().lower() if data.email else None,
        phone=data.phone.strip() if data.phone else None,
        tenant_slug=data.tenant_slug.strip().lower() if data.tenant_slug else None,
    )
    session.commit()
    return ForgotPasswordResponse(**result)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    data: ResetPasswordRequest,
    session: Session = Depends(get_session),
) -> ResetPasswordResponse:
    result = validate_and_reset_password(
        session,
        token_str=data.token.strip(),
        new_password=data.new_password,
    )
    session.commit()
    return ResetPasswordResponse(**result)


class PendingSignupStatusResponse(BaseModel):
    status: str
    tenant_slug: str | None = None
    admin_login_hint: str | None = None
    error_message: str | None = None


@router.get("/pending-signup/{pending_id}", response_model=PendingSignupStatusResponse)
def get_pending_signup_status(
    pending_id: UUID,
    session: Session = Depends(get_session),
) -> PendingSignupStatusResponse:
    pending = session.get(PendingSignup, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Alta pendiente no encontrada")

    if pending.status == PendingSignupStatus.ACTIVE and pending.tenant_id:
        from app.models.tenant import Tenant
        tenant = session.get(Tenant, pending.tenant_id)
        settings = get_settings()
        base = settings.public_app_url.rstrip("/")
        slug = tenant.slug if tenant else None
        hint = (
            f"Accede en {base}/acceso-cliente con cuenta «{slug}» y usuario ADM001"
            if slug else None
        )
        return PendingSignupStatusResponse(
            status="active",
            tenant_slug=slug,
            admin_login_hint=hint,
        )

    return PendingSignupStatusResponse(
        status=pending.status,
        error_message=pending.error_message,
    )
