from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.models.models import BreakType, ClockInType, Employee
from app.models.tenant import Tenant
from app.schemas.ollama import OllamaIntentResponse
from app.schemas.whatsapp import GoWAMessage, GoWAWebhookPayload
from app.services.break_service import BreakService
from app.services.clock_service import ClockService
from app.services.clock_settings_service import get_or_create_settings
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

    async def _handle_location(
        self, employee_id: UUID, phone: str, message: GoWAMessage
    ) -> dict:
        loc = message.location
        if not loc:
            return {"ok": False, "error": "Ubicación vacía"}

        last = self._clock.get_last_clock(employee_id)
        if last and last.record_type == ClockInType.ENTRADA:
            record_type = ClockInType.SALIDA
            label = "SALIDA"
        else:
            record_type = ClockInType.ENTRADA
            label = "ENTRADA"

        record = self._clock.register_clock(
            employee_id=employee_id,
            record_type=record_type,
            latitude=loc.latitude,
            longitude=loc.longitude,
            whatsapp_message_id=message.id,
            notes="Fichaje con geolocalización WhatsApp",
        )

        reply = (
            f"Fichaje {label} registrado a las "
            f"{record.recorded_at.strftime('%H:%M:%S')} (hora servidor). "
            f"Ubicación: {loc.latitude:.6f}, {loc.longitude:.6f}"
        )
        try:
            await self._gowa.send_text(phone, reply)
        except Exception:
            pass
        return {
            "ok": True,
            "action": f"fichar_{record_type.value}",
            "clock_in_id": str(record.id),
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
            reply += self._geo_hint()
        self._session.commit()
        try:
            await self._gowa.send_text(phone, reply)
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
                record = self._clock.register_clock(
                    employee_id=employee.id,
                    record_type=ClockInType.ENTRADA,
                    whatsapp_message_id=message_id,
                )
                return (
                    f"ENTRADA registrada a las "
                    f"{record.recorded_at.strftime('%H:%M:%S')} (hora servidor)."
                )

            case "fichar_salida":
                record = self._clock.register_clock(
                    employee_id=employee.id,
                    record_type=ClockInType.SALIDA,
                    whatsapp_message_id=message_id,
                )
                return (
                    f"SALIDA registrada a las "
                    f"{record.recorded_at.strftime('%H:%M:%S')} (hora servidor)."
                )

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
                return (
                    "No he entendido tu solicitud. Puedes: fichar entrada/salida, "
                    "iniciar o finalizar parada, solicitar vacaciones, consultar saldo, "
                    "enviar documentación pendiente o compartir ubicación para fichar."
                )
