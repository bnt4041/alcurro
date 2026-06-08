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

    def send_text_sync(self, phone: str, text: str) -> dict:
        if not self._send_url:
            raise RuntimeError("WhatsApp no configurado en la plataforma")
        payload = {
            "phone": format_phone_for_gowa(phone, self._country_iso),
            "message": text,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
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

    def _media_send_base_url(self) -> str:
        if not self._send_url:
            return ""
        import re
        return re.sub(r"/send/message$", "", self._send_url)

    def send_file_sync(
        self, phone: str, file_bytes: bytes, filename: str, caption: str = ""
    ) -> dict:
        """Envía un archivo (no imagen) por WhatsApp vía goWA /send/file."""
        base = self._media_send_base_url()
        if not base:
            raise RuntimeError("WhatsApp no configurado en la plataforma")
        url = f"{base}/send/file"
        import mimetypes
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                data={"phone": format_phone_for_gowa(phone, self._country_iso), "caption": caption},
                files={"file": (filename, file_bytes, content_type)},
                headers={k: v for k, v in self._headers().items() if k != "Content-Type"},
            )
            response.raise_for_status()
            return response.json() if response.content else {"ok": True}

    def send_image_sync(
        self, phone: str, image_bytes: bytes, filename: str, caption: str = ""
    ) -> dict:
        """Envía una imagen por WhatsApp vía goWA /send/image."""
        base = self._media_send_base_url()
        if not base:
            raise RuntimeError("WhatsApp no configurado en la plataforma")
        url = f"{base}/send/image"
        import mimetypes
        content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                data={"phone": format_phone_for_gowa(phone, self._country_iso), "caption": caption},
                files={"image": (filename, image_bytes, content_type)},
                headers={k: v for k, v in self._headers().items() if k != "Content-Type"},
            )
            response.raise_for_status()
            return response.json() if response.content else {"ok": True}

    async def download_media(self, media_path: str) -> bytes | None:
        """Descarga un archivo multimedia desde goWA vía HTTP.
        
        goWA sirve archivos en /statics/media/{filename}.
        media_path puede ser ruta completa (/app/statics/media/xxx.jpeg) o solo nombre.
        """
        from pathlib import Path
        import re

        # Extraer el nombre del archivo
        filename = Path(media_path).name

        # Construir URL base de goWA desde self._send_url
        if not self._send_url:
            return None
        # self._send_url es como http://gowa:3000/send/message
        base = re.sub(r"/send/message$", "", self._send_url)
        url = f"{base}/statics/media/{filename}"

        headers = {}
        if self._basic_auth and ":" in self._basic_auth:
            token = base64.b64encode(self._basic_auth.encode()).decode()
            headers["Authorization"] = f"Basic {token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.content
        except Exception:
            return None
