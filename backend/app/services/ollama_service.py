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
            keyword_rescue.intent in _NON_CLOCK_INTENTS
            and keyword_rescue.confidence >= 0.7
            and intent.intent in _CLOCK_INTENTS
        ):
            logger.info(
                "Anti-clock-bias override: DeepSeek=%s → NLU=%s (msg=%r)",
                intent.intent, keyword_rescue.intent, message_text[:60],
            )
            intent = keyword_rescue

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
