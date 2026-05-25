"""Esquemas Pydantic v2 — formato oficial goWA (aldinokemal)."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class GoWALocation(BaseModel):
    latitude: float
    longitude: float
    name: str | None = None
    address: str | None = None

    @model_validator(mode="before")
    @classmethod
    def from_gowa_coords(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        lat = data.get("latitude") or data.get("degreesLatitude")
        lng = data.get("longitude") or data.get("degreesLongitude")
        if lat is not None and lng is not None:
            return {
                "latitude": float(lat),
                "longitude": float(lng),
                "name": data.get("name"),
                "address": data.get("address"),
            }
        return data


class GoWAMessage(BaseModel):
    id: str | None = None
    from_number: str = Field(default="", alias="from")
    type: str = "text"
    text: str | None = None
    body: str | None = None
    location: GoWALocation | None = None
    caption: str | None = None
    media_path: str | None = None
    file_name: str | None = None
    mimetype: str | None = None

    model_config = {"populate_by_name": True}

    @property
    def plain_text(self) -> str | None:
        return (self.text or self.body or self.caption or "").strip() or None

    @property
    def is_location(self) -> bool:
        return self.location is not None

    @property
    def is_media(self) -> bool:
        if self.media_path:
            return True
        return self.type in ("image", "document", "video", "sticker", "audio")

    @property
    def is_text(self) -> bool:
        return bool(self.plain_text) and not self.is_location and not self.is_media


class GoWAWebhookPayload(BaseModel):
    """Soporta webhook goWA (`event` + `payload`) y formato simplificado de pruebas."""

    event: str | None = None
    device_id: str | None = None
    payload: dict[str, Any] | None = None
    message: GoWAMessage | None = None
    sender: str | None = None
    phone: str | None = None

    @model_validator(mode="before")
    @classmethod
    def adapt_gowa_event(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("event") == "message" and isinstance(data.get("payload"), dict):
            p = data["payload"]
            loc = p.get("location") or p.get("live_location")
            msg_type = p.get("type") or "text"
            media_path = (
                p.get("path")
                or p.get("media_path")
                or p.get("file_path")
                or (p.get("image") or {}).get("path")
                if isinstance(p.get("image"), dict)
                else None
            )
            if not media_path and isinstance(p.get("document"), dict):
                media_path = p["document"].get("path")
            return {
                "event": data.get("event"),
                "device_id": data.get("device_id"),
                "message": {
                    "from": p.get("from", ""),
                    "id": p.get("id"),
                    "type": msg_type,
                    "body": p.get("body"),
                    "text": p.get("text"),
                    "caption": p.get("caption"),
                    "location": loc,
                    "media_path": media_path,
                    "file_name": p.get("filename") or p.get("file_name"),
                    "mimetype": p.get("mimetype") or p.get("mime_type"),
                },
            }
        return data

    def resolve_message(self) -> GoWAMessage | None:
        if self.message:
            return self.message
        if self.sender or self.phone:
            return GoWAMessage.model_validate(
                {"from": self.sender or self.phone or "", "body": ""}
            )
        return None

    def resolve_phone(self) -> str | None:
        msg = self.resolve_message()
        if msg and msg.from_number:
            return normalize_phone(msg.from_number)
        if self.sender:
            return normalize_phone(self.sender)
        if self.phone:
            return normalize_phone(self.phone)
        return None

    def should_process(self) -> bool:
        if self.event and self.event != "message":
            return False
        return True


def normalize_phone(value: str) -> str:
    """Extrae dígitos del JID WhatsApp (ej. 34600111222@s.whatsapp.net)."""
    local = value.split("@")[0]
    return "".join(c for c in local if c.isdigit())


# Código de país ISO → prefijo internacional (ampliar según necesidad)
DIAL_BY_COUNTRY: dict[str, str] = {
    "ES": "34",
    "PT": "351",
    "FR": "33",
    "IT": "39",
    "DE": "49",
    "GB": "44",
    "UK": "44",
}


def dial_code(country_iso: str = "ES") -> str:
    iso = (country_iso or "ES").upper()
    if iso.isdigit():
        return iso
    return DIAL_BY_COUNTRY.get(iso, "34")


def normalize_mobile_digits(phone: str, country_iso: str = "ES") -> str:
    """
    Devuelve dígitos con prefijo internacional.
    Ej: 624230960 + ES → 34624230960
    """
    digits = normalize_phone(phone)
    if not digits:
        return digits
    if digits.startswith("00"):
        digits = digits[2:]
    dial = dial_code(country_iso)
    if len(digits) >= 11 and digits.startswith(dial):
        return digits
    # Móvil español sin prefijo: 9 dígitos empezando por 6–9
    if len(digits) == 9 and digits[0] in "6789":
        return dial + digits
    # 0624230960
    if len(digits) == 10 and digits[0] == "0" and digits[1] in "6789":
        return dial + digits[1:]
    return digits


def format_phone_for_gowa(phone: str, country_iso: str = "ES") -> str:
    if "@" in phone:
        return phone
    digits = normalize_mobile_digits(phone, country_iso)
    if not digits:
        raise ValueError("Teléfono no válido")
    return f"{digits}@s.whatsapp.net"
