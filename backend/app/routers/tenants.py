from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.core.permissions import Permission, require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.database import get_session
from app.models.billing import BillingCycle, PaddlePayment, PaddlePaymentStatus, PricingPlan, Subscription
from app.models.tenant import Company, Tenant
from app.schemas.billing import TenantAccountBillingRead
from app.schemas.tenant import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    TenantBillingUpdate,
    TenantBrandingRead,
    TenantCreate,
    TenantRead,
    TenantUpdate,
    TenantWhatsAppStatusRead,
)
from app.services.billing_read import tenant_account_billing
from app.services.gowa_client import get_shared_whatsapp_session
from app.services.paddle_service import (
    get_paddle_price_id,
    paddle_configured,
    patch_paddle_subscription_variant,
    update_paddle_customer_name,
)
from app.services.pricing_service import (
    calculate_subscription_amount,
    get_active_discount_by_code,
    sync_subscription_pricing,
)
from app.services.org_service import (
    clone_groups_for_tenant,
    ensure_group_templates,
    seed_tenant_organization,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])

UPLOAD_DIR = Path("/app/uploads")
LOGO_DIR = UPLOAD_DIR / "branding"
ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
MAX_LOGO_BYTES = 2 * 1024 * 1024


def _remove_tenant_logo_files(tenant_id: UUID) -> None:
    tenant_dir = LOGO_DIR / str(tenant_id)
    if not tenant_dir.is_dir():
        return
    for old in tenant_dir.glob("logo.*"):
        old.unlink(missing_ok=True)


def public_branding(slug: str, session: Session = Depends(get_session)) -> Tenant:
    tenant = session.exec(select(Tenant).where(Tenant.slug == slug.lower())).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return tenant


@router.get("/current", response_model=TenantRead)
def current_tenant(
    ctx: TenantContext = Depends(get_tenant_context),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> Tenant:
    return ctx.tenant


@router.patch("/current/branding", response_model=TenantRead)
def update_current_branding(
    data: TenantUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    tenant = ctx.tenant
    for key, value in data.model_dump(exclude_unset=True).items():
        if key in ("name", "logo_url", "primary_color", "secondary_color", "accent_color"):
            setattr(tenant, key, value)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.post("/current/logo", response_model=TenantRead)
async def upload_tenant_logo(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_LOGO_TYPES.get(content_type)
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Formato no válido. Usa PNG, JPG, WEBP o SVG.",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="El logo no puede superar 2 MB")

    tenant = ctx.tenant
    tenant_dir = LOGO_DIR / str(tenant.id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    _remove_tenant_logo_files(tenant.id)
    stored = tenant_dir / f"logo{ext}"
    stored.write_bytes(data)
    tenant.logo_url = f"/uploads/branding/{tenant.id}/logo{ext}"
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.delete("/current/logo", response_model=TenantRead)
def remove_tenant_logo(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    tenant = ctx.tenant
    _remove_tenant_logo_files(tenant.id)
    tenant.logo_url = None
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@router.patch("/current/billing", response_model=TenantRead)
def update_current_billing(
    data: TenantBillingUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    tenant = ctx.tenant
    payload = data.model_dump(exclude_unset=True)
    new_legal_name = payload.get("legal_name")
    for key, value in payload.items():
        if key == "billing_email" and value is not None:
            value = str(value)
        setattr(tenant, key, value)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    if new_legal_name and new_legal_name != ctx.tenant.legal_name:
        update_paddle_customer_name(tenant, new_legal_name)
    return tenant


@router.get("/current/billing-summary", response_model=TenantAccountBillingRead)
def current_billing_summary(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> TenantAccountBillingRead:
    data = tenant_account_billing(session, ctx.tenant.id)
    session.commit()
    return TenantAccountBillingRead(**data)


@router.get("/current/companies", response_model=list[CompanyRead])
def list_companies(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
) -> list[Company]:
    return list(
        session.exec(
            select(Company).where(Company.tenant_id == ctx.tenant.id)
        ).all()
    )


@router.post("/current/companies", response_model=CompanyRead, status_code=201)
def create_company(
    data: CompanyCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "companies")),
) -> Company:
    from app.services.org_service import seed_company_organization
    row = Company(tenant_id=ctx.tenant.id, name=data.name, tax_id=data.tax_id)
    session.add(row)
    session.flush()
    seed_company_organization(session, row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/current/companies/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "companies")),
) -> Company:
    row = session.get(Company, company_id)
    if not row or row.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/current/invoices/{invoice_id}/pdf")
def download_tenant_invoice_pdf(
    invoice_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> Response:
    from app.models.invoice import Invoice
    from app.services.invoice_service import get_invoice_pdf_bytes

    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    pdf_bytes = get_invoice_pdf_bytes(session, invoice_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="No se pudo generar el PDF")
    filename = f"{invoice.number.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class TenantPaymentRead(BaseModel):
    id: str
    amount_cents: int
    currency: str
    status: str
    description: str | None
    receipt_url: str | None
    paddle_transaction_id: str | None
    paid_at: str | None
    created_at: str


@router.get("/current/payments", response_model=list[TenantPaymentRead])
def list_tenant_payments(
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> list[TenantPaymentRead]:
    rows = session.exec(
        select(PaddlePayment)
        .where(PaddlePayment.tenant_id == ctx.tenant.id)
        .order_by(PaddlePayment.created_at.desc())  # type: ignore[attr-defined]
        .limit(200)
    ).all()
    status_map = {
        PaddlePaymentStatus.PAID: "Cobrado",
        PaddlePaymentStatus.PENDING: "Pendiente",
        PaddlePaymentStatus.FAILED: "Fallido",
        PaddlePaymentStatus.REFUNDED: "Reembolsado",
    }
    return [
        TenantPaymentRead(
            id=str(r.id),
            amount_cents=r.amount_cents,
            currency=r.currency,
            status=status_map.get(r.status, r.status),
            description=r.description,
            receipt_url=r.receipt_url,
            paddle_transaction_id=r.paddle_transaction_id,
            paid_at=r.paid_at.isoformat() if r.paid_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/current/payments/{payment_id}/invoice-url")
def get_payment_invoice_url(
    payment_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> dict[str, str]:
    """Devuelve una URL fresca a la factura PDF de Paddle (las URLs caducan ~1h)."""
    from app.services.paddle_service import get_transaction_invoice_url

    payment = session.get(PaddlePayment, payment_id)
    if not payment or payment.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    if not payment.paddle_transaction_id:
        raise HTTPException(status_code=404, detail="Este cobro no tiene factura de Paddle asociada")
    url = get_transaction_invoice_url(payment.paddle_transaction_id)
    if not url:
        raise HTTPException(status_code=404, detail="La factura aún no está disponible. Inténtalo en unos minutos.")
    return {"url": url}


@router.get("/current/whatsapp/status", response_model=TenantWhatsAppStatusRead)
async def tenant_whatsapp_status(
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "tenant")),
) -> TenantWhatsAppStatusRead:
    """Estado del WhatsApp compartido de alcurro (solo lectura para cuentas cliente)."""
    data = await get_shared_whatsapp_session(session)
    linked = data.get("connected", False)
    configured = data.get("configured", False)
    if linked:
        msg = (
            "WhatsApp de alcurro está activo. Tus empleados pueden fichar "
            "desde su móvil si tienen el teléfono registrado."
        )
    elif configured:
        msg = (
            "WhatsApp de alcurro pendiente de vincular. "
            "El administrador de la plataforma debe escanear el código QR."
        )
    else:
        msg = "WhatsApp de alcurro aún no está configurado en la plataforma."
    return TenantWhatsAppStatusRead(
        connected=linked,
        configured=configured,
        message=msg,
    )


# --- Plataforma: crear nuevas cuentas tenant (solo super-admin del tenant demo) ---


@router.post("", response_model=TenantRead, status_code=201)
def create_tenant(
    data: TenantCreate,
    session: Session = Depends(get_session),
    x_platform_key: str | None = Header(default=None, alias="X-Platform-Key"),
) -> Tenant:
    if x_platform_key != get_settings().platform_setup_key:
        raise HTTPException(status_code=403, detail="Clave de plataforma inválida")
    from app.services.slug import resolve_tenant_slug

    slug = resolve_tenant_slug(session, data.name, data.slug)
    tenant = Tenant(
        slug=slug,
        name=data.name,
        legal_name=data.legal_name,
        tax_id=data.tax_id,
        billing_email=str(data.billing_email) if data.billing_email else None,
        billing_phone=data.billing_phone,
        billing_address=data.billing_address,
        billing_city=data.billing_city,
        billing_postal_code=data.billing_postal_code,
        billing_province=data.billing_province,
        billing_country=data.billing_country or "ES",
        primary_color=data.primary_color,
        secondary_color=data.secondary_color,
        accent_color=data.accent_color,
        gowa_basic_auth=data.gowa_basic_auth,
        gowa_webhook_path=f"/webhook/whatsapp/{slug}",
    )
    session.add(tenant)
    session.flush()
    ensure_group_templates(session)
    seed_tenant_organization(session, tenant, data.name)
    clone_groups_for_tenant(session, tenant.id)
    from app.services.legal_service import seed_default_legal_documents

    seed_default_legal_documents(session, tenant.id)
    session.commit()
    session.refresh(tenant)
    return tenant


class PlanChangeRequest(BaseModel):
    plan_id: UUID
    billing_cycle: str  # "monthly" | "annual"


class PlanChangePending(BaseModel):
    ok: bool
    message: str
    pending_plan_name: str | None = None
    pending_billing_cycle: str | None = None
    effective_date: str | None = None


@router.post("/current/change-plan", response_model=PlanChangePending)
def request_plan_change(
    data: PlanChangeRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> PlanChangePending:
    """Solicita un cambio de tarifa para el próximo periodo de facturación.

    Restricción: no se puede hacer downgrade si la suscripción activa es anual.
    """
    new_plan = session.get(PricingPlan, data.plan_id)
    if not new_plan or not new_plan.is_active:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada o inactiva")

    if data.billing_cycle not in (BillingCycle.MONTHLY, BillingCycle.ANNUAL):
        raise HTTPException(status_code=400, detail="Ciclo de facturación no válido")

    # Get current subscription for this tenant
    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == ctx.tenant.id)
    ).first()

    if sub:
        current_plan = session.get(PricingPlan, sub.pricing_plan_id) if sub.pricing_plan_id else None
        # Block downgrade if currently on annual billing
        if sub.billing_cycle == BillingCycle.ANNUAL and current_plan:
            if data.billing_cycle == BillingCycle.MONTHLY:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "No puedes cambiar a facturación mensual mientras tienes una "
                        "suscripción anual activa. El cambio estará disponible al vencer "
                        "el período anual actual."
                    ),
                )
            # Annual → annual: block if new plan is cheaper (downgrade)
            new_monthly_equiv = (
                new_plan.annual_price_cents // 12
                if data.billing_cycle == BillingCycle.ANNUAL
                else new_plan.monthly_price_cents
            )
            current_monthly_equiv = (
                current_plan.annual_price_cents // 12
                if sub.billing_cycle == BillingCycle.ANNUAL
                else current_plan.monthly_price_cents
            )
            if new_monthly_equiv < current_monthly_equiv:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "No es posible hacer downgrade de tarifa con una suscripción "
                        "anual activa. Podrás cambiar a una tarifa inferior al vencer "
                        "el período anual."
                    ),
                )

        # Determinar si es upgrade o downgrade
        current_plan = session.get(PricingPlan, sub.pricing_plan_id) if sub.pricing_plan_id else None
        def _monthly_equiv(plan: PricingPlan, cycle: str) -> int:
            return plan.annual_price_cents // 12 if cycle == BillingCycle.ANNUAL else plan.monthly_price_cents

        is_upgrade = True
        if current_plan:
            is_upgrade = _monthly_equiv(new_plan, data.billing_cycle) >= _monthly_equiv(current_plan, sub.billing_cycle)

        sub.pending_plan_id = data.plan_id
        sub.pending_billing_cycle = data.billing_cycle
        session.add(sub)
        session.flush()

        # Sincronizar con Paddle
        ls_error: str | None = None
        if paddle_configured() and sub.paddle_subscription_id:
            price_id = get_paddle_price_id(new_plan, data.billing_cycle)
            if price_id:
                try:
                    patch_paddle_subscription_variant(
                        sub.paddle_subscription_id,
                        price_id,
                        invoice_immediately=is_upgrade,
                    )
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).error(
                        "Error actualizando precio en Paddle sub %s: %s", sub.paddle_subscription_id, exc
                    )
                    ls_error = "El cambio se ha guardado, pero no se pudo actualizar en Paddle."

        session.commit()

        if is_upgrade:
            msg = (
                f"Tarifa actualizada a «{new_plan.name}». "
                f"Se te cobrará ahora la diferencia prorrateada del período actual."
            )
        else:
            msg = (
                f"Cambio a «{new_plan.name}» registrado. "
                f"El nuevo precio se aplicará a partir de la próxima renovación "
                f"({sub.current_period_end.isoformat() if sub.current_period_end else 'siguiente período'})."
            )
        if ls_error:
            msg += f" Aviso: {ls_error}"

        return PlanChangePending(
            ok=True,
            message=msg,
            pending_plan_name=new_plan.name,
            pending_billing_cycle=data.billing_cycle,
            effective_date=sub.current_period_end.isoformat() if sub.current_period_end else None,
        )

    raise HTTPException(status_code=404, detail="No tienes ninguna suscripción activa")


class ApplyDiscountRequest(BaseModel):
    discount_code: str


class ApplyDiscountResponse(BaseModel):
    ok: bool
    message: str
    discount_name: str | None = None
    new_amount_cents: int | None = None
    currency: str | None = None


@router.post("/current/apply-discount", response_model=ApplyDiscountResponse)
def apply_tenant_discount(
    data: ApplyDiscountRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> ApplyDiscountResponse:
    """Aplica un código de descuento a la suscripción activa del tenant."""
    sub = session.exec(
        select(Subscription).where(Subscription.tenant_id == ctx.tenant.id)
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="No tienes ninguna suscripción activa")

    discount = get_active_discount_by_code(session, data.discount_code.strip(), sub.pricing_plan_id)
    if not discount:
        raise HTTPException(status_code=404, detail="Código de descuento no válido o expirado")

    plan = session.get(PricingPlan, sub.pricing_plan_id) if sub.pricing_plan_id else None
    if not plan:
        raise HTTPException(status_code=400, detail="No se puede aplicar el descuento sin tarifa activa")

    new_amount = calculate_subscription_amount(plan, sub.billing_cycle, discount)
    sub.discount_id = discount.id
    sub.amount_cents = new_amount
    session.add(sub)
    session.flush()

    session.commit()

    # Aplicar el descuento también en Paddle (se hereda en los próximos renewals).
    if new_amount == 0:
        msg = f"Descuento «{discount.name}» aplicado — cuenta gratuita en Alcurro."
    else:
        msg = f"Descuento «{discount.name}» aplicado. Nuevo importe en Alcurro: {new_amount / 100:.2f} {sub.currency}."
    if sub.paddle_subscription_id:
        from app.services.paddle_service import apply_paddle_discount_to_subscription
        ok = apply_paddle_discount_to_subscription(sub.paddle_subscription_id, discount.code)
        if not ok:
            msg += " Aviso: no se pudo aplicar el descuento en Paddle automáticamente."
    return ApplyDiscountResponse(
        ok=True,
        message=msg,
        discount_name=discount.name,
        new_amount_cents=new_amount,
        currency=sub.currency,
    )


class BillingCompanyRequest(BaseModel):
    company_id: UUID


@router.put("/current/billing-company", response_model=TenantRead)
def set_billing_company(
    data: BillingCompanyRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.WRITE, "tenant")),
) -> Tenant:
    """Establece la empresa principal de facturación de la cuenta."""
    tenant = ctx.tenant
    company = session.get(Company, data.company_id)
    if not company or company.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Empresa no encontrada en esta cuenta")
    tenant.billing_company_id = data.company_id
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant
