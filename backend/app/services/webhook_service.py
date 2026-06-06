from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.models.models import BreakType, Employee
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
from app.services.ai_conversation_service import append_message, build_system_prompt, get_history_for_ollama, _to_spain
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

import re as _re
_RE_SALIDA_VERBS = _re.compile(
    r"^\s*(me\s+voy|me\s+marcho|me\s+piro|termino|acabo|finalizo|salida|"
    r"ficho\s*(salida|ya)?|fichar\s*salida|fin\s+de\s+jornada|salgo|"
    r"he\s+terminado|he\s+acabado|voy\s+a\s+salir)[,.\s]*",
    _re.IGNORECASE,
)

def _extract_work_summary(text: str) -> str | None:
    """Extrae el texto libre tras el verbo de salida como resumen del día."""
    cleaned = _RE_SALIDA_VERBS.sub("", text).strip(" .,;:")
    return cleaned if len(cleaned) > 3 else None

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

    def _is_open(self, employee_id: UUID) -> bool:
        return self._clock.get_open_clock(employee_id) is not None

    def _format_clock_reply(self, label: str, record, project_name: str | None = None) -> str:
        ts = record.salida_at if label == "SALIDA" else record.entrada_at
        return format_clock_registered(
            label,
            _to_spain(ts).strftime("%H:%M:%S"),
            project_name=project_name,
            latitude=record.latitude,
            longitude=record.longitude,
        )

    def _open_clock_with_project_flow(
        self,
        employee: Employee,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        whatsapp_message_id: str | None = None,
        picker_text: str | None = None,
    ) -> str:
        """Abre una jornada. Si hay proyectos activos, pide selección primero."""
        if not self._settings.require_project_on_clock_in:
            record = self._clock.open_clock(
                employee_id=employee.id,
                latitude=latitude,
                longitude=longitude,
                whatsapp_message_id=whatsapp_message_id,
                commit=False,
            )
            return self._format_clock_reply("ENTRADA", record)

        if picker_text:
            direct = resolve_project_from_reply(self._session, employee.company_id, picker_text)
            if direct:
                record = self._clock.open_clock(
                    employee_id=employee.id,
                    latitude=latitude,
                    longitude=longitude,
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
            if not project:
                projects = list_active_projects(self._session, employee.company_id)
                return (
                    format_project_picker_message(projects, "ENTRADA")
                    + "\n\nNo he reconocido el proyecto. Responde con el número o nombre."
                )
            record = self._clock.open_clock(
                employee_id=employee.id,
                latitude=pending.latitude,
                longitude=pending.longitude,
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
        )
        return format_project_picker_message(projects, "ENTRADA")

    def _close_clock(
        self,
        employee: Employee,
        work_summary: str | None = None,
        whatsapp_message_id: str | None = None,
    ) -> str:
        record = self._clock.close_clock(
            employee_id=employee.id,
            work_summary=work_summary,
            whatsapp_message_id=whatsapp_message_id,
            commit=False,
        )
        if not record:
            return "No tengo registrada una entrada abierta para ti. ¿Quizás ya fichaste la salida?"
        return self._format_clock_reply("SALIDA", record)

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
        is_open = self._is_open(employee_id)
        if pending and pending.pending_confirmation:
            action = "fichar_salida" if is_open else "fichar_entrada"
            clock_type = "salida" if is_open else "entrada"
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
            if is_open:
                reply = self._close_clock(employee, whatsapp_message_id=message.id)
            else:
                reply = self._open_clock_with_project_flow(
                    employee, latitude=lat, longitude=lng, whatsapp_message_id=message.id,
                )
            clear_pending(self._session, employee_id)
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply + self._geo_hint())
                await self._notify_incident_if_needed(phone)
            except Exception:
                pass
            return {"ok": True, "action": action}

        action = "fichar_salida" if is_open else "fichar_entrada"
        clock_type = "salida" if is_open else "entrada"
        if not can_whatsapp_location_clock(
            self._session, employee, self._tenant_id, record_type=clock_type
        ):
            reply = denial_message(self._session, employee, self._tenant_id)
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "denied_location"}

        if is_open:
            reply = self._close_clock(employee, whatsapp_message_id=message.id)
        else:
            reply = self._open_clock_with_project_flow(
                employee, latitude=lat, longitude=lng, whatsapp_message_id=message.id,
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
            set_pending(
                self._session,
                employee_id=employee.id,
                record_type="salida" if intent_code == "fichar_salida" else "entrada",
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

        # Guard: detectar intent inconsistente con el estado real — solo informar, no ejecutar
        is_open = self._is_open(employee.id)
        if intent_code == "fichar_entrada" and is_open:
            last = self._clock.get_open_clock(employee.id)
            hora = _to_spain(last.entrada_at).strftime("%H:%M") if last else "?"
            reply = (
                f"Ya tienes una jornada abierta desde las *{hora}*.\n"
                "Si quieres fichar la *salida*, dímelo."
            )
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="guard_already_open",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "guard_already_open"}
        elif intent_code == "fichar_salida" and not is_open:
            reply = "No tienes ninguna jornada abierta. Si quieres fichar la *entrada*, dímelo."
            append_message(
                self._session,
                tenant_id=self._tenant_id,
                employee_id=employee.id,
                role="assistant",
                content=reply[:_REPLY_MAX],
                intent_code="guard_not_open",
            )
            self._session.commit()
            try:
                await self._gowa.send_text(phone, reply)
            except Exception:
                pass
            return {"ok": True, "action": "guard_not_open"}

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
            reply = self._close_clock(employee, whatsapp_message_id=message_id)
        else:
            reply = self._open_clock_with_project_flow(
                employee,
                latitude=pending.latitude,
                longitude=pending.longitude,
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
                return self._open_clock_with_project_flow(
                    employee,
                    whatsapp_message_id=message_id,
                    picker_text=raw_text,
                )

            case "fichar_salida":
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
