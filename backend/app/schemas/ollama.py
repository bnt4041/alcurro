from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class OllamaIntentResponse(BaseModel):
    """Respuesta del orquestador conversacional (Ollama).

    El modelo decide en qué fase está la conversación:
    - "ask": necesita más información del usuario → message es una pregunta
    - "confirm": ha entendido la intención → message pide confirmación sí/no
    - "execute": la acción ya está confirmada → el sistema debe ejecutar intent
    """

    stage: Literal["ask", "confirm", "execute"] = Field(
        default="ask",
        description="Fase de la conversación: pedir más info, confirmar, o ejecutar",
    )
    intent: str = Field(
        default="desconocido",
        description=(
            "fichar_entrada | fichar_salida | inicio_parada | fin_parada | "
            "solicitar_vacaciones | consultar_saldo_vacaciones | confirmar_documento | "
            "resumen_dia | reportar_incidencia | desconocido"
        ),
    )
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str = Field(
        default="",
        description="Texto que el asistente envía al empleado en esta fase",
    )

    def get_date(self, key: str) -> date | None:
        raw = self.entities.get(key)
        if not raw:
            return None
        if isinstance(raw, date):
            return raw
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None
