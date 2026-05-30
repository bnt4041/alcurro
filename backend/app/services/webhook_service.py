from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.models.models import BreakType, ClockInType, Employee
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
from app.services.whatsapp_format import (
    format_break_registered,
    format_clock_registered,
    format_confirmation_cancelled,
    format_conversational_help,
    format_geo_hint,
    format_inbound_document_picker,
)
from app.services.leave_service import LeaveService
from app.services.ai_conversation_service import append_message, _to_spain
from app.services.ai_usage_service import profile_key_for_employee
from app.services.ollama_service import OllamaService
from app.services.whatsapp_nlu import (
    build_confirmation_message,
    is_affirmative_reply,
    is_cancel_or_new_intent,
    is_negative_reply,
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
        return format_clock_registered(
            label,
            _to_spain(record.recorded_at).strftime("%H:%M:%S"),
            project_name=project_name,
            latitude=record.latitude,
            longitude=record.longitude,
        )

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
        # Solo tratar como pendiente de proyecto si NO es una confirmación pendiente
        if pending and not pending.pending_confirmation:
            # El usuario ya eligió proyecto desde el selector
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

        # Si hay confirmación pendiente por ubicación, ejecutar directamente
        pending = get_pending(self._session, employee_id)
        if pending and pending.pending_confirmation:
            record_type = (
                ClockInType.SALIDA
                if pending.record_type == ClockInType.SALIDA.value
                else ClockInType.ENTRADA
            )
            label = "SALIDA" if record_type == ClockInType.SALIDA else "ENTRADA"
            if not can_whatsapp_location_clock(
                self._session, employee, self._tenant_id, record_type=record_type.value
            ):
                reply = denial_message(self._session, employee, self._tenant_id)
                clear_pending(self._session, employee_id)
                self._session.commit()
                try:
                    await self._gowa.send_text(phone, reply)
                except Exception:
                    pass
                return {"ok": True, "action": "denied_location"}
            reply = self._register_clock_with_project_flow(
                employee,
                record_type,
                label,
                latitude=lat,
                longitude=lng,
                whatsapp_message_id=message.id,
            )
            clear_pending(self._session, employee_id)
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply + self._geo_hint())
                await self._notify_incident_if_needed(phone)
            except Exception:
                pass
            return {"ok": True, "action": f"fichar_{record_type.value}"}

        record_type, label = self._next_record_type(employee_id)
        if not can_whatsapp_location_clock(
            self._session,
            employee,
            self._tenant_id,
            record_type=record_type.value,
        ):
            reply = denial_message(self._session, employee, self._tenant_id)
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "denied_location"}

        reply = self._register_clock_with_project_flow(
            employee,
            record_type,
            label,
            latitude=lat,
            longitude=lng,
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

        ok, reply = receive_inbound_file(
            self._session,
            employee,
            tenant_id=self._tenant_id,
            file_bytes=file_bytes,
            filename=filename,
            document_code=file_pending[0].document_code if len(file_pending) == 1 else None,
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
        # 1. Pendiente de subir documento
        upload_pending = get_pending_upload(self._session, employee.id)
        if upload_pending:
            return await self._handle_inbound_document_pick(employee, phone, text)

        # 2. Pendiente de confirmación sí/no
        pending = get_pending(self._session, employee.id)
        if pending and pending.pending_confirmation:
            return await self._handle_confirmation_response(
                employee, phone, text, message_id, pending
            )

        # 3. Pendiente de selección de proyecto (sin confirmación pendiente)
        if self._settings.require_project_on_clock_in and pending:
            return await self._handle_project_selection(
                employee, phone, text, message_id, pending
            )

        # 4. Ollama como orquestador: decide stage (ask/confirm/execute)
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
            record_type = (
                ClockInType.SALIDA
                if intent_code == "fichar_salida"
                else ClockInType.ENTRADA
            )
            set_pending(
                self._session,
                employee_id=employee.id,
                record_type=record_type,
                whatsapp_message_id=message_id,
                pending_confirmation=True,
                pending_intent=intent_code,
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

        reply = await self._execute_intent(
            employee, intent_data, raw_text, message_id
        )
        if intent_code in ("fichar_entrada", "fichar_salida"):
            reply += self._geo_hint()

        # Anteponer mensaje de Ollama al resultado si existe
        if ollama_message and ollama_message not in reply:
            reply = f"{ollama_message}\n\n{reply}"

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
        """Procesa la respuesta sí/no a una confirmación pendiente."""
        intent_code = pending.pending_intent or "fichar_entrada"

        append_message(
            self._session,
            tenant_id=self._tenant_id,
            employee_id=employee.id,
            role="user",
            content=text,
        )

        if is_affirmative_reply(text):
            # Limpiar el pending ANTES de ejecutar (evita que _register_clock_with_project_flow
            # confunda el pending de confirmación con uno de proyecto)
            clear_pending(self._session, employee.id)

            # Ejecutar la acción pendiente directamente (no necesita Ollama para un "sí")
            intent_data = OllamaIntentResponse(
                stage="execute",
                intent=intent_code,
                confidence=1.0,
                message="¡Perfecto!",
            )
            reply = await self._execute_intent(
                employee, intent_data, text, message_id
            )
            if intent_code in ("fichar_entrada", "fichar_salida"):
                reply += self._geo_hint()
            if intent_data.message and intent_data.message not in reply:
                reply = f"{intent_data.message}\n\n{reply}"
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

        if is_negative_reply(text):
            reply = format_confirmation_cancelled(employee.full_name)
            clear_pending(self._session, employee.id)
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="cancelled",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "cancelled"}

        # No es un sí/no claro: dejar que Ollama (orquestador) decida el siguiente paso
        self._ollama.profile_key = profile_key_for_employee(employee.role)
        intent_data = await self._ollama.extract_intent(
            text,
            employee=employee,
            tenant=self._tenant,
            clock_settings=self._settings,
        )
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

        rt = (
            ClockInType.SALIDA
            if pending.record_type == ClockInType.SALIDA.value
            else ClockInType.ENTRADA
        )
        code = "fichar_salida" if rt == ClockInType.SALIDA else "fichar_entrada"
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

            case "consultar_saldo_vacaciones":
                return self._leave.get_balance_message(employee)

            case "confirmar_documento":
                return self._leave.acknowledge_document(employee.id, raw_text)

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
