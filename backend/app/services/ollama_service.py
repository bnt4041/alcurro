import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx
from sqlmodel import Session

logger = logging.getLogger(__name__)

from app.config import get_settings
from app.models.models import BreakType, Employee
from app.services.break_service import BreakService
from app.models.tenant import Tenant
from app.models.clock_settings import ClockSettings
from app.schemas.ollama import OllamaIntentResponse
from app.services.ai_conversation_service import (
    build_system_prompt,
    get_history_for_ollama,
)
from app.services.whatsapp_nlu import (
    match_whatsapp_intent,
)
from app.services.whatsapp_permission_service import list_whatsapp_actions_for_employee


class OllamaService:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        session: Session | None = None,
        tenant_id: UUID | None = None,
        profile_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._session = session
        self._tenant_id = tenant_id
        self.profile_key = profile_key

    def _system_prompt(
        self,
        employee: Employee | None,
        tenant: Tenant | None,
        clock_settings: ClockSettings | None,
        *,
        nlu_hint: str | None = None,
    ) -> str:
        if self._session and employee and tenant and clock_settings and self._tenant_id:
            return build_system_prompt(
                self._session,
                employee=employee,
                tenant=tenant,
                settings=clock_settings,
                tenant_id=self._tenant_id,
                nlu_hint=nlu_hint,
            )
        return (
            "Eres un asistente HRM por WhatsApp. Actúas como orquestador conversacional. "
            'Responde solo JSON: stage ("ask"|"confirm"|"execute"), intent, entities, '
            "confidence, message.\n"
            "- ask: necesitas más información del empleado\n"
            "- confirm: has entendido, pides confirmación sí/no\n"
            "- execute: acción confirmada o de solo lectura, ejecutar directamente\n"
        )

    async def extract_intent(
        self,
        message_text: str,
        *,
        employee: Employee | None = None,
        tenant: Tenant | None = None,
        clock_settings: ClockSettings | None = None,
    ) -> OllamaIntentResponse:
        started = time.perf_counter()
        prompt_tokens = 0
        completion_tokens = 0
        success = True
        intent: OllamaIntentResponse
        allowed: list[str] = []
        if self._session and employee and self._tenant_id:
            allowed = list_whatsapp_actions_for_employee(
                self._session, employee, self._tenant_id
            )
        infer_fichar = self._make_infer_fichar(employee)
        infer_break = self._make_infer_break(employee)
        keyword_rescue = match_whatsapp_intent(
            message_text,
            allowed,
            infer_fichar=infer_fichar,
            infer_break=infer_break,
        )
        # NLU sin filtro de permisos: solo para detectar sesgo del modelo hacia fichajes
        keyword_unfiltered = match_whatsapp_intent(
            message_text,
            allowed=None,
            infer_fichar=infer_fichar,
            infer_break=infer_break,
        )
        logger.info("NLU rescue: intent=%s stage=%s conf=%.2f | unfiltered: intent=%s conf=%.2f | msg=%r",
                    keyword_rescue.intent, keyword_rescue.stage, keyword_rescue.confidence,
                    keyword_unfiltered.intent, keyword_unfiltered.confidence, message_text[:60])

        # IA como decisor: DeepSeek si hay API key configurada, Ollama local si no.
        cfg = get_settings()
        try:
            history = []
            if self._session and employee and self._tenant_id:
                history = get_history_for_ollama(
                    self._session,
                    self._tenant_id,
                    employee.id,
                    exclude_last_user_content=message_text.strip(),
                )
            if cfg.deepseek_api_key:
                intent, prompt_tokens, completion_tokens = await self._call_openai_compatible(
                    message_text,
                    api_key=cfg.deepseek_api_key,
                    base_url=cfg.deepseek_base_url,
                    model=cfg.deepseek_model,
                    employee=employee,
                    tenant=tenant,
                    clock_settings=clock_settings,
                    history=history,
                )
            else:
                intent, prompt_tokens, completion_tokens = await self._call_ollama(
                    message_text,
                    employee=employee,
                    tenant=tenant,
                    clock_settings=clock_settings,
                    history=history,
                    nlu_hint=None,
                )
        except Exception as exc:
            success = False
            logger.warning(
                "IA orquestador falló para tenant=%s msg=%r — usando fallback NLU: %s",
                self._tenant_id,
                message_text[:80],
                exc,
            )
            # Respaldo solo si la IA falla por causas técnicas (red/timeout).
            intent = keyword_rescue

        logger.info("DeepSeek raw: intent=%s stage=%s conf=%.2f", intent.intent, intent.stage, intent.confidence)

        # Si Ollama duda (desconocido o confianza baja) pero el keyword match es preciso,
        # confiar en el keyword — modelos pequeños son poco fiables en frases simples.
        if (
            (intent.intent == "desconocido" or intent.confidence < 0.5)
            and keyword_rescue.confidence >= 0.7
            and keyword_rescue.intent != "desconocido"
        ):
            intent = keyword_rescue

        # Anti-sesgo de fichaje: si el NLU detecta con alta confianza un intent no-fichaje
        # (permiso, vacaciones, incidencia…) pero DeepSeek devolvió un intent de fichaje,
        # confiar en el NLU — el contexto de "jornada abierta" sesga al modelo hacia salida.
        _CLOCK_INTENTS = {"fichar_entrada", "fichar_salida", "inicio_parada", "fin_parada"}
        _NON_CLOCK_INTENTS = {
            "solicitar_permiso", "solicitar_vacaciones", "consultar_saldo_vacaciones",
            "resumen_dia", "confirmar_documento", "reportar_incidencia",
        }
        if (
            keyword_unfiltered.intent in _NON_CLOCK_INTENTS
            and keyword_unfiltered.confidence >= 0.7
            and intent.intent in _CLOCK_INTENTS
        ):
            logger.warning(
                "Anti-clock-bias override: DeepSeek=%s → NLU=%s (allowed=%s) msg=%r",
                intent.intent, keyword_unfiltered.intent, keyword_rescue.intent, message_text[:60],
            )
            override_nlu = keyword_rescue if keyword_rescue.intent == keyword_unfiltered.intent else keyword_unfiltered
            # Mejorar el mensaje estático del NLU con contexto del empleado
            if override_nlu.intent == "solicitar_permiso" and employee:
                first = employee.full_name.split()[0] if employee.full_name else ""
                txt_low = message_text.lower()
                _DAYS = ["lunes","martes","miércoles","miercoles","jueves","viernes","sábado","sabado","domingo","mañana","pasado","hoy","este","próximo","proximo"]
                _REASONS = ["médico","medico","hospital","dentista","cita","personal","asuntos","permiso","baja","urgencia"]
                has_day = any(d in txt_low for d in _DAYS)
                has_reason = any(r in txt_low for r in _REASONS)
                if has_day and has_reason:
                    override_nlu = OllamaIntentResponse(
                        stage="confirm", intent="solicitar_permiso", confidence=0.9,
                        message=f"Entendido, {first}. ¿Te confirmo el permiso para ese día?",
                        entities={},
                    )
                else:
                    override_nlu = OllamaIntentResponse(
                        stage="ask", intent="solicitar_permiso", confidence=0.8,
                        message=f"Claro, {first}. ¿Para qué día necesitas el permiso y cuál es el motivo?",
                        entities={},
                    )
            intent = override_nlu

        if allowed and intent.intent not in allowed and intent.intent != "desconocido":
            intent = OllamaIntentResponse(intent="desconocido", confidence=0.2)

        duration_ms = int((time.perf_counter() - started) * 1000)
        if self._session and self._tenant_id:
            from app.services.ai_usage_service import log_usage

            log_usage(
                self._session,
                tenant_id=self._tenant_id,
                profile_key=self.profile_key,
                action_code=intent.intent,
                source="whatsapp_ai" if success else "whatsapp_fallback",
                model=cfg.deepseek_model if (success and cfg.deepseek_api_key) else self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                success=success,
            )
        return intent

    def _make_infer_fichar(
        self, employee: Employee | None
    ) -> Callable[[], str | None] | None:
        if not self._session or not employee or not self._tenant_id:
            return None

        def infer() -> str | None:
            from app.services.clock_service import ClockService

            last = ClockService(self._session, self._tenant_id).get_last_clock(
                employee.id
            )
            if last and last.salida_at is None:
                return "fichar_salida"
            return "fichar_entrada"

        return infer

    def _make_infer_break(
        self, employee: Employee | None
    ) -> Callable[[], str | None] | None:
        if not self._session or not employee:
            return None

        def infer() -> str | None:
            last = BreakService(self._session).get_last_break(employee.id)
            if last and last.record_type == BreakType.INICIO:
                return "fin_parada"
            if last and last.record_type == BreakType.FIN:
                return "inicio_parada"
            return "inicio_parada"

        return infer

    async def _call_ollama(
        self,
        message_text: str,
        *,
        employee: Employee | None = None,
        tenant: Tenant | None = None,
        clock_settings: ClockSettings | None = None,
        history: list[dict[str, str]] | None = None,
        nlu_hint: str | None = None,
    ) -> tuple[OllamaIntentResponse, int, int]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self._system_prompt(
                    employee, tenant, clock_settings, nlu_hint=nlu_hint
                ),
            },
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message_text.strip()})

        payload = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "messages": messages,
            "options": {"temperature": 0.25, "top_p": 0.9},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        content = data.get("message", {}).get("content", "{}")
        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)
        parsed = self._parse_json_content(content)
        return OllamaIntentResponse.model_validate(parsed), prompt_tokens, completion_tokens

    async def _call_openai_compatible(
        self,
        message_text: str,
        *,
        api_key: str,
        base_url: str,
        model: str,
        employee: Employee | None = None,
        tenant: Tenant | None = None,
        clock_settings: ClockSettings | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[OllamaIntentResponse, int, int]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self._system_prompt(employee, tenant, clock_settings),
            },
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message_text.strip()})

        payload = {
            "model": model,
            "stream": False,
            "response_format": {"type": "json_object"},
            "messages": messages,
            "temperature": 0.25,
            "top_p": 0.9,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        parsed = self._parse_json_content(content)
        logger.debug(
            "DeepSeek response: model=%s intent=%s stage=%s confidence=%s tokens=%s/%s",
            model,
            parsed.get("intent"),
            parsed.get("stage"),
            parsed.get("confidence"),
            prompt_tokens,
            completion_tokens,
        )
        return OllamaIntentResponse.model_validate(parsed), prompt_tokens, completion_tokens

    # Intenciones que requieren confirmación → stage="confirm"
    _CONFIRM_INTENTS = frozenset({
        "fichar_entrada", "fichar_salida",
        "inicio_parada", "fin_parada",
        "solicitar_vacaciones", "solicitar_permiso", "reportar_incidencia",
    })
    # Intenciones de solo lectura → stage="execute"  
    _EXECUTE_INTENTS = frozenset({
        "consultar_saldo_vacaciones", "resumen_dia", "confirmar_documento",
    })

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        content = content.strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                parsed = json.loads(match.group())
            else:
                parsed = {
                    "stage": "ask",
                    "intent": "desconocido",
                    "entities": {},
                    "confidence": 0.0,
                    "message": "",
                }
        # Normalizar stage: si Ollama no lo incluye, inferir desde el intent
        raw_stage = parsed.get("stage")
        if raw_stage not in ("ask", "confirm", "execute"):
            intent = parsed.get("intent", "desconocido")
            if intent in OllamaService._CONFIRM_INTENTS:
                parsed["stage"] = "confirm"
            elif intent in OllamaService._EXECUTE_INTENTS:
                parsed["stage"] = "execute"
            else:
                parsed["stage"] = "ask"
        # Normalizar message
        if parsed.get("message") in ("", "null", None):
            parsed["message"] = ""
        elif isinstance(parsed.get("message"), str):
            parsed["message"] = parsed["message"].strip()[:500]
        else:
            parsed["message"] = ""
        return parsed

    async def match_project(self, text: str, project_names: list[str]) -> int | None:
        """
        Dado el texto libre del empleado y la lista de nombres de proyecto,
        devuelve el índice 0-based del proyecto que mejor encaja, o None.
        Fallback IA para cuando la coincidencia rápida (fuzzy) no basta.
        """
        if not project_names:
            return None
        enumerated = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(project_names))
        system = (
            "Eres un asistente que identifica proyectos de una empresa. "
            "Responde ÚNICAMENTE con el número del proyecto al que se refiere el empleado "
            "(1, 2, 3…) o 0 si no se refiere a ninguno. Sin texto adicional."
        )
        user_msg = f"Proyectos disponibles:\n{enumerated}\n\nEl empleado escribió: \"{text}\""
        cfg = get_settings()
        try:
            if cfg.deepseek_api_key:
                raw = await self._match_raw_openai(system, user_msg, cfg)
            else:
                raw = await self._match_raw_ollama(system, user_msg)
            num = int(raw.strip().split()[0])
            if 1 <= num <= len(project_names):
                return num - 1
        except Exception as exc:
            logger.debug("match_project fallback IA falló: %s", exc)
        return None

    async def _match_raw_ollama(self, system: str, user_msg: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 10},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()

    async def _match_raw_openai(self, system: str, user_msg: str, cfg) -> str:
        payload = {
            "model": cfg.deepseek_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 10,
        }
        headers = {
            "Authorization": f"Bearer {cfg.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{cfg.deepseek_base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
