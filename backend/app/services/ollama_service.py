import json
import re
import time
from typing import Any
from uuid import UUID

import httpx
from sqlmodel import Session

from app.config import get_settings
from app.models.models import Employee
from app.models.tenant import Tenant
from app.models.clock_settings import ClockSettings
from app.schemas.ollama import OllamaIntentResponse
from app.services.ai_conversation_service import (
    build_system_prompt,
    get_history_for_ollama,
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
    ) -> str:
        if self._session and employee and tenant and clock_settings and self._tenant_id:
            return build_system_prompt(
                self._session,
                employee=employee,
                tenant=tenant,
                settings=clock_settings,
                tenant_id=self._tenant_id,
            )
        return (
            "Eres un clasificador de intenciones HRM por WhatsApp. "
            'Responde solo JSON con intent, entities y confidence. '
            'Intents: fichar_entrada, fichar_salida, inicio_parada, fin_parada, '
            "solicitar_vacaciones, consultar_saldo_vacaciones, confirmar_documento, "
            "resumen_dia, desconocido."
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
        try:
            history = []
            if self._session and employee and self._tenant_id:
                history = get_history_for_ollama(
                    self._session, self._tenant_id, employee.id
                )
            intent, prompt_tokens, completion_tokens = await self._call_ollama(
                message_text,
                employee=employee,
                tenant=tenant,
                clock_settings=clock_settings,
                history=history,
            )
        except Exception:
            success = False
            intent = self._keyword_fallback(message_text, allowed)
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
                source="whatsapp",
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                success=success,
            )
        return intent

    async def _call_ollama(
        self,
        message_text: str,
        *,
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
            "model": self._model,
            "stream": False,
            "format": "json",
            "messages": messages,
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

    @staticmethod
    def _keyword_fallback(
        message_text: str, allowed: list[str] | None = None
    ) -> OllamaIntentResponse:
        t = message_text.lower()

        def ok(code: str) -> bool:
            if not allowed:
                return True
            return code in allowed

        if ok("fichar_entrada") and any(
            w in t for w in ("entrada", "fiché", "fiche", "empiezo", "llego")
        ):
            return OllamaIntentResponse(intent="fichar_entrada", confidence=0.7)
        if ok("fichar_salida") and any(
            w in t for w in ("salida", "termino", "me voy")
        ):
            return OllamaIntentResponse(intent="fichar_salida", confidence=0.7)
        if ok("inicio_parada") and (
            any(
                w in t
                for w in (
                    "inicio parada",
                    "empiezo parada",
                    "empiezo descanso",
                    "pausa",
                )
            )
            or (("parada" in t or "descanso" in t) and "fin" not in t and "termin" not in t)
        ):
            return OllamaIntentResponse(intent="inicio_parada", confidence=0.65)
        if ok("fin_parada") and any(
            w in t
            for w in (
                "fin parada",
                "termino parada",
                "acabo parada",
                "vuelvo del descanso",
            )
        ):
            return OllamaIntentResponse(intent="fin_parada", confidence=0.65)
        if ok("solicitar_vacaciones") and any(
            w in t for w in ("vacaciones", "días libres", "dia libre", "permiso")
        ):
            return OllamaIntentResponse(intent="solicitar_vacaciones", confidence=0.6)
        if ok("consultar_saldo_vacaciones") and (
            "saldo" in t or "cuántos días" in t or "cuantos dias" in t
        ):
            return OllamaIntentResponse(
                intent="consultar_saldo_vacaciones", confidence=0.6
            )
        if ok("confirmar_documento") and any(
            w in t for w in ("recibido", "acepto", "confirmo")
        ):
            return OllamaIntentResponse(intent="confirmar_documento", confidence=0.6)
        if ok("resumen_dia") and any(
            w in t
            for w in (
                "resumen del dia",
                "resumen del día",
                "resumen hoy",
                "resumen de hoy",
                "que he fichado",
                "qué he fichado",
            )
        ):
            return OllamaIntentResponse(intent="resumen_dia", confidence=0.75)
        return OllamaIntentResponse(intent="desconocido", confidence=0.3)

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group())
            return {
                "intent": "desconocido",
                "entities": {},
                "confidence": 0.0,
            }
