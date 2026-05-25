from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.models.models import BreakType, ClockInType, Employee
from app.models.tenant import Tenant
from app.schemas.ollama import OllamaIntentResponse
from app.schemas.whatsapp import GoWAMessage, GoWAWebhookPayload
from app.services.break_service import BreakService
from app.services.clock_pending_service import clear_pending, get_pending, set_pending
from app.services.clock_incident_hook import (
    should_notify_whatsapp,
    whatsapp_message_for_incident,
)
from app.services.clock_service import ClockService
from app.services.clock_settings_service import get_or_create_settings
from app.services.daily_summary_service import build_daily_summary
from app.services.employee_onboarding_service import (
    build_welcome_message,
    mark_welcome_sent,
    receive_inbound_file,
    seed_inbound_documents,
    should_send_welcome,
)
from app.services.gowa_service import GoWAService
from app.services.leave_service import LeaveService
from app.services.ai_config_service import is_action_allowed_for_role
from app.services.ai_usage_service import profile_key_for_employee
from app.services.ollama_service import OllamaService
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
        message = payload.resolve_message()

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

        if message and message.is_location and message.location:
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
        if self._settings.require_geolocation:
            return (
                "\n\n📍 Recuerda: se recomienda compartir tu ubicación al fichar."
            )
        return ""

    def _next_record_type(self, employee_id: UUID) -> tuple[ClockInType, str]:
        last = self._clock.get_last_clock(employee_id)
        if last and last.record_type == ClockInType.ENTRADA:
            return ClockInType.SALIDA, "SALIDA"
        return ClockInType.ENTRADA, "ENTRADA"

    def _format_clock_reply(
        self,
        label: str,
        record,
        project_name: str | None = None,
    ) -> str:
        msg = (
            f"Fichaje {label} registrado a las "
            f"{record.recorded_at.strftime('%H:%M:%S')} (hora servidor)."
        )
        if project_name:
            msg += f"\nProyecto: {project_name}"
        if record.latitude is not None and record.longitude is not None:
            msg += (
                f"\nUbicación: {record.latitude:.6f}, {record.longitude:.6f}"
            )
        return msg

    def _register_clock_with_project_flow(
        self,
        employee: Employee,
        record_type: ClockInType,
        label: str,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        whatsapp_message_id: str | None = None,
        picker_text: str | None = None,
    ) -> str:
        if not self._settings.require_project_on_clock_in:
            record = self._clock.register_clock(
                employee_id=employee.id,
                record_type=record_type,
                latitude=latitude,
                longitude=longitude,
                whatsapp_message_id=whatsapp_message_id,
                commit=False,
            )
            return self._format_clock_reply(label, record)

        if picker_text:
            direct = resolve_project_from_reply(
                self._session, employee.company_id, picker_text
            )
            if direct:
                record = self._clock.register_clock(
                    employee_id=employee.id,
                    record_type=record_type,
                    latitude=latitude,
                    longitude=longitude,
                    whatsapp_message_id=whatsapp_message_id,
                    project_id=direct.id,
                    commit=False,
                )
                clear_pending(self._session, employee.id)
                return self._format_clock_reply(label, record, direct.name)

        pending = get_pending(self._session, employee.id)
        if pending:
            project = resolve_project_from_reply(
                self._session, employee.company_id, picker_text or ""
            )
            if not project:
                projects = list_active_projects(self._session, employee.company_id)
                return (
                    format_project_picker_message(projects, label)
                    + "\n\nNo he reconocido el proyecto. Responde con el número o nombre."
                )
            rt = (
                ClockInType.SALIDA
                if pending.record_type == ClockInType.SALIDA.value
                else ClockInType.ENTRADA
            )
            lbl = "SALIDA" if rt == ClockInType.SALIDA else "ENTRADA"
            record = self._clock.register_clock(
                employee_id=employee.id,
                record_type=rt,
                latitude=pending.latitude,
                longitude=pending.longitude,
                whatsapp_message_id=pending.whatsapp_message_id or whatsapp_message_id,
                project_id=project.id,
                commit=False,
            )
            clear_pending(self._session, employee.id)
            return self._format_clock_reply(lbl, record, project.name)

        projects = list_active_projects(self._session, employee.company_id)
        set_pending(
            self._session,
            employee_id=employee.id,
            record_type=record_type,
            latitude=latitude,
            longitude=longitude,
            whatsapp_message_id=whatsapp_message_id,
        )
        return format_project_picker_message(projects, label)

    async def _handle_location(
        self, employee_id: UUID, phone: str, message: GoWAMessage
    ) -> dict:
        loc = message.location
        if not loc:
            return {"ok": False, "error": "Ubicación vacía"}

        employee = self._session.get(Employee, employee_id)
        if not employee:
            return {"ok": False, "error": "Empleado no encontrado"}

        record_type, label = self._next_record_type(employee_id)
        reply = self._register_clock_with_project_flow(
            employee,
            record_type,
            label,
            latitude=loc.latitude,
            longitude=loc.longitude,
            whatsapp_message_id=message.id,
        )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply + self._geo_hint())
            await self._notify_incident_if_needed(phone)
        except Exception:
            pass
        return {
            "ok": True,
            "action": f"fichar_{record_type.value}",
        }

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

        file_bytes = path.read_bytes()
        filename = message.file_name or path.name
        ok, reply = receive_inbound_file(
            self._session,
            employee,
            tenant_id=self._tenant_id,
            file_bytes=file_bytes,
            filename=filename,
        )
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
        except Exception:
            pass
        return {"ok": ok, "action": "inbound_document" if ok else "inbound_rejected"}

    async def _handle_text(
        self,
        employee: Employee,
        phone: str,
        text: str,
        message_id: str | None,
    ) -> dict:
        pending = get_pending(self._session, employee.id)
        if self._settings.require_project_on_clock_in and pending:
            rt = (
                ClockInType.SALIDA
                if pending.record_type == ClockInType.SALIDA.value
                else ClockInType.ENTRADA
            )
            lbl = "SALIDA" if rt == ClockInType.SALIDA else "ENTRADA"
            reply = self._register_clock_with_project_flow(
                employee,
                rt,
                lbl,
                whatsapp_message_id=message_id,
                picker_text=text,
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
                await self._notify_incident_if_needed(phone)
            except Exception:
                pass
            return {"ok": True, "action": "select_project"}

        if self._settings.daily_summary_enabled:
            lower = text.lower().strip()
            if any(
                k in lower
                for k in (
                    "resumen del dia",
                    "resumen del día",
                    "resumen hoy",
                    "resumen de hoy",
                )
            ):
                reply = build_daily_summary(self._session, employee.id)
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "resumen_dia"}

        self._ollama.profile_key = profile_key_for_employee(employee.role)
        intent_data = await self._ollama.extract_intent(text)
        if not is_action_allowed_for_role(
            self._session, employee.role, intent_data.intent
        ):
            reply = (
                "No tienes permiso para realizar esa acción por WhatsApp. "
                "Contacta con tu responsable o RRHH."
            )
        else:
            reply = await self._execute_intent(
                employee, intent_data, text, message_id
            )
            if intent_data.intent in ("fichar_entrada", "fichar_salida"):
                reply += self._geo_hint()
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
            if intent_data.intent in ("fichar_entrada", "fichar_salida"):
                await self._notify_incident_if_needed(phone)
        except Exception:
            pass
        return {"ok": True, "action": intent_data.intent, "reply": reply}

    async def _execute_intent(
        self,
        employee: Employee,
        intent: OllamaIntentResponse,
        raw_text: str,
        message_id: str | None,
    ) -> str:
        match intent.intent:
            case "fichar_entrada":
                return self._register_clock_with_project_flow(
                    employee,
                    ClockInType.ENTRADA,
                    "ENTRADA",
                    whatsapp_message_id=message_id,
                    picker_text=raw_text,
                )

            case "fichar_salida":
                return self._register_clock_with_project_flow(
                    employee,
                    ClockInType.SALIDA,
                    "SALIDA",
                    whatsapp_message_id=message_id,
                    picker_text=raw_text,
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
                return (
                    f"INICIO DE PARADA registrado a las "
                    f"{record.recorded_at.strftime('%H:%M:%S')} (hora servidor)."
                )

            case "fin_parada":
                record = self._breaks.register_break(
                    employee_id=employee.id,
                    record_type=BreakType.FIN,
                    whatsapp_message_id=message_id,
                )
                return (
                    f"FIN DE PARADA registrado a las "
                    f"{record.recorded_at.strftime('%H:%M:%S')} (hora servidor)."
                )

            case "solicitar_vacaciones":
                _, msg = self._leave.create_request(employee, intent, raw_text)
                return msg

            case "consultar_saldo_vacaciones":
                return self._leave.get_balance_message(employee)

            case "confirmar_documento":
                return self._leave.acknowledge_document(employee.id, raw_text)

            case _:
                hints = [
                    "fichar entrada/salida",
                    "iniciar o finalizar parada",
                    "solicitar vacaciones",
                    "consultar saldo",
                    "enviar documentación",
                    "compartir ubicación para fichar",
                ]
                if self._settings.daily_summary_enabled:
                    hints.append("pedir resumen del día")
                return (
                    "No he entendido tu solicitud. Puedes: "
                    + ", ".join(hints)
                    + "."
                )
