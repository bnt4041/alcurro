import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas.ollama import OllamaIntentResponse

SYSTEM_PROMPT = """Eres un clasificador de intenciones para un sistema HRM español por WhatsApp.
Analiza el mensaje del empleado y responde ÚNICAMENTE con un JSON válido (sin markdown):
{
  "intent": "<una de: fichar_entrada, fichar_salida, solicitar_vacaciones, consultar_saldo_vacaciones, confirmar_documento, desconocido>",
  "entities": { "fecha_inicio": "YYYY-MM-DD", "fecha_fin": "YYYY-MM-DD", "motivo": "..." },
  "confidence": 0.0-1.0
}
Reglas:
- "entrada", "fiché", "empiezo", "llego" -> fichar_entrada
- "salida", "termino", "me voy" -> fichar_salida
- vacaciones, días libres, permiso -> solicitar_vacaciones (extrae fechas si las hay)
- saldo vacaciones, cuántos días tengo -> consultar_saldo_vacaciones
- "recibido", "acepto", "confirmo" documento/nómina -> confirmar_documento
- Si no encaja: desconocido con entities vacío
"""


class OllamaService:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model

    async def extract_intent(self, message_text: str) -> OllamaIntentResponse:
        try:
            return await self._call_ollama(message_text)
        except Exception:
            return self._keyword_fallback(message_text)

    async def _call_ollama(self, message_text: str) -> OllamaIntentResponse:
        payload = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
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
        parsed = self._parse_json_content(content)
        return OllamaIntentResponse.model_validate(parsed)

    @staticmethod
    def _keyword_fallback(message_text: str) -> OllamaIntentResponse:
        t = message_text.lower()
        if any(w in t for w in ("entrada", "fiché", "fiche", "empiezo", "llego")):
            return OllamaIntentResponse(intent="fichar_entrada", confidence=0.7)
        if any(w in t for w in ("salida", "termino", "me voy")):
            return OllamaIntentResponse(intent="fichar_salida", confidence=0.7)
        if any(w in t for w in ("vacaciones", "días libres", "dia libre", "permiso")):
            return OllamaIntentResponse(intent="solicitar_vacaciones", confidence=0.6)
        if "saldo" in t or "cuántos días" in t or "cuantos dias" in t:
            return OllamaIntentResponse(intent="consultar_saldo_vacaciones", confidence=0.6)
        if any(w in t for w in ("recibido", "acepto", "confirmo")):
            return OllamaIntentResponse(intent="confirmar_documento", confidence=0.6)
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
