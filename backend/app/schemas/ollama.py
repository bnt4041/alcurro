from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class OllamaIntentResponse(BaseModel):
    intent: str = Field(
        description=(
            "fichar_entrada | fichar_salida | solicitar_vacaciones | "
            "consultar_saldo_vacaciones | confirmar_documento | desconocido"
        )
    )
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

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
