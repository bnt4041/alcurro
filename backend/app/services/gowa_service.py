import base64

import httpx
from sqlmodel import Session

from app.models.tenant import Tenant
from app.schemas.whatsapp import format_phone_for_gowa


class GoWAService:
    """Cliente HTTP hacia goWA POST /send/message del tenant."""

    def __init__(self, tenant: Tenant) -> None:
        self._send_url = tenant.gowa_send_url or f"http://{tenant.gowa_host}:3000/send/message"
        self._basic_auth = tenant.gowa_basic_auth

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._basic_auth and ":" in self._basic_auth:
            token = base64.b64encode(self._basic_auth.encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers

    async def send_text(self, phone: str, text: str) -> dict:
        if not self._send_url:
            raise RuntimeError("goWA no provisionado para este tenant")
        payload = {
            "phone": format_phone_for_gowa(phone),
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
