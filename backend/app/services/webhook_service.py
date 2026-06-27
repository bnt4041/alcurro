from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.models.models import (
    BreakType,
    Employee,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
)
from app.models.tenant import Tenant
from app.schemas.ollama import OllamaIntentResponse
from app.schemas.whatsapp import GoWAMessage, GoWAWebhookPayload
from app.services.break_service import BreakService
from app.services.clock_pending_service import (
    clear_pending,
    get_pending,
    is_pending_confirmation,
    set_pending,
)
from app.services.clock_incident_hook import (
    should_notify_whatsapp,
    whatsapp_message_for_incident,
)
from app.models.incident import Incident
from app.services.incident_service import (
    check_missing_clock_out,
    get_pending_justification_incidents,
    submit_employee_justification,
    add_note,
)
from app.services.clock_service import ClockService
from app.services.clock_settings_service import get_or_create_settings
from app.services.daily_summary_service import build_daily_summary
from app.services.employee_onboarding_service import (
    build_welcome_message,
    complete_pending_upload,
    mark_welcome_sent,
    receive_inbound_file,
    seed_inbound_documents,
    should_send_welcome,
)
from app.services.gowa_service import GoWAService
from app.services.inbound_pending_service import (
    get_pending_upload,
    pending_file_documents,
    resolve_document_from_reply,
    set_pending_upload,
)
from app.services.clock_settings_service import inbound_name
from app.services.geocoding import reverse_geocode
from app.services.whatsapp_format import (
    format_break_registered,
    format_clock_registered,
    format_confirmation_cancelled,
    format_conversational_help,
    format_geo_hint,
    format_geo_request,
    format_inbound_document_picker,
)
from app.services.leave_service import LeaveService
from app.services.ai_conversation_service import append_message, build_system_prompt, get_history_for_ollama, _to_spain
from app.services.ai_usage_service import profile_key_for_employee
from app.services.ollama_service import OllamaService
from app.services.whatsapp_nlu import (
    build_confirmation_message,
    is_affirmative_reply,
    is_cancel_or_new_intent,
    is_negative_reply,
    normalize_whatsapp_text,
)
from app.services.whatsapp_permission_service import (
    ACTION_LABELS,
    can_whatsapp_inbound_media,
    can_whatsapp_location_clock,
    denial_message,
    is_whatsapp_action_allowed,
    list_whatsapp_actions_for_employee,
)

_REPLY_MAX = 2000

import re as _re
_RE_SALIDA_VERBS = _re.compile(
    r"^\s*(me\s+voy|me\s+marcho|me\s+piro|termino|acabo|finalizo|salida|"
    r"ficho\s*(salida|ya)?|fichar\s*salida|fin\s+de\s+jornada|salgo|"
    r"he\s+terminado|he\s+acabado|voy\s+a\s+salir)[,.\s]*",
    _re.IGNORECASE,
)
_RE_SKIP_SUMMARY = _re.compile(
    r"^\s*(sin\s+resumen|–|—|-+|nada|no|skip|omitir|sin\s+novedad|sin\s+novedades|paso|ok|vale|ninguna?)\s*$",
    _re.IGNORECASE,
)
_RE_JUSTIFICAR = _re.compile(
    r"^\s*justific[ao]r?\s*[:\-]?\s*",
    _re.IGNORECASE,
)


def _extract_justification_text(text: str) -> str | None:
    """Devuelve el texto de justificación si el mensaje empieza por «justificar».
    Si el mensaje es sólo «justificar» (sin texto), devuelve cadena vacía.
    Devuelve None si el mensaje no es una justificación.
    """
    stripped = text.strip()
    if not _RE_JUSTIFICAR.match(stripped):
        return None
    body = _RE_JUSTIFICAR.sub("", stripped).strip()
    return body  # "" si solo dijo "justificar"


def _extract_work_summary(text: str) -> str | None:
    """Extrae el texto libre tras el verbo de salida como resumen del día."""
    cleaned = _RE_SALIDA_VERBS.sub("", text).strip(" .,;:")
    return cleaned if len(cleaned) > 3 else None

_WORK_SUMMARY_REQUEST = (
    "📝 *Resumen de jornada*\n\n"
    "Antes de registrar tu salida, comparte brevemente cómo ha ido el día:\n\n"
    "• Lo que has realizado\n"
    "• Notas o tareas para mañana\n"
    "• Cualquier anomalía o incidencia\n\n"
    "_Si prefieres no añadir nada escribe *sin resumen*._"
)

_LIVE_LOCATION_REQUEST = (
    "📍 Esta ubicación coincide *exactamente* con la de otro fichaje ya registrado.\n\n"
    "Para confirmar dónde estás ahora mismo, por favor comparte tu *ubicación en "
    "tiempo real*:\n"
    "📎 *Adjuntar* → *Ubicación* → *Compartir ubicación en tiempo real*.\n\n"
    "Será solo un momento para fijar tu posición correctamente. En cuanto la reciba "
    "te aviso y podrás dejar de compartir — no hace falta que la mantengas. 🙂"
)

_LIVE_LOCATION_REMINDER = (
    "🙏 Necesito tu *ubicación en tiempo real*, no una compartida normal.\n\n"
    "📎 *Adjuntar* → *Ubicación* → *Compartir ubicación en tiempo real*.\n"
    "En cuanto la reciba te aviso para que puedas dejar de compartir."
)

_LIVE_LOCATION_OK = (
    "✅ Ubicación en tiempo real recibida. Ya puedes *dejar de compartir*, ¡gracias!"
)

from app.services.project_service import (
    format_project_picker_message,
    list_active_projects,
    resolve_project_from_reply,
)


class WebhookService:
    def __init__(self, session: Session, tenant_id: UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        tenant = session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant no encontrado")
        self._tenant = tenant
        self._clock = ClockService(session, tenant_id=tenant_id)
        self._breaks = BreakService(session)
        self._leave = LeaveService(session)
        self._ollama = OllamaService(
            base_url=tenant.ollama_base_url,
            model=tenant.ollama_model,
            session=session,
            tenant_id=tenant_id,
        )
        self._gowa = GoWAService(session)
        self._settings = get_or_create_settings(session, tenant_id)

    async def _notify_incident_if_needed(self, phone: str) -> None:
        inc = self._clock.last_incident
        self._clock.last_incident = None
        if not inc or not should_notify_whatsapp(
            self._session, self._tenant_id, inc
        ):
            return
        try:
            await self._gowa.send_text(
                phone, whatsapp_message_for_incident(self._session, inc)
            )
        except Exception:
            pass

    async def process(self, payload: GoWAWebhookPayload) -> dict:
        if not payload.should_process():
            return {"ok": True, "action": "ignored_event", "event": payload.event}

        phone = payload.resolve_phone()

        if not phone:
            return {"ok": False, "error": "Teléfono no identificado en el webhook"}

        employee = self._clock.get_employee_by_phone(phone)
        if not employee:
            reply = (
                "No estás registrado en el sistema HRM. "
                "Contacta con Recursos Humanos."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "unknown_employee"}

        if should_send_welcome(employee):
            from app.services.employee_onboarding_service import (
                provision_inbound_signatures,
            )

            seed_inbound_documents(self._session, employee.id, self._tenant_id)
            provision_inbound_signatures(self._session, employee, self._tenant_id)
            welcome = build_welcome_message(
                self._session, employee, self._tenant.name
            )
            try:
                await self._gowa.send_text(phone, welcome)
                mark_welcome_sent(self._session, employee)
                self._session.commit()
            except Exception:
                pass

        # ── Timeout / cancelación de procesos pendientes (antes del legal check) ─
        message = payload.resolve_message()
        if message and message.is_text and message.plain_text:
            pending = get_pending(self._session, employee.id)
            if pending:
                from datetime import datetime, timedelta, timezone
                text = message.plain_text
                _is_justif = (pending.pending_meta or {}).get("awaiting_incident_justification")
                timeout = timedelta(minutes=60) if _is_justif else timedelta(minutes=3)
                created = pending.created_at
                if created:
                    created_aware = created.replace(tzinfo=timezone.utc) if created.tzinfo is None else created
                else:
                    created_aware = datetime.now(timezone.utc) - timeout - timedelta(seconds=1)
                expired = datetime.now(timezone.utc) - created_aware > timeout

                cancelled = is_negative_reply(text) or text.strip().lower() in (
                    "cancelar", "cancela", "cancel", "anular", "anula", "salir", "terminar", "dejar",
                )

                if expired or cancelled:
                    reason = "por inactividad" if expired else "a petición tuya"
                    clear_pending(self._session, employee.id)
                    from app.services.inbound_pending_service import clear_pending_upload
                    clear_pending_upload(self._session, employee.id)
                    self._session.commit()

                    reply = f"⏰ He cerrado la solicitud pendiente {reason}. ¿Necesitas algo más?"
                    try:
                        await self._gowa.send_text(phone, reply)
                    except Exception:
                        pass
                    return {"ok": True, "action": "pending_cancelled", "reason": reason}

        # ── Legal check ──────────────────────────────────────────────────────────
        try:
            from app.services.legal_service import create_whatsapp_token, employee_legal_status
            from app.config import get_settings as _get_settings
            _items, _all_ok = employee_legal_status(self._session, self._tenant_id, employee.id)
            if not _all_ok:
                _token = create_whatsapp_token(
                    self._session, employee_id=employee.id, tenant_id=self._tenant_id
                )
                self._session.commit()
                _base = _get_settings().public_app_url.rstrip("/")
                _link = f"{_base}/legal/{_token.token}"
                _pending_titles = [i.title for i in _items if i.is_required and not i.accepted]
                _msg = (
                    f"Antes de continuar, necesitas aceptar los textos legales requeridos.\n\n"
                    f"Documentos pendientes: {', '.join(_pending_titles)}.\n\n"
                    f"Accede al siguiente enlace (válido 5 min) para firmarlos:"
                )
                try:
                    await self._gowa.send_link(phone, _link, _msg)
                except Exception:
                    try:
                        await self._gowa.send_text(phone, f"{_msg}\n\n{_link}")
                    except Exception:
                        pass
                return {"ok": True, "action": "legal_pending"}
        except Exception:
            pass
        # ─────────────────────────────────────────────────────────────────────────

        message = payload.resolve_message()
        if message and message.is_location:
            return await self._handle_location(employee.id, phone, message)

        if message and message.is_media:
            return await self._handle_media(employee, phone, message)

        if message and message.is_text and message.plain_text:
            return await self._handle_text(
                employee, phone, message.plain_text, message.id
            )

        try:
            await self._gowa.send_text(
                phone,
                "Envía un mensaje de texto, una foto/PDF o comparte tu ubicación.",
            )
        except Exception:
            pass
        return {"ok": True, "action": "unsupported_message_type"}

    def _geo_hint(self) -> str:
        return format_geo_hint(self._settings.require_geolocation)

    def _is_open(self, employee_id: UUID) -> bool:
        return self._clock.get_open_clock(employee_id) is not None

    def _format_clock_reply(self, label: str, record, project_name: str | None = None) -> str:
        ts = record.salida_at if label == "SALIDA" else record.entrada_at
        if label == "SALIDA":
            lat, lng, addr = record.latitude_out, record.longitude_out, record.address_out
        else:
            lat, lng, addr = record.latitude, record.longitude, record.address
        return format_clock_registered(
            label,
            _to_spain(ts).strftime("%H:%M:%S"),
            project_name=project_name,
            latitude=lat,
            longitude=lng,
            address=addr,
        )

    async def _open_clock_with_project_flow(
        self,
        employee: Employee,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        address: str | None = None,
        whatsapp_message_id: str | None = None,
        picker_text: str | None = None,
    ) -> str:
        """Abre una jornada. Si hay proyectos activos, pide selección primero."""
        if not self._settings.require_project_on_clock_in:
            record = self._clock.open_clock(
                employee_id=employee.id,
                latitude=latitude,
                longitude=longitude,
                address=address,
                whatsapp_message_id=whatsapp_message_id,
                commit=False,
            )
            return self._format_clock_reply("ENTRADA", record)

        if picker_text:
            direct = resolve_project_from_reply(self._session, employee.company_id, picker_text)
            if not direct and not picker_text.strip().isdigit():
                # Fallback IA: el texto puede contener errores ortográficos o falta de acentos
                _projects = list_active_projects(self._session, employee.company_id)
                _ai_idx = await self._ollama.match_project(
                    picker_text, [p.name for p in _projects]
                )
                if _ai_idx is not None:
                    direct = _projects[_ai_idx]
            if direct:
                record = self._clock.open_clock(
                    employee_id=employee.id,
                    latitude=latitude,
                    longitude=longitude,
                    address=address,
                    whatsapp_message_id=whatsapp_message_id,
                    project_id=direct.id,
                    commit=False,
                )
                clear_pending(self._session, employee.id)
                return self._format_clock_reply("ENTRADA", record, direct.name)

        pending = get_pending(self._session, employee.id)
        if pending and not pending.pending_confirmation:
            project = resolve_project_from_reply(
                self._session, employee.company_id, picker_text or ""
            )
            if not project and picker_text and not picker_text.strip().isdigit():
                # Fallback IA cuando el empleado ya vio el selector y responde con un nombre
                _projects = list_active_projects(self._session, employee.company_id)
                _ai_idx = await self._ollama.match_project(
                    picker_text, [p.name for p in _projects]
                )
                if _ai_idx is not None:
                    project = _projects[_ai_idx]
            if not project:
                projects = list_active_projects(self._session, employee.company_id)
                return (
                    format_project_picker_message(projects, "ENTRADA")
                    + "\n\nNo he reconocido el proyecto. Responde con el número o nombre."
                )
            # Recover geocoded address stored when project picker was shown
            resolved_address = address or (pending.pending_meta or {}).get("address")
            record = self._clock.open_clock(
                employee_id=employee.id,
                latitude=pending.latitude,
                longitude=pending.longitude,
                address=resolved_address,
                whatsapp_message_id=pending.whatsapp_message_id or whatsapp_message_id,
                project_id=project.id,
                commit=False,
            )
            clear_pending(self._session, employee.id)
            return self._format_clock_reply("ENTRADA", record, project.name)

        projects = list_active_projects(self._session, employee.company_id)
        set_pending(
            self._session,
            employee_id=employee.id,
            record_type="entrada",
            latitude=latitude,
            longitude=longitude,
            whatsapp_message_id=whatsapp_message_id,
            pending_meta={"address": address} if address else None,
        )
        return format_project_picker_message(projects, "ENTRADA")

    def _request_work_summary(
        self,
        employee: Employee,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        address: str | None = None,
        whatsapp_message_id: str | None = None,
    ) -> str:
        """Guarda el estado 'awaiting_summary' y devuelve el mensaje de solicitud."""
        meta: dict = {"awaiting_summary": True}
        if address:
            meta["address"] = address
        set_pending(
            self._session,
            employee_id=employee.id,
            record_type="salida",
            latitude=latitude,
            longitude=longitude,
            whatsapp_message_id=whatsapp_message_id,
            pending_confirmation=False,
            pending_intent="fichar_salida",
            pending_meta=meta,
        )
        return _WORK_SUMMARY_REQUEST

    async def _handle_work_summary_response(
        self,
        employee: Employee,
        phone: str,
        text: str,
        message_id: str | None,
        pending,
    ) -> dict:
        """Recibe el resumen de jornada y ejecuta el cierre del fichaje."""
        if is_cancel_or_new_intent(text):
            clear_pending(self._session, employee.id)
            self._session.flush()
            self._ollama.profile_key = profile_key_for_employee(employee.role)
            intent_data = await self._ollama.extract_intent(
                text,
                employee=employee,
                tenant=self._tenant,
                clock_settings=self._settings,
            )
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="user",
                content=text,
            )
            self._session.flush()
            return await self._handle_stage(employee, phone, intent_data, text, message_id)

        work_summary = None if _RE_SKIP_SUMMARY.match(text) else text.strip()
        lat = pending.latitude
        lng = pending.longitude
        address = (pending.pending_meta or {}).get("address")
        clear_pending(self._session, employee.id)
        # La jornada puede haber superado el umbral de omisión mientras el empleado
        # redactaba el resumen → bloquear el cierre y abrir incidencia (misma operativa
        # que _clock_state_guard para fichar_salida).
        if self._clock.is_open_clock_expired(employee.id):
            self._create_expired_clock_incident(employee)
            last = self._clock.get_open_clock(employee.id)
            hora = _to_spain(last.entrada_at).strftime("%H:%M del %d/%m/%Y") if last else "?"
            reply = (
                f"⚠️ Tu jornada del {hora} lleva demasiadas horas abierta y no puede cerrarse.\n"
                "Se ha abierto una incidencia para que RRHH la regularice.\n\n"
                "Si quieres iniciar una *nueva jornada*, dímelo."
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "guard_expired_clock"}
        reply = self._close_clock(
            employee,
            work_summary=work_summary,
            whatsapp_message_id=message_id,
            latitude=lat,
            longitude=lng,
            address=address,
        )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
            await self._notify_incident_if_needed(phone)
        except Exception:
            pass
        return {"ok": True, "action": "work_summary_saved"}

    def _create_expired_clock_incident(self, employee: Employee) -> Incident | None:
        """Abre la incidencia de omisión de salida (regla configurable del tenant).

        Delega en `check_missing_clock_out`, que aplica el umbral `missing_clock_out_hours`
        y la config de justificación/WhatsApp del tenant, y evita duplicados.
        """
        return check_missing_clock_out(self._session, self._tenant_id, employee)

    def _close_clock(
        self,
        employee: Employee,
        work_summary: str | None = None,
        whatsapp_message_id: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        address: str | None = None,
    ) -> str:
        record = self._clock.close_clock(
            employee_id=employee.id,
            work_summary=work_summary,
            whatsapp_message_id=whatsapp_message_id,
            latitude=latitude,
            longitude=longitude,
            address=address,
            commit=False,
        )
        if not record:
            return "No tengo registrada una entrada abierta para ti. ¿Quizás ya fichaste la salida?"
        return self._format_clock_reply("SALIDA", record)

    def _mark_awaiting_live(self, employee_id: UUID, pending) -> None:
        """Marca que esperamos una ubicación en tiempo real antes de fichar.

        Conserva cualquier estado pendiente previo (confirmación, proyecto…) y
        solo añade la marca. Si no había pendiente, crea uno mínimo.
        """
        if pending is not None:
            meta = dict(pending.pending_meta or {})
            meta["awaiting_live_location"] = True
            pending.pending_meta = meta
            self._session.add(pending)
            self._session.flush()
        else:
            set_pending(
                self._session,
                employee_id=employee_id,
                record_type="entrada",
                pending_meta={"awaiting_live_location": True, "live_only": True},
            )

    def _clear_awaiting_live(self, employee_id: UUID, pending) -> None:
        """Quita la marca de espera de ubicación en tiempo real.

        Si el pendiente existía solo para esa espera, lo elimina por completo
        para no interferir con el flujo normal de fichaje.
        """
        if pending is None:
            return
        meta = dict(pending.pending_meta or {})
        live_only = meta.pop("live_only", False)
        meta.pop("awaiting_live_location", None)
        if (
            live_only
            and not pending.pending_confirmation
            and not pending.pending_intent
            and not meta
        ):
            clear_pending(self._session, employee_id)
        else:
            pending.pending_meta = meta or None
            self._session.add(pending)
            self._session.flush()

    async def _handle_location(
        self, employee_id: UUID, phone: str, message: GoWAMessage
    ) -> dict:
        loc = message.location
        if not loc:
            reply = (
                "📍 No he podido leer la ubicación.\n\n"
                "En WhatsApp: *clip* (📎) → *Ubicación* → *Enviar tu ubicación actual*.\n"
                "No uses solo texto; debe ser el adjunto de ubicación."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": False, "error": "Ubicación vacía"}

        # Validar coordenadas
        try:
            lat = float(loc.latitude)
            lng = float(loc.longitude)
        except (TypeError, ValueError):
            reply = (
                "📍 Las coordenadas recibidas no son válidas. "
                "Inténtalo de nuevo compartiendo tu ubicación desde WhatsApp."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": False, "error": "Coordenadas inválidas"}

        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            reply = (
                "📍 Las coordenadas GPS están fuera de rango. "
                "Asegúrate de compartir tu ubicación real desde WhatsApp."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": False, "error": "Coordenadas fuera de rango"}

        employee = self._session.get(Employee, employee_id)
        if not employee:
            return {"ok": False, "error": "Empleado no encontrado"}

        # ── Anti-reenvío de ubicación ────────────────────────────────────────
        # Una ubicación ESTÁTICA que coincide al milímetro con un fichaje ya
        # registrado (de este u otro empleado) pudo haberse reenviado. Pedimos
        # ubicación EN TIEMPO REAL, que WhatsApp no permite reenviar. Solo se
        # exige una vez: la marca `awaiting_live_location` se limpia al recibirla.
        is_live = bool(getattr(loc, "is_live", False))
        _pending_live = get_pending(self._session, employee_id)
        awaiting_live = bool(
            _pending_live
            and (_pending_live.pending_meta or {}).get("awaiting_live_location")
        )
        if awaiting_live:
            if not is_live:
                # Insiste: ya se le pidió tiempo real y vuelve a mandar estática.
                try:
                    await self._gowa.send_text(phone, _LIVE_LOCATION_REMINDER)
                except Exception:
                    pass
                return {"ok": True, "action": "await_live_location"}
            # Llegó la ubicación en tiempo real → continúa el fichaje con ella.
            self._clear_awaiting_live(employee_id, _pending_live)
            try:
                await self._gowa.send_text(phone, _LIVE_LOCATION_OK)
            except Exception:
                pass
        elif not is_live and self._clock.location_exists(lat, lng):
            self._mark_awaiting_live(employee_id, _pending_live)
            self._session.commit()
            try:
                await self._gowa.send_text(phone, _LIVE_LOCATION_REQUEST)
            except Exception:
                pass
            return {"ok": True, "action": "await_live_location"}
        # ─────────────────────────────────────────────────────────────────────

        # Reverse geocoding (best-effort, non-blocking)
        geo_address = await reverse_geocode(lat, lng)

        # Si hay confirmación pendiente por ubicación, ejecutar directamente
        pending = get_pending(self._session, employee_id)
        is_open = self._is_open(employee_id)
        # Fichaje caducado (>20 h): bloquear salida y tratar como nueva entrada
        is_expired = is_open and self._clock.is_open_clock_expired(employee_id)
        effective_open = is_open and not is_expired
        if pending and pending.pending_confirmation:
            action = "fichar_salida" if effective_open else "fichar_entrada"
            clock_type = "salida" if effective_open else "entrada"
            if not can_whatsapp_location_clock(
                self._session, employee, self._tenant_id, record_type=clock_type
            ):
                reply = denial_message(self._session, employee, self._tenant_id)
                clear_pending(self._session, employee_id)
                self._session.commit()
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "denied_location"}
            if effective_open:
                if self._settings.daily_summary_enabled:
                    reply = self._request_work_summary(
                        employee,
                        latitude=lat,
                        longitude=lng,
                        address=geo_address,
                        whatsapp_message_id=message.id,
                    )
                    self._session.commit()
                    try:
                        await self._gowa.send_text(phone, reply)
                    except Exception:
                        pass
                    return {"ok": True, "action": "await_work_summary"}
                reply = self._close_clock(
                    employee,
                    whatsapp_message_id=message.id,
                    latitude=lat,
                    longitude=lng,
                    address=geo_address,
                )
            else:
                if is_expired:
                    self._create_expired_clock_incident(employee)
                    self._session.flush()
                reply = await self._open_clock_with_project_flow(
                    employee,
                    latitude=lat,
                    longitude=lng,
                    address=geo_address,
                    whatsapp_message_id=message.id,
                )
            # _open_clock_with_project_flow may have set a project-selection pending
            # (pending_confirmation=False). If so, keep it so _handle_text can resolve it.
            after_pending = get_pending(self._session, employee_id)
            if not (after_pending and not after_pending.pending_confirmation):
                clear_pending(self._session, employee_id)
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply + self._geo_hint())
                await self._notify_incident_if_needed(phone)
            except Exception:
                pass
            return {"ok": True, "action": action}

        action = "fichar_salida" if effective_open else "fichar_entrada"
        clock_type = "salida" if effective_open else "entrada"
        if not can_whatsapp_location_clock(
            self._session, employee, self._tenant_id, record_type=clock_type
        ):
            reply = denial_message(self._session, employee, self._tenant_id)
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "denied_location"}

        if effective_open:
            if self._settings.daily_summary_enabled:
                reply = self._request_work_summary(
                    employee,
                    latitude=lat,
                    longitude=lng,
                    address=geo_address,
                    whatsapp_message_id=message.id,
                )
                self._session.commit()
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "await_work_summary"}
            reply = self._close_clock(
                employee,
                whatsapp_message_id=message.id,
                latitude=lat,
                longitude=lng,
                address=geo_address,
            )
        else:
            if is_expired:
                self._create_expired_clock_incident(employee)
                self._session.flush()
            reply = await self._open_clock_with_project_flow(
                employee,
                latitude=lat,
                longitude=lng,
                address=geo_address,
                whatsapp_message_id=message.id,
            )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply + self._geo_hint())
            await self._notify_incident_if_needed(phone)
        except Exception:
            pass
        return {"ok": True, "action": action}

    async def _handle_media(
        self, employee: Employee, phone: str, message: GoWAMessage
    ) -> dict:
        path_str = message.media_path
        if not path_str:
            reply = "No he podido leer el archivo. Vuelve a enviarlo, por favor."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "media_no_path"}

        path = Path(path_str)
        # goWA puede enviar solo el nombre del archivo (sin ruta) o ruta completa
        if not path.is_file():
            # Intentar en el directorio de storages de goWA (volumen compartido)
            alt_path = Path("/app/storages") / path.name
            if alt_path.is_file():
                path = alt_path
        if not path.is_file():
            # Intentar descargar desde goWA vía HTTP (statics/media/)
            data = await self._gowa.download_media(path_str)
            if data:
                # Guardar el archivo descargado en uploads para procesarlo
                from app.services.document_service import store_upload_file
                UPLOAD_DIR = Path("/app/uploads")
                filename = message.file_name or path.name
                saved_path, _ = store_upload_file(UPLOAD_DIR, filename, data)
                path = Path(saved_path)
        if not path.is_file():
            reply = (
                "Archivo no disponible en el servidor. "
                "Prueba a reenviar la imagen o el PDF."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "media_not_found"}

        if not can_whatsapp_inbound_media(
            self._session, employee, self._tenant_id, self._settings
        ):
            reply = denial_message(self._session, employee, self._tenant_id)
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "denied_media"}

        file_bytes = path.read_bytes()
        filename = message.file_name or path.name

        # ── Adjunto para incidencia pendiente ──────────────────────────────────
        pending = get_pending(self._session, employee.id)
        if pending and (pending.pending_meta or {}).get("awaiting_incident_file"):
            incident_id_str = (pending.pending_meta or {}).get("incident_id")
            if incident_id_str:
                from uuid import UUID as _UUID
                from app.services.document_service import store_upload_file as _store
                from app.services.incident_service import add_note as _add_note
                UPLOAD_DIR = Path("/app/uploads")
                saved_path, safe_name = _store(UPLOAD_DIR, filename, file_bytes)
                rel = saved_path.replace("/app/uploads/", "/uploads/")
                try:
                    _add_note(
                        self._session,
                        incident_id=_UUID(incident_id_str),
                        content=f"📎 Adjunto enviado por WhatsApp: [{safe_name}]({rel})",
                        author_name=employee.full_name,
                    )
                except Exception:
                    pass
                # Limpiar estado pendiente
                pending.pending_meta = {k: v for k, v in (pending.pending_meta or {}).items()
                                        if k not in ("awaiting_incident_file", "incident_id")}
                pending.pending_confirmation = False
                pending.pending_intent = None
                self._session.add(pending)
                self._session.commit()
                reply = (
                    f"✅ Archivo *{safe_name}* adjuntado a tu incidencia.\n"
                    "¿Quieres adjuntar otro archivo? Envíalo ahora o escribe _listo_ para terminar."
                )
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "incident_file_attached"}

        file_pending = pending_file_documents(self._session, employee.id)
        if len(file_pending) > 1:
            set_pending_upload(
                self._session,
                employee_id=employee.id,
                file_bytes=file_bytes,
                filename=filename,
                whatsapp_message_id=message.id,
            )
            picker_rows = [
                type(
                    "Row",
                    (),
                    {
                        "document_name": inbound_name(
                            self._session, r.document_code
                        )
                    },
                )()
                for r in file_pending
            ]
            reply = format_inbound_document_picker(picker_rows)
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "inbound_pick_document"}

        if len(file_pending) == 1:
            ok, reply = receive_inbound_file(
                self._session,
                employee,
                tenant_id=self._tenant_id,
                file_bytes=file_bytes,
                filename=filename,
                document_code=file_pending[0].document_code,
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": ok, "action": "inbound_document" if ok else "inbound_rejected"}

        # ── NO hay documentos pendientes: preguntar si es incidencia o permiso ──
        set_pending_upload(
            self._session,
            employee_id=employee.id,
            file_bytes=file_bytes,
            filename=filename,
            whatsapp_message_id=message.id,
        )
        set_pending(
            self._session,
            employee_id=employee.id,
            record_type="media",
            whatsapp_message_id=message.id,
            pending_confirmation=False,
            pending_intent="media_classify",
        )
        reply = (
            f"📎 He recibido tu archivo *{filename}*.\n\n"
            "¿Para qué es?\n"
            "1️⃣ *Incidencia* — reportar un problema, retraso, avería…\n"
            "2️⃣ *Permiso* — solicitar vacaciones, días libres, baja…\n\n"
            "Responde *1* o *2*, o escribe _incidencia_ o _permiso_."
        )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
        except Exception:
            pass
        return {"ok": True, "action": "media_classify"}

    async def _handle_text(
        self,
        employee: Employee,
        phone: str,
        text: str,
        message_id: str | None,
    ) -> dict:
        # ── Timeout / cancelación de procesos pendientes ──────────────────────
        pending = get_pending(self._session, employee.id)
        if pending:
            from datetime import datetime, timedelta, timezone
            # Justificación de incidencia: timeout de 60 min en lugar de 3
            is_justification_pending = (pending.pending_meta or {}).get("awaiting_incident_justification")
            timeout = timedelta(minutes=60) if is_justification_pending else timedelta(minutes=3)
            if pending.created_at:
                # Convertir naive a aware (asumimos UTC)
                created = pending.created_at.replace(tzinfo=timezone.utc) if pending.created_at.tzinfo is None else pending.created_at
            else:
                created = datetime.now(timezone.utc) - timeout - timedelta(seconds=1)
            expired = datetime.now(timezone.utc) - created > timeout

            # Cancelación explícita por palabra clave
            cancelled = is_negative_reply(text) or text.strip().lower() in (
                "cancelar", "cancela", "cancel", "anular", "anula", "salir", "terminar", "dejar",
            )

            if expired or cancelled:
                reason = "por inactividad" if expired else "a petición tuya"
                clear_pending(self._session, employee.id)
                # También limpiar uploads pendientes
                from app.services.inbound_pending_service import clear_pending_upload
                clear_pending_upload(self._session, employee.id)
                self._session.commit()

                reply = f"⏰ He cerrado la solicitud pendiente {reason}. ¿Necesitas algo más?"
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass

                # Si fue cancelación explícita (no timeout), procesar el nuevo texto
                if cancelled and not expired:
                    # Procesar el texto como nueva intención
                    self._ollama.profile_key = profile_key_for_employee(employee.role)
                    intent_data = await self._ollama.extract_intent(
                        text,
                        employee=employee,
                        tenant=self._tenant,
                        clock_settings=self._settings,
                    )
                    append_message(
                        self._session,
                        tenant_id=self._tenant_id,
                        employee_id=employee.id,
                        role="user",
                        content=text,
                    )
                    self._session.flush()
                    return await self._handle_stage(employee, phone, intent_data, text, message_id)

                return {"ok": True, "action": "pending_cancelled", "reason": reason}

        # 0. Comando debug: "${prompt}" -> devuelve el prompt COMPLETO (system + historial) que se envía a la IA
        if text.strip() == "${prompt}":
            import json
            system_prompt = build_system_prompt(
                self._session,
                employee=employee,
                tenant=self._tenant,
                settings=self._settings,
                tenant_id=self._tenant_id,
            )
            history = get_history_for_ollama(
                self._session,
                self._tenant_id,
                employee.id,
            )
            # Reconstruir el array messages que se enviaría a Ollama
            full_messages = [
                {"role": "system", "content": system_prompt},
            ]
            full_messages.extend(history)
            full_messages.append({"role": "user", "content": text.strip()})
            payload_preview = json.dumps(full_messages, ensure_ascii=False, indent=2)

            reply = (
                f"*PROMPT COMPLETO ENVIADO A OLLAMA:*\n"
                f"Modelo: `{self._tenant.ollama_model}`\n"
                f"Mensajes en historial: {len(history)}\n"
                f"Total mensajes enviados: {len(full_messages)}\n\n"
                f"```json\n{payload_preview[:3500]}\n```"
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "debug_prompt"}

        # 0. Flujo de clasificación de archivo multimedia (incidencia / permiso)
        pending = get_pending(self._session, employee.id)
        if pending and pending.pending_intent and pending.pending_intent.startswith("media_"):
            return await self._handle_media_classification(
                employee, phone, text, message_id, pending
            )

        # 0b. Esperando adjunto para incidencia — "listo" / "no" cancela la espera
        pending = get_pending(self._session, employee.id)
        if pending and (pending.pending_meta or {}).get("awaiting_incident_file"):
            normalized = text.strip().lower()
            if normalized in ("listo", "no", "nada", "terminar", "fin", "no gracias", "ya está"):
                pending.pending_meta = {k: v for k, v in (pending.pending_meta or {}).items()
                                        if k not in ("awaiting_incident_file", "incident_id")}
                pending.pending_confirmation = False
                pending.pending_intent = None
                self._session.add(pending)
                self._session.commit()
                reply = "De acuerdo, incidencia registrada sin adjuntos. 👍"
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "incident_file_skipped"}
            # Cualquier otro texto: recordar que esperamos un archivo
            reply = (
                "📎 Envía el documento o foto como adjunto en este chat, "
                "o escribe _listo_ para terminar sin adjuntar."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_file_awaiting_reminder"}

        # 1. Pendiente de subir documento
        upload_pending = get_pending_upload(self._session, employee.id)
        if upload_pending:
            return await self._handle_inbound_document_pick(employee, phone, text)

        # 1b. Pendiente de justificación por WhatsApp (paso 2: el empleado escribe el texto)
        pending = get_pending(self._session, employee.id)
        if pending and (pending.pending_meta or {}).get("awaiting_incident_justification"):
            return await self._complete_whatsapp_justification(employee, phone, text, pending)

        # 1c. Detección de "justificar [texto]" — sin necesidad de estado previo
        _jtext = _extract_justification_text(text)
        if _jtext is not None:
            return await self._handle_whatsapp_justification(employee, phone, _jtext)

        # 2. Pendiente de resumen de trabajo al fichar salida
        pending = get_pending(self._session, employee.id)
        if pending and (pending.pending_meta or {}).get("awaiting_summary"):
            return await self._handle_work_summary_response(
                employee, phone, text, message_id, pending
            )

        # 2b. Pendiente de aprobación de vacaciones (responsable eligió de una lista)
        pending = get_pending(self._session, employee.id)
        if pending and (pending.pending_meta or {}).get("awaiting_leave_approval"):
            return await self._handle_leave_approval_response(
                employee, phone, text, pending
            )

        # 3. Pendiente de confirmación sí/no
        if pending and pending.pending_confirmation:
            return await self._handle_confirmation_response(
                employee, phone, text, message_id, pending
            )

        # 4. Pendiente de selección de proyecto (sin confirmación pendiente)
        if self._settings.require_project_on_clock_in and pending:
            return await self._handle_project_selection(
                employee, phone, text, message_id, pending
            )

        # 5. Ollama como orquestador: decide stage (ask/confirm/execute)
        self._ollama.profile_key = profile_key_for_employee(employee.role)
        intent_data = await self._ollama.extract_intent(
            text,
            employee=employee,
            tenant=self._tenant,
            clock_settings=self._settings,
        )

        append_message(
            self._session,
            tenant_id=self._tenant_id,
            employee_id=employee.id,
            role="user",
            content=text,
        )
        self._session.flush()

        return await self._handle_stage(employee, phone, intent_data, text, message_id)

    async def _handle_whatsapp_justification(
        self,
        employee: Employee,
        phone: str,
        justification_text: str,
    ) -> dict:
        """Gestiona el flujo de justificación de incidencia desde WhatsApp."""
        incidents = get_pending_justification_incidents(self._session, employee.id)

        if not incidents:
            reply = "No tienes incidencias pendientes de justificación en este momento."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_none"}

        # Si no hay texto aún, preguntar cuál es la justificación
        if not justification_text:
            if len(incidents) == 1:
                inc = incidents[0]
                # Guardar pending state: awaiting_incident_justification
                set_pending(
                    self._session,
                    employee_id=employee.id,
                    pending_meta={
                        "awaiting_incident_justification": True,
                        "incident_id": str(inc.id),
                    },
                )
                self._session.commit()
                reply = (
                    f"📝 Incidencia: *{inc.title}*\n"
                    f"Escribe tu justificación y te la registraré."
                )
            else:
                lines = ["Tienes varias incidencias pendientes. Escribe el número y tu justificación:"]
                for i, inc in enumerate(incidents, 1):
                    fecha = inc.incident_date.strftime("%d/%m/%Y") if inc.incident_date else "—"
                    lines.append(f"*{i}.* {inc.title} ({fecha})")
                lines.append("")
                lines.append("Ejemplo: _justificar 1: Llegué tarde por un retraso del metro_")
                reply = "\n".join(lines)
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_asked"}

        # Detectar si viene con número de selección: "1: [texto]" o "1 [texto]"
        _num_match = _re.match(r"^(\d+)\s*[:\-]?\s*(.+)$", justification_text, _re.DOTALL)
        if _num_match and len(incidents) > 1:
            idx = int(_num_match.group(1)) - 1
            if 0 <= idx < len(incidents):
                selected_incident = incidents[idx]
                justification_text = _num_match.group(2).strip()
            else:
                reply = f"Número fuera de rango. Tienes {len(incidents)} incidencias. Indica 1–{len(incidents)}."
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "incident_justification_bad_index"}
        else:
            # Una sola incidencia o texto sin número: usar la más reciente
            selected_incident = incidents[0]
            # Si hay varias y no especificó número, avisar que se usó la primera
            if len(incidents) > 1:
                justification_text = justification_text.lstrip("0123456789: -")

        if len(justification_text) < 3:
            reply = "La justificación es demasiado corta. Escribe «justificar» seguido de tu explicación."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_too_short"}

        submit_employee_justification(self._session, selected_incident.public_token, justification_text)
        add_note(
            self._session,
            incident_id=selected_incident.id,
            content=f"📱 Justificación recibida por WhatsApp: {justification_text[:500]}",
            author_name="Sistema",
        )
        self._session.commit()

        reply = (
            f"✅ Justificación registrada para «{selected_incident.title}».\n"
            f"RRHH la revisará y resolverá la incidencia. Gracias."
        )
        try:
            await self._gowa.send_text(phone, reply)
        except Exception:
            pass
        return {"ok": True, "action": "incident_justified_whatsapp", "incident_id": str(selected_incident.id)}

    async def _complete_whatsapp_justification(
        self,
        employee: Employee,
        phone: str,
        text: str,
        pending,
    ) -> dict:
        """Paso 2 del flujo de justificación: el empleado escribe el texto después de que el sistema lo pidió."""
        if is_negative_reply(text) or text.strip().lower() in ("cancelar", "no", "nada"):
            from app.services.clock_pending_service import clear_pending as _clear
            _clear(self._session, employee.id)
            self._session.commit()
            reply = "De acuerdo, justificación cancelada."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_cancelled"}

        if len(text.strip()) < 3:
            reply = "La justificación es demasiado corta. Escribe tu explicación o «cancelar» para salir."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_too_short"}

        from uuid import UUID as _UUID
        incident_id_str = (pending.pending_meta or {}).get("incident_id")
        from app.services.clock_pending_service import clear_pending as _clear
        _clear(self._session, employee.id)

        if not incident_id_str:
            reply = "No encontré la incidencia asociada. Intenta de nuevo con «justificar [texto]»."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_missing"}

        from app.models.incident import Incident as _Incident
        inc = self._session.get(_Incident, _UUID(incident_id_str))
        if not inc or inc.employee_id != employee.id:
            reply = "No encontré la incidencia. Intenta de nuevo."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "incident_justification_not_found"}

        submit_employee_justification(self._session, inc.public_token, text.strip())
        add_note(
            self._session,
            incident_id=inc.id,
            content=f"📱 Justificación recibida por WhatsApp: {text.strip()[:500]}",
            author_name="Sistema",
        )
        self._session.commit()

        reply = (
            f"✅ Justificación registrada para «{inc.title}».\n"
            f"RRHH la revisará y resolverá la incidencia. Gracias."
        )
        try:
            await self._gowa.send_text(phone, reply)
        except Exception:
            pass
        return {"ok": True, "action": "incident_justified_whatsapp", "incident_id": str(inc.id)}

    async def _clock_state_guard(
        self,
        employee: Employee,
        phone: str,
        intent_code: str,
    ) -> dict | None:
        """Valida que el fichaje pedido sea coherente con el estado real de la jornada.

        Se ejecuta ANTES de decidir ask/confirm/execute, para no pedir confirmaciones
        imposibles ni dejar que la IA improvise ofertas contradictorias. Devuelve un
        resultado terminal (ya ha respondido) si hay incoherencia; None si puede continuar.
        """
        if intent_code not in ("fichar_entrada", "fichar_salida"):
            return None

        is_open = self._is_open(employee.id)
        is_expired = is_open and self._clock.is_open_clock_expired(employee.id)

        async def _respond(reply: str, action: str) -> dict:
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code=action,
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": action}

        # Jornada caducada (supera el umbral de omisión de salida) + intento de salida →
        # bloquear y abrir incidencia para que RRHH la regularice.
        if is_expired and intent_code == "fichar_salida":
            self._create_expired_clock_incident(employee)
            last = self._clock.get_open_clock(employee.id)
            hora = _to_spain(last.entrada_at).strftime("%H:%M del %d/%m/%Y") if last else "?"
            return await _respond(
                f"⚠️ Tu jornada del {hora} lleva demasiadas horas abierta y no puede cerrarse.\n"
                "Se ha abierto una incidencia para que RRHH la regularice.\n\n"
                "Si quieres iniciar una *nueva jornada*, dímelo.",
                "guard_expired_clock",
            )

        # Entrada cuando ya hay jornada abierta (no caducada)
        if intent_code == "fichar_entrada" and is_open and not is_expired:
            last = self._clock.get_open_clock(employee.id)
            hora = _to_spain(last.entrada_at).strftime("%H:%M") if last else "?"
            return await _respond(
                f"Ya tienes una jornada abierta desde las *{hora}*.\n"
                "Si quieres fichar la *salida*, dímelo.",
                "guard_already_open",
            )

        # Salida sin ninguna jornada abierta
        if intent_code == "fichar_salida" and not is_open:
            return await _respond(
                "No tienes ninguna jornada abierta. Si quieres fichar la *entrada*, dímelo.",
                "guard_not_open",
            )

        return None

    async def _handle_stage(
        self,
        employee: Employee,
        phone: str,
        intent_data: OllamaIntentResponse,
        raw_text: str,
        message_id: str | None,
    ) -> dict:
        """Orquestador conversacional: sigue la decisión de Ollama (ask/confirm/execute)."""
        stage = intent_data.stage
        intent_code = intent_data.intent
        ollama_message = (intent_data.message or "").strip()
        # Descartar el mensaje si la IA repite textualmente el input del usuario
        if ollama_message and ollama_message.lower() == raw_text.strip().lower():
            ollama_message = ""

        # Verificar permisos para la intención (excepto stage=ask que es solo conversación)
        if stage in ("confirm", "execute") and intent_code != "desconocido":
            if not is_whatsapp_action_allowed(
                self._session, employee, self._tenant_id, intent_code
            ):
                reply = denial_message(self._session, employee, self._tenant_id)
                append_message(
                    self._session,
                    tenant_id=self._tenant_id,
                    employee_id=employee.id,
                    role="assistant",
                    content=reply[:_REPLY_MAX],
                    intent_code="denied",
                )
                self._session.commit()
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "denied"}

        # Validación de estado de jornada — ANTES de ask/confirm/execute.
        # Garantiza una respuesta determinista (no pedimos confirmar fichajes imposibles
        # ni dejamos que la IA improvise ofertas que contradicen el estado real).
        if intent_code in ("fichar_entrada", "fichar_salida"):
            _pend = get_pending(self._session, employee.id)
            if _pend and _pend.pending_confirmation:
                clear_pending(self._session, employee.id)
            guard_result = await self._clock_state_guard(employee, phone, intent_code)
            if guard_result is not None:
                return guard_result

        if stage == "ask":
            # Seguir preguntando: enviar el mensaje de Ollama y esperar
            reply = ollama_message or format_conversational_help(
                [ACTION_LABELS.get(c, c) for c in list_whatsapp_actions_for_employee(
                    self._session, employee, self._tenant_id
                )],
                employee_name=employee.full_name,
            )
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="ask",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "ask", "reply": reply}

        if stage == "confirm":
            # Guardar intención pendiente de confirmación y preguntar sí/no
            _record_type = "salida" if intent_code == "fichar_salida" else "entrada"
            if intent_code == "reportar_incidencia":
                _record_type = "incidencia"
            elif intent_code == "solicitar_permiso":
                _record_type = "permiso"
            # Para reportar_incidencia/solicitar_permiso: guardar entities de la IA
            _meta = None
            if intent_code in ("reportar_incidencia", "solicitar_permiso"):
                _meta = dict(intent_data.entities) if intent_data.entities else {}
            if intent_code == "reportar_incidencia":
                if not _meta.get("title") and not _meta.get("titulo"):
                    _meta["_ai_summary"] = ollama_message
                    _meta["_original_text"] = raw_text
            set_pending(
                self._session,
                employee_id=employee.id,
                record_type=_record_type,
                whatsapp_message_id=message_id,
                pending_confirmation=True,
                pending_intent=intent_code,
                pending_meta=_meta,
            )
            reply = ollama_message or build_confirmation_message(
                intent_code, employee.full_name
            )
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="pending_confirmation",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "confirm", "intent": intent_code}

        # stage == "execute"
        if intent_code == "desconocido":
            # No debería pasar, pero por si acaso: preguntar
            reply = ollama_message or format_conversational_help(
                [ACTION_LABELS.get(c, c) for c in list_whatsapp_actions_for_employee(
                    self._session, employee, self._tenant_id
                )],
                employee_name=employee.full_name,
            )
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="ask",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "ask"}

        # Limpiar pending si existía
        pending = get_pending(self._session, employee.id)
        if pending and pending.pending_confirmation:
            clear_pending(self._session, employee.id)

        # Los guards de coherencia (jornada ya abierta / sin abrir / caducada+salida) ya se
        # aplicaron al inicio de _handle_stage. Aquí solo queda el caso no bloqueante:
        # entrada con jornada caducada → crear incidencia antes de abrir la nueva jornada.
        if (
            intent_code == "fichar_entrada"
            and self._is_open(employee.id)
            and self._clock.is_open_clock_expired(employee.id)
        ):
            self._create_expired_clock_incident(employee)
            self._session.flush()

        # Si require_geolocation y es un fichaje de texto → pedir ubicación primero
        if (
            intent_code in ("fichar_entrada", "fichar_salida")
            and self._settings.require_geolocation
        ):
            _record_type = "salida" if intent_code == "fichar_salida" else "entrada"
            set_pending(
                self._session,
                employee_id=employee.id,
                record_type=_record_type,
                whatsapp_message_id=message_id,
                pending_confirmation=True,
                pending_intent=intent_code,
            )
            reply = format_geo_request()
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="await_location",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "await_location"}

        reply = await self._execute_intent(
            employee, intent_data, raw_text, message_id
        )
        if intent_code in ("fichar_entrada", "fichar_salida"):
            reply += self._geo_hint()

        # Para execute el sistema ya genera la respuesta; solo usar mensaje de Ollama si no hay reply del sistema
        if ollama_message and not reply.strip():
            reply = ollama_message

        append_message(
            self._session,
            tenant_id=self._tenant_id,
            employee_id=employee.id,
            role="assistant",
            content=reply[:_REPLY_MAX],
            intent_code=intent_code,
        )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
            if intent_code in ("fichar_entrada", "fichar_salida"):
                await self._notify_incident_if_needed(phone)
        except Exception:
            pass
        return {"ok": True, "action": intent_code, "reply": reply}

    async def _handle_confirmation_response(
        self,
        employee: Employee,
        phone: str,
        text: str,
        message_id: str | None,
        pending,
    ) -> dict:
        """Procesa la respuesta a una confirmación pendiente — siempre pasa por el orquestador."""
        intent_code = pending.pending_intent or "fichar_entrada"

        append_message(
            self._session,
            tenant_id=self._tenant_id,
            employee_id=employee.id,
            role="user",
            content=text,
        )

        # Siempre pasar por el orquestador; el historial le da el contexto de la confirmación pendiente
        self._ollama.profile_key = profile_key_for_employee(employee.role)
        intent_data = await self._ollama.extract_intent(
            text,
            employee=employee,
            tenant=self._tenant,
            clock_settings=self._settings,
        )

        # Si el orquestador dice execute pero no sabe el intent (desconocido),
        # o si no dice execute pero el texto es claramente afirmativo →
        # forzar la ejecución de la intención pendiente
        if (
            intent_data.stage != "execute" or intent_data.intent == "desconocido"
        ) and is_affirmative_reply(text):
            intent_data = OllamaIntentResponse(
                stage="execute",
                intent=intent_code,
                confidence=1.0,
                message="",
                entities=pending.pending_meta or {},
            )

        # Para incidencias confirmadas: restaurar entities del mensaje original
        # (el mensaje de confirmación no contiene la descripción de la incidencia)
        if (
            intent_data.stage == "execute"
            and intent_data.intent == "reportar_incidencia"
            and pending.pending_meta
        ):
            merged = dict(intent_data.entities or {})
            for _k in ("title", "titulo", "description", "descripcion", "motivo", "_ai_summary", "_original_text"):
                if pending.pending_meta.get(_k) and not merged.get(_k):
                    merged[_k] = pending.pending_meta[_k]
            intent_data = OllamaIntentResponse(
                stage=intent_data.stage,
                intent=intent_data.intent,
                confidence=intent_data.confidence,
                message=intent_data.message,
                entities=merged,
            )

        # Si el orquestador no va a ejecutar, limpiar el pending para evitar loops
        if intent_data.stage != "execute":
            clear_pending(self._session, employee.id)

        return await self._handle_stage(employee, phone, intent_data, text, message_id)

    async def _handle_project_selection(
        self,
        employee: Employee,
        phone: str,
        text: str,
        message_id: str | None,
        pending,
    ) -> dict:
        """Procesa la selección de proyecto para un fichaje pendiente."""
        # Si el texto parece una nueva intención (no selección de proyecto), cancelar y redirigir
        if is_cancel_or_new_intent(text):
            clear_pending(self._session, employee.id)
            self._session.flush()
            self._ollama.profile_key = profile_key_for_employee(employee.role)
            intent_data = await self._ollama.extract_intent(
                text,
                employee=employee,
                tenant=self._tenant,
                clock_settings=self._settings,
            )
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="user",
                content=text,
            )
            self._session.flush()
            return await self._handle_stage(employee, phone, intent_data, text, message_id)

        # pending.record_type es "entrada" o "salida" (string en ClockPendingFichaje)
        is_salida = pending.record_type == "salida"
        code = "fichar_salida" if is_salida else "fichar_entrada"
        if not is_whatsapp_action_allowed(
            self._session, employee, self._tenant_id, code
        ):
            reply = denial_message(self._session, employee, self._tenant_id)
            clear_pending(self._session, employee.id)
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "denied_project"}
        if is_salida:
            if self._settings.daily_summary_enabled:
                reply = self._request_work_summary(
                    employee,
                    latitude=pending.latitude,
                    longitude=pending.longitude,
                    whatsapp_message_id=message_id,
                )
            else:
                reply = self._close_clock(employee, whatsapp_message_id=message_id)
        else:
            _pending_address = (pending.pending_meta or {}).get("address")
            reply = await self._open_clock_with_project_flow(
                employee,
                latitude=pending.latitude,
                longitude=pending.longitude,
                address=_pending_address,
                whatsapp_message_id=pending.whatsapp_message_id or message_id,
                picker_text=text,
            )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
            await self._notify_incident_if_needed(phone)
        except Exception:
            pass
        return {"ok": True, "action": "select_project"}

    async def _handle_inbound_document_pick(
        self,
        employee: Employee,
        phone: str,
        text: str,
    ) -> dict:
        """Procesa la selección de tipo de documento para un archivo pendiente."""
        doc_row = resolve_document_from_reply(self._session, employee.id, text)
        if not doc_row:
            file_pending = pending_file_documents(self._session, employee.id)
            picker_rows = [
                type(
                    "Row",
                    (),
                    {"document_name": inbound_name(self._session, r.document_code)},
                )()
                for r in file_pending
            ]
            reply = format_inbound_document_picker(picker_rows)
            reply += "\n\n_No he reconocido tu respuesta. Indica el número o nombre._"
        else:
            ok, reply = complete_pending_upload(
                self._session,
                employee,
                tenant_id=self._tenant_id,
                document_code=doc_row.document_code,
            )
            if not ok:
                pass
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
        except Exception:
            pass
        return {"ok": True, "action": "inbound_document_assigned"}

    async def _handle_media_classification(
        self,
        employee: Employee,
        phone: str,
        text: str,
        message_id: str | None,
        pending,
    ) -> dict:
        """Flujo: archivo recibido sin docs pendientes → ¿incidencia o permiso? → crear."""
        from app.services.incident_service import create_incident
        from app.services.inbound_pending_service import clear_pending_upload, get_pending_upload
        from app.services.document_service import create_delivery, store_upload_file
        from pathlib import Path as _Path

        UPLOAD_DIR = _Path("/app/uploads")
        intent = pending.pending_intent
        t = text.strip().lower()

        # Registrar mensaje del usuario en el historial
        append_message(
            self._session,
            tenant_id=self._tenant_id,
            employee_id=employee.id,
            role="user",
            content=text,
        )

        if intent == "media_classify":
            # Paso 1: ¿incidencia o permiso?
            if t in ("cancelar", "cancel", "no", "nada"):
                clear_pending_upload(self._session, employee.id)
                clear_pending(self._session, employee.id)
                self._session.commit()
                reply = "👍 De acuerdo, he descartado el archivo. Si necesitas algo más, aquí estoy."
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "media_cancelled"}
            if t in ("1", "incidencia", "reportar", "reportar incidencia", "problema", "avería", "retraso"):
                set_pending(
                    self._session,
                    employee_id=employee.id,
                    record_type="media",
                    pending_intent="media_incidencia_title",
                )
                reply = (
                    "✍️ Describe la incidencia en una frase:\n"
                    "ej: _Llegada tarde por tráfico_, _Avería en el vehículo_, _Error en el fichaje_…"
                )
            elif t in ("2", "permiso", "solicitar permiso", "baja", "vacaciones", "días libres", "dias libres"):
                set_pending(
                    self._session,
                    employee_id=employee.id,
                    record_type="media",
                    pending_intent="media_permiso_dates",
                )
                reply = (
                    "📅 Indica las fechas del permiso.\n"
                    "ej: _del 5 al 10 de junio_ o _10/06 - 15/06_"
                )
            else:
                reply = "No he entendido. Responde *1* para incidencia o *2* para permiso."

            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": intent}

        elif intent == "media_incidencia_title":
            # Paso 2: crear incidencia con el archivo adjunto
            upload = get_pending_upload(self._session, employee.id)
            title = text.strip()[:300] or "Incidencia reportada por WhatsApp"

            # Mover archivo de pending a uploads definitivo
            doc_path = None
            doc_name = None
            if upload and _Path(upload.file_path).is_file():
                data = _Path(upload.file_path).read_bytes()
                doc_path, doc_name = store_upload_file(UPLOAD_DIR, upload.filename, data)

            incident = create_incident(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                category="fichaje",
                incident_type="manual",
                title=title,
                description=f"Archivo adjunto: {doc_name or upload.filename if upload else 'N/A'}",
                source="whatsapp",
                created_by_id=employee.id,
            )

            # Vincular archivo como document_delivery
            if doc_path and doc_name:
                create_delivery(
                    self._session,
                    tenant_id=self._tenant_id,
                    company_id=None,
                    employee_id=employee.id,
                    document_type_id=None,
                    document_type_code="otro",
                    file_path=doc_path,
                    file_name=doc_name,
                    title=f"Incidencia: {title}",
                    requires_acknowledgment=False,
                )

            clear_pending_upload(self._session, employee.id)
            clear_pending(self._session, employee.id)
            self._session.commit()

            reply = f"✅ Incidencia registrada: *{incident.title}*\nPuedes consultarla en el panel de RRHH."
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "media_incidencia_created"}

        elif intent == "media_permiso_dates":
            # Paso 2: parsear fechas y crear solicitud de permiso
            from datetime import date as _date
            from app.models.models import LeaveRequest

            upload = get_pending_upload(self._session, employee.id)
            start_date, end_date = self._parse_leave_dates(text)

            if not start_date or not end_date:
                reply = (
                    "No he podido entender las fechas. Intenta de nuevo:\n"
                    "ej: _del 5 al 10 de junio_ o _10/06/2025 - 15/06/2025_"
                )
                self._session.commit()
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "media_permiso_dates_retry"}

            days = self._leave.count_business_days(start_date, end_date)

            # Mover archivo de pending a uploads definitivo
            doc_path = None
            doc_name = None
            if upload and _Path(upload.file_path).is_file():
                data = _Path(upload.file_path).read_bytes()
                doc_path, doc_name = store_upload_file(UPLOAD_DIR, upload.filename, data)

            leave_req = LeaveRequest(
                employee_id=employee.id,
                start_date=start_date,
                end_date=end_date,
                days_requested=days,
                status="pending",
                reason=f"Solicitado por WhatsApp. Archivo: {doc_name or upload.filename if upload else 'N/A'}",
                supervisor_id=employee.supervisor_id,
                raw_message=text,
            )
            self._session.add(leave_req)
            self._session.flush()

            if doc_path and doc_name:
                create_delivery(
                    self._session,
                    tenant_id=self._tenant_id,
                    company_id=None,
                    employee_id=employee.id,
                    document_type_id=None,
                    document_type_code="otro",
                    file_path=doc_path,
                    file_name=doc_name,
                    title=f"Permiso: {start_date} → {end_date}",
                    requires_acknowledgment=False,
                )

            clear_pending_upload(self._session, employee.id)
            clear_pending(self._session, employee.id)
            self._session.commit()

            reply = (
                f"✅ Permiso registrado: *{start_date} → {end_date}* ({days:.1f} días).\n"
                "Pendiente de aprobación por tu supervisor."
            )
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "media_permiso_created"}

        # fallback
        return {"ok": True, "action": "media_unknown"}

    @staticmethod
    def _parse_leave_dates(text: str) -> tuple:
        """Intenta extraer fecha inicio y fecha fin de un texto en español."""
        from datetime import date as _date, timedelta
        import re as _re

        t = text.strip()

        # Patrones tipo "del X al Y de mes" o "X - Y" o "X/Y/Z - A/B/C"
        # dd/mm/aaaa o dd/mm/aa
        date_pattern = r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)"
        dates = _re.findall(date_pattern, t)
        if len(dates) >= 2:
            d1 = _parse_date_flex(dates[0])
            d2 = _parse_date_flex(dates[1])
            if d1 and d2:
                return (d1, d2) if d1 <= d2 else (d2, d1)

        # Patrón "del X al Y de mes"
        meses = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
            "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
            "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
            "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
        }
        range_pattern = r"del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(\w+)"
        m = _re.search(range_pattern, t, _re.IGNORECASE)
        if m:
            d1 = int(m.group(1))
            d2 = int(m.group(2))
            mes_key = m.group(3).lower().rstrip("s")
            mes = meses.get(mes_key)
            if mes:
                year = _date.today().year
                # Si el mes ya pasó, asumir próximo año
                today = _date.today()
                d1_date = _date(year, mes, d1)
                if d1_date < today:
                    d1_date = _date(year + 1, mes, d1)
                d2_date = _date(d1_date.year, mes, d2)
                if d2_date < d1_date:
                    d2_date = _date(d1_date.year + 1, mes, d2)
                return (d1_date, d2_date) if d1_date <= d2_date else (d2_date, d1_date)

        # Un solo día: "mañana", "hoy", "el 10 de junio"
        single_day = _parse_date_flex(t)
        if single_day:
            return (single_day, single_day + timedelta(days=1))

        return (None, None)

    async def _execute_intent(
        self,
        employee: Employee,
        intent: OllamaIntentResponse,
        raw_text: str,
        message_id: str | None,
    ) -> str:
        match intent.intent:
            case "fichar_entrada":
                return await self._open_clock_with_project_flow(
                    employee,
                    whatsapp_message_id=message_id,
                    picker_text=raw_text,
                )

            case "fichar_salida":
                if self._settings.daily_summary_enabled:
                    return self._request_work_summary(
                        employee, whatsapp_message_id=message_id
                    )
                summary = _extract_work_summary(raw_text)
                return self._close_clock(
                    employee,
                    work_summary=summary,
                    whatsapp_message_id=message_id,
                )

            case "resumen_dia":
                if not self._settings.daily_summary_enabled:
                    return (
                        "La consulta de resumen del día no está activada "
                        "en tu empresa."
                    )
                return build_daily_summary(self._session, employee.id)

            case "inicio_parada":
                record = self._breaks.register_break(
                    employee_id=employee.id,
                    record_type=BreakType.INICIO,
                    whatsapp_message_id=message_id,
                )
                return format_break_registered(
                    "INICIO DE PARADA",
                    _to_spain(record.recorded_at).strftime("%H:%M:%S"),
                )

            case "fin_parada":
                record = self._breaks.register_break(
                    employee_id=employee.id,
                    record_type=BreakType.FIN,
                    whatsapp_message_id=message_id,
                )
                return format_break_registered(
                    "FIN DE PARADA",
                    _to_spain(record.recorded_at).strftime("%H:%M:%S"),
                )

            case "solicitar_vacaciones":
                _, msg = self._leave.create_request(employee, intent, raw_text)
                return msg

            case "solicitar_permiso":
                # Permiso de un solo día: mapear "fecha" → fecha_inicio/fecha_fin
                if "fecha" in intent.entities and "fecha_inicio" not in intent.entities:
                    intent.entities["fecha_inicio"] = intent.entities["fecha"]
                    intent.entities["fecha_fin"] = intent.entities["fecha"]
                # Si no hay motivo explícito, usar el mensaje del usuario
                if "motivo" not in intent.entities and raw_text:
                    intent.entities["motivo"] = raw_text[:200]
                _, msg = self._leave.create_request(employee, intent, raw_text)
                return msg

            case "consultar_saldo_vacaciones":
                return self._leave.get_balance_message(employee)

            case "vacaciones_pendientes" | "aprobar_vacaciones":
                return self._list_pending_leaves_for_approval(employee)

            case "incidencias_abiertas":
                return self._list_team_incidents(employee, unmanaged_only=False)

            case "incidencias_sin_gestionar":
                return self._list_team_incidents(employee, unmanaged_only=True)

            case "confirmar_documento":
                return self._leave.acknowledge_document(employee.id, raw_text)

            case "reportar_incidencia":
                return self._execute_reportar_incidencia(employee, intent, raw_text)

            case _:
                allowed = list_whatsapp_actions_for_employee(
                    self._session, employee, self._tenant_id
                )
                hints = [ACTION_LABELS.get(c, c) for c in allowed]
                if not hints:
                    return denial_message(self._session, employee, self._tenant_id)
                extra = []
                if (
                    "fichar_entrada" in allowed or "fichar_salida" in allowed
                ):
                    extra.append("Compartir ubicación (clip → Ubicación) para fichar")
                return format_conversational_help(
                    hints + extra,
                    employee_name=employee.full_name,
                    lead=intent.message or None,
                )

    def _execute_reportar_incidencia(
        self,
        employee: Employee,
        intent: OllamaIntentResponse,
        raw_text: str,
    ) -> str:
        """Crea una incidencia de fichaje desde WhatsApp."""
        from app.services.incident_service import create_incident
        import re as _re

        title = (
            intent.entities.get("title")
            or intent.entities.get("titulo")
            or intent.message
            or None
        )
        # Fallback 1: mensaje original del empleado (guardado en pending_meta al confirmar)
        if not title:
            orig = (intent.entities.get("_original_text") or "").strip()
            _skip = {"si", "sí", "yes", "vale", "ok", "okey", "confirmo", "dale",
                     "claro", "si, por favor", "sí, por favor", "si por favor", "sí por favor"}
            if orig and orig.lower() not in _skip:
                title = orig[:300]
        # Fallback 2: extraer del mensaje de confirmación de la IA
        if not title:
            ai_summary = intent.entities.get("_ai_summary", "")
            if ai_summary:
                m = _re.search(
                    r'(?:incidencia\s+(?:por|de|para|sobre)\s+|registre\s+(?:una\s+)?incidencia\s+(?:por|de|para)\s+)(.+)',
                    ai_summary, _re.IGNORECASE
                )
                if m:
                    title = m.group(1).rstrip("?.").strip().capitalize()
        # Fallback 3: raw_text solo si no parece un mensaje de confirmación
        if not title:
            _skip_raw = {"si", "sí", "vale", "ok", "okey", "confirmo", "dale", "claro",
                         "si, por favor", "sí, por favor", "si por favor", "sí por favor"}
            if raw_text and raw_text.lower() not in _skip_raw:
                title = raw_text[:300]
        if not title:
            title = "Incidencia reportada por WhatsApp"

        description = (
            intent.entities.get("description")
            or intent.entities.get("descripcion")
            or intent.entities.get("motivo")
            or None
        )

        # Extraer fecha de la incidencia (puede ser ayer, anteayer, fecha concreta...)
        from datetime import date as _date
        incident_date: _date | None = None
        fecha_raw = intent.entities.get("fecha_incidencia")
        if fecha_raw and str(fecha_raw).strip().lower() not in ("null", "none", ""):
            try:
                incident_date = _date.fromisoformat(str(fecha_raw).strip())
            except (ValueError, TypeError):
                pass
        if incident_date is None:
            incident_date = _parse_date_flex(str(fecha_raw).strip()) if fecha_raw else None
        if incident_date is None:
            incident_date = _date.today()

        incident = create_incident(
            self._session,
            tenant_id=self._tenant_id,
            employee_id=employee.id,
            category="fichaje",
            incident_type="manual",
            title=str(title)[:300],
            description=str(description)[:2000] if description else None,
            source="whatsapp",
            incident_date=incident_date,
            created_by_id=employee.id,
        )

        self._session.commit()

        # Dejar estado pendiente para recibir adjuntos opcionales
        from app.services.clock_pending_service import get_pending, set_pending
        existing = get_pending(self._session, employee.id)
        meta = dict(existing.pending_meta or {}) if existing else {}
        meta["awaiting_incident_file"] = True
        meta["incident_id"] = str(incident.id)
        set_pending(
            self._session,
            employee_id=employee.id,
            record_type=existing.record_type if existing else "incident",
            pending_confirmation=False,
            pending_intent="awaiting_incident_file",
            pending_meta=meta,
        )
        self._session.commit()

        return (
            f"✅ Incidencia registrada: *{incident.title}*\n\n"
            "¿Quieres adjuntar algún documento o foto? "
            "Envíalo ahora por WhatsApp o escribe _listo_ para terminar."
        )

    # ── Gestión de equipo por WhatsApp (responsables) ────────────────────────
    def _wa_manager_scope(self, manager: Employee, module: str) -> list[UUID]:
        """IDs de empleados que el responsable puede gestionar por WhatsApp.

        Si el responsable no tiene grupo de permisos asignado (solo matriz IA),
        el alcance es toda su empresa — coherente con `is_whatsapp_action_allowed`,
        que también trata «sin permisos» como «autorizado por matriz».
        """
        from app.core.permissions import get_employee_permissions
        from app.services.org_service import employee_ids_in_scope
        from app.services.scope_service import read_scope_employee_ids

        if not get_employee_permissions(self._session, manager, self._tenant_id):
            return employee_ids_in_scope(
                self._session, self._tenant_id, company_id=manager.company_id
            )
        return read_scope_employee_ids(
            self._session,
            manager,
            self._tenant_id,
            module,
            company_id=manager.company_id,
        )

    def _pending_leaves(self, manager: Employee) -> list[LeaveRequest]:
        from sqlmodel import select

        ids = self._wa_manager_scope(manager, "leave")
        if not ids:
            return []
        return list(
            self._session.exec(
                select(LeaveRequest)
                .where(
                    LeaveRequest.employee_id.in_(ids),  # type: ignore[attr-defined]
                    LeaveRequest.status == LeaveStatus.PENDING,
                )
                .order_by(LeaveRequest.start_date)  # type: ignore[attr-defined]
            ).all()
        )

    def _list_pending_leaves_for_approval(self, manager: Employee) -> str:
        """Lista las vacaciones pendientes y deja el estado para aprobar/rechazar."""
        leaves = self._pending_leaves(manager)
        if not leaves:
            clear_pending(self._session, manager.id)
            return "✅ No tienes solicitudes de vacaciones pendientes de aprobar."

        lines = [f"📋 *Vacaciones pendientes de aprobar* ({len(leaves)}):", ""]
        leave_ids: list[str] = []
        for i, lv in enumerate(leaves, start=1):
            leave_ids.append(str(lv.id))
            emp = self._session.get(Employee, lv.employee_id)
            name = emp.full_name if emp else "—"
            lt = (
                self._session.get(LeaveType, lv.leave_type_id)
                if lv.leave_type_id
                else None
            )
            tname = f" · {lt.name}" if lt else ""
            lines.append(
                f"*{i}.* {name} — {_fmt_short_date(lv.start_date)} a "
                f"{_fmt_short_date(lv.end_date)} ({lv.days_requested:g} días){tname}"
            )
        lines += [
            "",
            "Responde *aprobar N* o *rechazar N* (p. ej. _aprobar 1_), "
            "o *aprobar todas*.",
            "Escribe *cancelar* para salir.",
        ]
        set_pending(
            self._session,
            employee_id=manager.id,
            record_type="leave_approval",
            pending_confirmation=False,
            pending_intent="aprobar_vacaciones",
            pending_meta={"awaiting_leave_approval": True, "leave_ids": leave_ids},
        )
        return "\n".join(lines)

    def _apply_leave_decision(
        self, manager: Employee, lv: LeaveRequest, approve: bool
    ) -> None:
        from datetime import datetime

        lv.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
        lv.reviewed_at = datetime.utcnow()
        lv.supervisor_id = manager.id
        verb = "Aprobada" if approve else "Rechazada"
        lv.review_notes = f"{verb} por {manager.full_name} (WhatsApp)"
        self._session.add(lv)

    def _notify_leave_reviewed(self, lv: LeaveRequest, approve: bool) -> None:
        from app.services.notification_service import notify_leave_request_reviewed

        emp = self._session.get(Employee, lv.employee_id)
        if not emp:
            return
        lt = (
            self._session.get(LeaveType, lv.leave_type_id)
            if lv.leave_type_id
            else None
        )
        notify_leave_request_reviewed(
            self._session,
            tenant_id=self._tenant_id,
            employee=emp,
            new_status=lv.status.value,
            start_date=str(lv.start_date),
            end_date=str(lv.end_date),
            days=lv.days_requested,
            leave_type_name=lt.name if lt else None,
            review_notes=lv.review_notes,
        )

    async def _handle_leave_approval_response(
        self, manager: Employee, phone: str, text: str, pending
    ) -> dict:
        """Procesa «aprobar N» / «rechazar N» / «aprobar todas» del responsable."""
        meta = pending.pending_meta or {}
        leave_ids: list[str] = list(meta.get("leave_ids") or [])
        t = normalize_whatsapp_text(text)

        if is_negative_reply(text) or t.strip() in ("cancelar", "cancela", "salir", "nada"):
            clear_pending(self._session, manager.id)
            self._session.commit()
            await self._safe_send(phone, "De acuerdo, no he cambiado nada. 👍")
            return {"ok": True, "action": "leave_approval_cancelled"}

        approve: bool | None = None
        if _re.search(r"\b(rechaz|deneg|denieg)\w*", t):
            approve = False
        elif _re.search(r"\b(aprob|acept|confirm|ok|vale|si)\w*", t):
            approve = True

        all_match = bool(_re.search(r"\btodas?\b", t))
        idxs = [int(n) for n in _re.findall(r"\d+", t)]

        # Sin verbo pero con selección → en este contexto se asume aprobar.
        if approve is None and (idxs or all_match):
            approve = True

        if approve is None:
            await self._safe_send(
                phone,
                "Dime *aprobar N* o *rechazar N* (p. ej. _aprobar 1_), "
                "*aprobar todas*, o *cancelar*.",
            )
            return {"ok": True, "action": "leave_approval_reminder"}

        if all_match:
            targets = list(leave_ids)
        else:
            targets = [leave_ids[i - 1] for i in idxs if 1 <= i <= len(leave_ids)]
        if not targets:
            await self._safe_send(
                phone,
                f"No reconozco esa selección. Hay {len(leave_ids)} solicitudes; "
                "responde por ejemplo _aprobar 1_.",
            )
            return {"ok": True, "action": "leave_approval_bad_index"}

        scope = set(self._wa_manager_scope(manager, "leave"))
        done: list[LeaveRequest] = []
        for lid in targets:
            try:
                lv = self._session.get(LeaveRequest, UUID(lid))
            except (ValueError, TypeError):
                lv = None
            if not lv or lv.status != LeaveStatus.PENDING:
                continue
            if lv.employee_id not in scope:
                continue
            self._apply_leave_decision(manager, lv, approve)
            done.append(lv)

        verb = "aprobado" if approve else "rechazado"
        header = (
            f"✅ He {verb} {len(done)} solicitud(es)."
            if done
            else "No he podido procesar esa selección (puede que ya estuvieran gestionadas)."
        )
        # Recalcular pendientes restantes y refrescar estado.
        remaining_msg = self._list_pending_leaves_for_approval(manager)
        self._session.commit()
        for lv in done:
            try:
                self._notify_leave_reviewed(lv, approve)
            except Exception:
                pass
        await self._safe_send(phone, header + "\n\n" + remaining_msg)
        return {"ok": True, "action": "leave_approved" if approve else "leave_rejected"}

    def _list_team_incidents(self, manager: Employee, *, unmanaged_only: bool) -> str:
        """Lista incidencias del equipo: abiertas o sin gestionar."""
        from sqlmodel import select

        ids = self._wa_manager_scope(manager, "clock_ins")
        title = "sin gestionar" if unmanaged_only else "abiertas"
        if not ids:
            return f"No tienes incidencias {title} visibles para gestionar."
        stmt = select(Incident).where(
            Incident.tenant_id == self._tenant_id,
            Incident.employee_id.in_(ids),  # type: ignore[attr-defined]
        )
        if unmanaged_only:
            stmt = stmt.where(
                Incident.managed == False,  # noqa: E712
                Incident.status != "dismissed",
            )
        else:
            stmt = stmt.where(
                Incident.status.in_(["open", "pending_justification"])  # type: ignore[attr-defined]
            )
        rows = list(
            self._session.exec(
                stmt.order_by(Incident.created_at.desc())  # type: ignore[attr-defined]
            ).all()
        )
        if not rows:
            return f"✅ No hay incidencias {title}."

        lines = [f"⚠️ *Incidencias {title}* ({len(rows)}):", ""]
        for inc in rows[:20]:
            emp = self._session.get(Employee, inc.employee_id)
            name = emp.full_name if emp else "—"
            d = inc.incident_date or inc.created_at.date()
            status_lbl = _INCIDENT_STATUS_LABELS.get(inc.status, inc.status)
            lines.append(
                f"• *{name}* — {inc.title} ({_fmt_short_date(d)}) · _{status_lbl}_"
            )
        if len(rows) > 20:
            lines.append(f"\n… y {len(rows) - 20} más. Gestiónalas desde el panel.")
        return "\n".join(lines)

    async def _safe_send(self, phone: str, text: str) -> None:
        try:
            await self._gowa.send_text(phone, text)
        except Exception:
            pass


_INCIDENT_STATUS_LABELS: dict[str, str] = {
    "pending_justification": "pendiente de justificación",
    "open": "abierta",
    "resolved": "resuelta",
    "dismissed": "descartada",
}


def _fmt_short_date(value) -> str:
    try:
        return value.strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def _parse_date_flex(raw: str):
    """Parsea una fecha en múltiples formatos. Retorna date o None."""
    from datetime import date as _date, timedelta
    import re as _re

    raw = raw.strip().lower()
    today = _date.today()

    if raw in ("hoy", "today"):
        return today
    if raw in ("mañana", "manana", "tomorrow"):
        return today + timedelta(days=1)
    if raw in ("pasado mañana", "pasado manana"):
        return today + timedelta(days=2)

    # dd/mm/yyyy, dd/mm/yy, dd-mm-yyyy
    for sep in ("/", "-"):
        parts = raw.split(sep)
        if len(parts) == 3:
            try:
                d = int(parts[0])
                m = int(parts[1])
                y = int(parts[2])
                if y < 100:
                    y += 2000
                return _date(y, m, d)
            except (ValueError, TypeError):
                pass

    # dd de mes
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
        "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
    }
    m = _re.match(r"(\d{1,2})\s+de\s+(\w+)", raw)
    if m:
        d = int(m.group(1))
        mes_key = m.group(2).lower().rstrip("s")
        mes = meses.get(mes_key)
        if mes:
            year = today.year
            result = _date(year, mes, d)
            if result < today:
                result = _date(year + 1, mes, d)
            return result

    return None
