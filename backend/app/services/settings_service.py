from datetime import datetime

import httpx
from sqlmodel import Session, select

from app.config import get_settings
from app.models.settings import SystemSettings
from app.schemas.crud import SystemSettingsRead, SystemSettingsUpdate


class SettingsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self) -> SystemSettings:
        row = self._session.get(SystemSettings, 1)
        if row:
            return row
        env = get_settings()
        row = SystemSettings(
            id=1,
            gowa_send_url="http://gowa:3000/send/message",
            gowa_basic_auth=env.gowa_basic_auth,
            gowa_webhook_url="http://backend:8000/webhook/whatsapp",
            gowa_ui_url="http://localhost:3000",
            ollama_base_url=env.ollama_base_url,
            ollama_model=env.ollama_model,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def read(self) -> SystemSettingsRead:
        return SystemSettingsRead.model_validate(self.get_or_create())

    def update(self, data: SystemSettingsUpdate) -> SystemSettingsRead:
        row = self.get_or_create()
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        row.updated_at = datetime.utcnow()
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return SystemSettingsRead.model_validate(row)

    async def test_gowa(self) -> tuple[bool, str, str | None]:
        from app.services.gowa_client import _in_docker, gowa_api_base

        s = self.get_or_create()
        base = gowa_api_base(s)
        user, password = (s.gowa_basic_auth or "admin:admin").split(":", 1)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{base}/devices",
                    auth=httpx.BasicAuth(user, password),
                )
            if r.status_code < 500:
                return True, f"goWA accesible en {base}", None
            return False, f"goWA respondió {r.status_code}", None
        except Exception as exc:
            hint = (
                " Usa http://gowa:3000/send/message como URL de envío dentro de Docker."
                if _in_docker() and "localhost" in (s.gowa_send_url or "")
                else ""
            )
            return False, f"No se pudo conectar con goWA.{hint}", str(exc)

    async def test_ollama(self) -> tuple[bool, str, str | None]:
        s = self.get_or_create()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{s.ollama_base_url.rstrip('/')}/api/tags")
            if r.status_code == 200:
                models = [m.get("name", "") for m in r.json().get("models", [])]
                return True, f"Ollama OK — modelos: {', '.join(models[:5]) or 'ninguno'}", None
            return False, f"Ollama respondió {r.status_code}", None
        except Exception as exc:
            return False, "No se pudo conectar con Ollama", str(exc)
