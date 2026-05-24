import base64

import httpx
from sqlmodel import Session

from app.schemas.whatsapp import format_phone_for_gowa
from app.services.settings_service import SettingsService


class GoWAService:
    """Cliente HTTP hacia la instancia goWA compartida de plataforma."""

    def __init__(self, session: Session, *, country_iso: str = "ES") -> None:
        self._session = session
        self._country_iso = (country_iso or "ES").upper()
        settings = SettingsService(session).get_or_create()
        self._send_url = settings.gowa_send_url
        self._basic_auth = settings.gowa_basic_auth
        self._device_id = settings.gowa_device_id

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._basic_auth and ":" in self._basic_auth:
            token = base64.b64encode(self._basic_auth.encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        if self._device_id:
            headers["X-Device-Id"] = self._device_id
        return headers

    def _link_send_url(self) -> str:
        if not self._send_url:
            return ""
        if self._send_url.endswith("/send/message"):
            return self._send_url[: -len("/send/message")] + "/send/link"
        return self._send_url.replace("/send/message", "/send/link")

    async def send_text(self, phone: str, text: str) -> dict:
        if not self._send_url:
            raise RuntimeError("WhatsApp no configurado en la plataforma")
        payload = {
            "phone": format_phone_for_gowa(phone, self._country_iso),
            "message": text,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._send_url,
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"ok": True}

    async def send_link(self, phone: str, url: str, caption: str) -> dict:
        """Envía enlace clicable (goWA /send/link) con la URL también en el texto."""
        link_url = self._link_send_url()
        if not link_url:
            raise RuntimeError("WhatsApp no configurado en la plataforma")
        payload = {
            "phone": format_phone_for_gowa(phone, self._country_iso),
            "link": url,
            "caption": caption,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                link_url,
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"ok": True}
