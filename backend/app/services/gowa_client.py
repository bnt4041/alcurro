"""Cliente HTTP hacia la instancia goWA compartida (Basic Auth + X-Device-Id en servidor)."""

from __future__ import annotations

import base64
import os
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlmodel import Session

from app.models.settings import SystemSettings


def _parse_basic_auth(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise HTTPException(
            status_code=500,
            detail="Credenciales goWA mal configuradas",
        )
    user, password = value.split(":", 1)
    return user, password


def _in_docker() -> bool:
    return os.path.exists("/.dockerenv")


def _docker_gowa_host(netloc: str) -> str:
    """Dentro de Docker, localhost no llega al contenedor goWA."""
    if not _in_docker():
        return netloc
    host = netloc.rsplit(":", 1)[0] if ":" in netloc else netloc
    port = netloc.rsplit(":", 1)[1] if ":" in netloc else "3000"
    if host in ("localhost", "127.0.0.1"):
        return f"gowa:{port}"
    return netloc


def gowa_api_base(settings: SystemSettings) -> str:
    """URL base interna para la API (p. ej. http://gowa:3000)."""
    if settings.gowa_send_url:
        parsed = urlparse(settings.gowa_send_url)
        if parsed.scheme and parsed.netloc:
            netloc = _docker_gowa_host(parsed.netloc)
            return f"{parsed.scheme}://{netloc}".rstrip("/")
    ui = settings.gowa_ui_url or "http://localhost:3000"
    parsed = urlparse(ui)
    netloc = _docker_gowa_host(parsed.netloc or "localhost:3000")
    return f"{parsed.scheme}://{netloc}".rstrip("/")


class SharedGoWAClient:
    """Un único WhatsApp de plataforma (system_settings id=1)."""

    def __init__(self, settings: SystemSettings, session: Session | None = None) -> None:
        self._settings = settings
        self._session = session
        self._base = gowa_api_base(settings)
        user, password = _parse_basic_auth(settings.gowa_basic_auth or "admin:admin")
        self._auth = httpx.BasicAuth(user, password)
        self._device_id: str | None = settings.gowa_device_id

    def _headers(self, device_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        did = device_id or self._device_id
        if did:
            headers["X-Device-Id"] = did
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        device_id: str | None = None,
        json_body: dict | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.request(
                method,
                f"{self._base}{path}",
                auth=self._auth,
                headers=self._headers(device_id),
                json=json_body,
            )

    async def _get_json(self, path: str, *, device_id: str | None = None) -> dict:
        response = await self._request("GET", path, device_id=device_id)
        response.raise_for_status()
        return response.json()

    async def _get_bytes(self, path: str, *, device_id: str | None = None) -> bytes:
        response = await self._request("GET", path, device_id=device_id)
        response.raise_for_status()
        return response.content

    def _persist_device_id(self, device_id: str) -> None:
        if self._settings.gowa_device_id == device_id:
            return
        self._settings.gowa_device_id = device_id
        self._device_id = device_id
        if self._session:
            self._session.add(self._settings)
            self._session.commit()
            self._session.refresh(self._settings)

    async def list_devices(self) -> list[dict]:
        data = await self._get_json("/devices")
        results = data.get("results")
        return results if isinstance(results, list) else []

    async def ensure_device(self) -> str:
        devices = await self.list_devices()

        if self._device_id:
            for d in devices:
                if str(d.get("id")) == self._device_id:
                    return self._device_id

        if devices:
            device_id = str(devices[0].get("id") or "")
            if device_id:
                self._persist_device_id(device_id)
                return device_id

        response = await self._request("POST", "/devices", json_body={})
        if response.status_code >= 400:
            try:
                err = response.json()
                msg = err.get("message") or response.text
            except Exception:
                msg = response.text
            raise HTTPException(
                status_code=502,
                detail=f"No se pudo registrar el dispositivo en goWA: {msg}",
            )
        data = response.json()
        results = data.get("results") if isinstance(data.get("results"), dict) else {}
        device_id = str(results.get("id") or "")
        if not device_id:
            raise HTTPException(
                status_code=502,
                detail="goWA no devolvió un identificador de dispositivo",
            )
        self._persist_device_id(device_id)
        return device_id

    async def device_state(self, device_id: str | None = None) -> str | None:
        did = device_id or self._device_id
        if not did:
            return None
        for d in await self.list_devices():
            if str(d.get("id")) == did:
                return str(d.get("state") or "")
        return None

    async def is_whatsapp_logged_in(self, device_id: str | None = None) -> bool:
        did = device_id or self._device_id
        if not did:
            return False

        state = await self.device_state(did)
        if state == "logged_in":
            return True
        if state in ("disconnected", ""):
            return False

        try:
            data = await self._get_json("/user/info", device_id=did)
        except httpx.HTTPError:
            return False
        if data.get("code") != "SUCCESS":
            return False
        results = data.get("results")
        if not isinstance(results, dict):
            return False
        devices = results.get("devices")
        if isinstance(devices, list) and len(devices) > 0:
            return True
        return bool(results.get("verified_name"))

    async def is_linked(self) -> bool:
        try:
            await self.ensure_device()
        except HTTPException:
            return False
        return await self.is_whatsapp_logged_in()

    async def fetch_qr(self) -> tuple[str | None, int | None, str | None]:
        device_id = await self.ensure_device()

        if await self.is_whatsapp_logged_in(device_id):
            return None, None, "WhatsApp ya está vinculado."

        response = await self._request("GET", "/app/login", device_id=device_id)

        if response.status_code == 400:
            try:
                body = response.json()
            except Exception:
                body = {}
            msg = str(body.get("message") or "")
            code = str(body.get("code") or "")
            lower = msg.lower()
            if "already" in lower or "signed in" in lower or "logged in" in lower:
                return None, None, "WhatsApp ya está vinculado."
            if code == "DEVICE_ID_REQUIRED":
                raise HTTPException(
                    status_code=502,
                    detail="goWA requiere dispositivo; inténtalo de nuevo en unos segundos.",
                )
            raise HTTPException(
                status_code=502,
                detail=msg or "goWA rechazó la solicitud de QR (400)",
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"goWA no respondió al solicitar el QR ({response.status_code})",
            )

        data = response.json()
        results = data.get("results") if isinstance(data.get("results"), dict) else {}
        qr_link = results.get("qr_link")
        duration = results.get("qr_duration")

        if not qr_link:
            msg = data.get("message") or "No hay código QR disponible"
            return None, None, str(msg)

        path = urlparse(str(qr_link)).path
        if not path:
            raise HTTPException(status_code=502, detail="goWA devolvió un QR sin URL válida")

        try:
            raw = await self._get_bytes(path, device_id=device_id)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="No se pudo descargar la imagen del código QR",
            ) from exc

        mime = "image/png"
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            mime = "image/jpeg"
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}", int(duration) if duration else 30, None


async def get_shared_whatsapp_session(session: Session) -> dict:
    from app.services.settings_service import SettingsService

    settings = SettingsService(session).get_or_create()
    out: dict = {
        "configured": bool(settings.gowa_send_url),
        "connected": False,
        "qr_image": None,
        "qr_expires_in": None,
        "message": None,
    }

    if not settings.gowa_send_url:
        out["message"] = "Configura la URL de goWA en el panel de administración."
        return out

    client = SharedGoWAClient(settings, session=session)
    try:
        linked = await client.is_linked()
        out["connected"] = linked
        if linked:
            out["message"] = (
                "WhatsApp de alcurro vinculado. Todas las cuentas usan esta línea."
            )
            return out

        qr_image, expires, msg = await client.fetch_qr()
        if not qr_image and not msg:
            msg = "Escanea el código QR con WhatsApp (Dispositivos vinculados)."
        out["qr_image"] = qr_image
        out["qr_expires_in"] = expires
        out["message"] = msg
        return out
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al consultar WhatsApp: {exc}",
        ) from exc
