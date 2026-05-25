import json
import re
import time
from typing import Any
from uuid import UUID

import httpx
from sqlmodel import Session

from app.config import get_settings
from app.schemas.ollama import OllamaIntentResponse
from app.services.ai_config_service import build_rules_prompt

BASE_SYSTEM_PROMPT = """Eres un clasificador de intenciones para un sistema HRM español por WhatsApp.
Analiza el mensaje del empleado y responde ÚNICAMENTE con un JSON válido (sin markdown):
{
  "intent": "<una de: fichar_entrada, fichar_salida, inicio_parada, fin_parada, solicitar_vacaciones, consultar_saldo_vacaciones, confirmar_documento, resumen_dia, desconocido>",
  "entities": { "fecha_inicio": "YYYY-MM-DD", "fecha_fin": "YYYY-MM-DD", "motivo": "..." },
  "confidence": 0.0-1.0
}
Reglas base:
- "entrada", "fiché", "empiezo", "llego" -> fichar_entrada
- "salida", "termino", "me voy" -> fichar_salida
- "parada", "descanso", "pausa", "empiezo parada" -> inicio_parada
- "vuelvo", "fin parada", "termino parada", "acabo parada" -> fin_parada
- vacaciones, días libres, permiso -> solicitar_vacaciones (extrae fechas si las hay)
- saldo vacaciones, cuántos días tengo -> consultar_saldo_vacaciones
- "recibido", "acepto", "confirmo" documento/nómina -> confirmar_documento
- resumen del día, resumen hoy, qué he fichado hoy -> resumen_dia
- Si no encaja: desconocido con entities vacío
"""


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

    def _system_prompt(self) -> str:
        extra = ""
        if self._session:
            extra = build_rules_prompt(self._session)
        if extra:
            return f"{BASE_SYSTEM_PROMPT}\n\n{extra}"
        return BASE_SYSTEM_PROMPT

    async def extract_intent(self, message_text: str) -> OllamaIntentResponse:
        started = time.perf_counter()
        prompt_tokens = 0
        completion_tokens = 0
        success = True
        intent: OllamaIntentResponse
        try:
            intent, prompt_tokens, completion_tokens = await self._call_ollama(
                message_text
            )
        except Exception:
            success = False
            intent = self._keyword_fallback(message_text)
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
        self, message_text: str
    ) -> tuple[OllamaIntentResponse, int, int]:
        payload = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": message_text.strip()},
            ],
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
    def _keyword_fallback(message_text: str) -> OllamaIntentResponse:
        t = message_text.lower()
        if any(w in t for w in ("entrada", "fiché", "fiche", "empiezo", "llego")):
            return OllamaIntentResponse(intent="fichar_entrada", confidence=0.7)
        if any(w in t for w in ("salida", "termino", "me voy")):
            return OllamaIntentResponse(intent="fichar_salida", confidence=0.7)
        if any(
            w in t
            for w in ("inicio parada", "empiezo parada", "empiezo descanso", "pausa")
        ) or (("parada" in t or "descanso" in t) and "fin" not in t and "termin" not in t):
            return OllamaIntentResponse(intent="inicio_parada", confidence=0.65)
        if any(
            w in t
            for w in ("fin parada", "termino parada", "acabo parada", "vuelvo del descanso")
        ):
            return OllamaIntentResponse(intent="fin_parada", confidence=0.65)
        if any(w in t for w in ("vacaciones", "días libres", "dia libre", "permiso")):
            return OllamaIntentResponse(intent="solicitar_vacaciones", confidence=0.6)
        if "saldo" in t or "cuántos días" in t or "cuantos dias" in t:
            return OllamaIntentResponse(intent="consultar_saldo_vacaciones", confidence=0.6)
        if any(w in t for w in ("recibido", "acepto", "confirmo")):
            return OllamaIntentResponse(intent="confirmar_documento", confidence=0.6)
        if any(
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
