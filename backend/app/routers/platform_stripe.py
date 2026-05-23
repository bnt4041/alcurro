from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.core.platform_deps import get_platform_user
from app.database import get_session
from app.models.billing import PricingPlan, StripePayment
from app.models.rbac import PlatformUser
from app.models.tenant import Tenant
from app.schemas.stripe_admin import (
    StripePaymentRead,
    StripePlatformStatus,
    StripeSyncPlanResult,
)
from app.services.stripe_service import stripe_configured, sync_plan_to_stripe

router = APIRouter(prefix="/platform/stripe", tags=["platform-stripe"])


@router.get("/status", response_model=StripePlatformStatus)
def stripe_status(
    _: PlatformUser = Depends(get_platform_user),
) -> StripePlatformStatus:
    settings = get_settings()
    return StripePlatformStatus(
        configured=stripe_configured(),
        publishable_key_set=bool(settings.stripe_publishable_key.strip()),
        webhook_secret_set=bool(settings.stripe_webhook_secret.strip()),
        public_app_url=settings.public_app_url,
    )


@router.get("/payments", response_model=list[StripePaymentRead])
def list_stripe_payments(
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
    limit: int = 100,
) -> list[StripePaymentRead]:
    rows = list(
        session.exec(
            select(StripePayment)
            .order_by(StripePayment.created_at.desc())
            .limit(min(limit, 500))
        ).all()
    )
    tenant_names: dict[UUID, str] = {}
    result: list[StripePaymentRead] = []
    for row in rows:
        tenant_name = None
        if row.tenant_id:
            if row.tenant_id not in tenant_names:
                t = session.get(Tenant, row.tenant_id)
                tenant_names[row.tenant_id] = t.name if t else "—"
            tenant_name = tenant_names[row.tenant_id]
        result.append(
            StripePaymentRead(
                id=row.id,
                tenant_id=row.tenant_id,
                tenant_name=tenant_name,
                subscription_id=row.subscription_id,
                amount_cents=row.amount_cents,
                currency=row.currency,
                status=row.status,
                description=row.description,
                stripe_invoice_id=row.stripe_invoice_id,
                stripe_checkout_session_id=row.stripe_checkout_session_id,
                paid_at=row.paid_at,
                created_at=row.created_at,
            )
        )
    return result


@router.post("/sync-plan/{plan_id}", response_model=StripeSyncPlanResult)
def sync_pricing_plan_to_stripe(
    plan_id: UUID,
    session: Session = Depends(get_session),
    _: PlatformUser = Depends(get_platform_user),
) -> StripeSyncPlanResult:
    if not stripe_configured():
        raise HTTPException(status_code=503, detail="Stripe no está configurado")
    plan = session.get(PricingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    plan = sync_plan_to_stripe(session, plan)
    plan.updated_at = datetime.utcnow()
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return StripeSyncPlanResult(
        plan_id=plan.id,
        stripe_product_id=plan.stripe_product_id,
        stripe_price_monthly_id=plan.stripe_price_monthly_id,
        stripe_price_annual_id=plan.stripe_price_annual_id,
    )
