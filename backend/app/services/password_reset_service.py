"""Servicio de recuperación de contraseña: genera token, envía email/WA, resetea."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.config import get_settings
from app.core.security import hash_password
from app.models.models import Employee
from app.models.password_reset import PasswordResetToken
from app.models.tenant import Company, Tenant


def _find_employee_by_email_or_phone(
    session: Session, email: str | None, phone: str | None, tenant_slug: str | None
) -> tuple[Employee | None, Tenant | None, Company | None]:
    """Busca un empleado por email o teléfono, opcionalmente filtrado por tenant."""
    base_query = select(Employee)

    if tenant_slug:
        tenant = session.exec(
            select(Tenant).where(Tenant.slug == tenant_slug.lower())
        ).first()
        if not tenant:
            return None, None, None
        company_ids = [
            c.id
            for c in session.exec(
                select(Company).where(Company.tenant_id == tenant.id)
            ).all()
        ]
        if not company_ids:
            return None, tenant, None
        base_query = base_query.where(Employee.company_id.in_(company_ids))  # type: ignore[attr-defined]
    else:
        tenant = None

    employee = None
    if email:
        employee = session.exec(
            base_query.where(Employee.email == email.lower().strip())
        ).first()
    if not employee and phone:
        employee = session.exec(
            base_query.where(Employee.phone == phone.strip())
        ).first()

    if employee:
        company = session.get(Company, employee.company_id)
        if not tenant and company:
            tenant = session.get(Tenant, company.tenant_id)
        return employee, tenant, company

    return None, tenant, None


def create_reset_token(session: Session, employee_id: UUID) -> PasswordResetToken:
    token = PasswordResetToken(employee_id=employee_id)
    session.add(token)
    session.flush()
    return token


def send_reset_email(
    employee: Employee, tenant: Tenant | None, token: str
) -> bool:
    """Envía email con enlace de recuperación. Retorna True si se envió."""
    if not employee.email:
        return False

    from app.database import engine
    from app.services.mail_service import MailService, smtp_configured

    settings = get_settings()
    base = settings.public_app_url.rstrip("/")
    reset_url = f"{base}/recuperar/{token}"
    tenant_name = tenant.name if tenant else "tu cuenta"

    try:
        with Session(engine) as s:
            mail_svc = MailService(s)
            if not smtp_configured(mail_svc._settings):  # type: ignore[attr-defined]
                return False
            ok, _ = mail_svc.send(
                to_address=employee.email,
                subject=f"Recuperación de contraseña — {tenant_name}",
                body=(
                    f"Hola {employee.full_name},\n\n"
                    f"Has solicitado restablecer tu contraseña en {tenant_name} (Alcurro).\n\n"
                    f"Usa este enlace para crear una nueva contraseña (válido 15 minutos):\n"
                    f"{reset_url}\n\n"
                    f"Si no has pedido este cambio, ignora el mensaje.\n\n"
                    f"— Alcurro"
                ),
                event_type="password_reset",
                tenant_id=tenant.id if tenant else None,
            )
            return ok
    except Exception:
        return False


def send_reset_whatsapp(
    employee: Employee, tenant: Tenant | None, token: str
) -> bool:
    """Envía mensaje WhatsApp con enlace de recuperación. Retorna True si se envió."""
    if not employee.phone:
        return False

    from app.services.gowa_service import GoWAService

    settings = get_settings()
    base = settings.public_app_url.rstrip("/")
    reset_url = f"{base}/recuperar/{token}"

    tenant_name = tenant.name if tenant else "tu cuenta"
    message = (
        f"Hola {employee.full_name} 👋\n\n"
        f"Has solicitado restablecer tu contraseña en *{tenant_name}*.\n\n"
        f"Usa este enlace para crear una nueva contraseña (válido 15 min):\n"
        f"{reset_url}"
    )

    try:
        from app.database import engine
        with Session(engine) as s:
            gowa = GoWAService(s)
            gowa.send_text_sync(employee.phone, message)
            return True
    except Exception:
        return False


def request_password_reset(
    session: Session,
    email: str | None,
    phone: str | None,
    tenant_slug: str | None,
) -> dict:
    """
    Procesa la solicitud de recuperación.
    Retorna dict con {ok, message, channels}.
    """
    employee, tenant, company = _find_employee_by_email_or_phone(
        session, email, phone, tenant_slug
    )

    # Por seguridad, siempre decimos lo mismo aunque no encontremos al usuario
    if not employee:
        return {
            "ok": True,
            "message": (
                "Si los datos corresponden a un usuario activo, "
                "recibirás instrucciones en unos minutos."
            ),
            "channels": [],
        }

    # Invalidar tokens previos no usados
    for old in session.exec(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.employee_id == employee.id,
            PasswordResetToken.used == False,  # noqa: E712
        )
    ).all():
        old.used = True
        session.add(old)

    token = create_reset_token(session, employee.id)
    session.commit()

    channels: list[str] = []

    # Enviar por email si tiene
    if employee.email:
        try:
            if send_reset_email(employee, tenant, token.token):
                channels.append("email")
        except Exception:
            pass

    # Enviar por WhatsApp si tiene teléfono
    if employee.phone:
        try:
            if send_reset_whatsapp(employee, tenant, token.token):
                channels.append("whatsapp")
        except Exception:
            pass

    return {
        "ok": True,
        "message": (
            "Si los datos corresponden a un usuario activo, "
            "recibirás instrucciones en unos minutos."
        ),
        "channels": channels,
    }


def validate_and_reset_password(
    session: Session, token_str: str, new_password: str
) -> dict:
    """Valida el token y cambia la contraseña. Retorna {ok, message}."""
    token = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token_str,
            PasswordResetToken.used == False,  # noqa: E712
        )
    ).first()

    if not token:
        return {"ok": False, "message": "Token inválido o ya usado."}

    if token.expires_at < datetime.utcnow():
        token.used = True
        session.add(token)
        session.commit()
        return {"ok": False, "message": "El enlace ha caducado (más de 15 minutos). Solicita uno nuevo."}

    employee = session.get(Employee, token.employee_id)
    if not employee or not employee.is_active:
        return {"ok": False, "message": "Usuario no encontrado o inactivo."}

    employee.password_hash = hash_password(new_password)
    session.add(employee)

    token.used = True
    session.add(token)
    session.commit()

    return {"ok": True, "message": "Contraseña actualizada. Ya puedes iniciar sesión."}
