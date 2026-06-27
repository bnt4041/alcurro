"""Esquemas Pydantic v2 — formato oficial goWA (aldinokemal)."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


def _extract_location_dict(data: dict[str, Any]) -> dict[str, Any] | None:
    """Normaliza ubicación desde distintos formatos de goWA / WhatsApp Web.
    
    Soporta múltiples formatos de ubicación:
    - {latitude, longitude}
    - {degreesLatitude, degreesLongitude}
    - {lat, lng}
    - {location: {...}}
    - {locationMessage: {...}}
    - {liveLocationMessage: {...}}
    - {msg: {location: {...}}}
    También maneja strings numéricos de coordenadas.
    """
    if not isinstance(data, dict):
        return None

    top_live = _looks_live(data)
    candidates: list[tuple[dict[str, Any], bool]] = [(data, top_live)]
    _live_keys = ("live_location", "liveLocationMessage")
    for key in (
        "location",
        "live_location",
        "locationMessage",
        "liveLocationMessage",
        "msg",
        "message",
    ):
        nested = data.get(key)
        if isinstance(nested, dict):
            candidates.append(
                (nested, key in _live_keys or top_live or _looks_live(nested))
            )

    # También buscar en valores que sean dict con coordenadas
    for v in data.values():
        if isinstance(v, dict) and any(
            k in v for k in ("latitude", "lat", "degreesLatitude", "longitude", "lng", "lon", "degreesLongitude")
        ):
            candidates.append((v, top_live or _looks_live(v)))

    for block, block_live in candidates:
        lat = (
            block.get("latitude")
            or block.get("degreesLatitude")
            or block.get("lat")
        )
        lng = (
            block.get("longitude")
            or block.get("degreesLongitude")
            or block.get("lng")
            or block.get("lon")
        )
        if lat is not None and lng is not None:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                # Validar rango GPS
                if -90 <= lat_f <= 90 and -180 <= lng_f <= 180:
                    return {
                        "latitude": lat_f,
                        "longitude": lng_f,
                        "name": block.get("name"),
                        "address": block.get("address"),
                        "is_live": bool(
                            block_live
                            or block.get("is_live")
                            or data.get("is_live")
                        ),
                    }
            except (TypeError, ValueError):
                continue
    return None


def _looks_live(data: dict[str, Any]) -> bool:
    """Heurística: el bloque corresponde a una ubicación en tiempo real."""
    t = str(
        data.get("type") or data.get("message_type") or data.get("messageType") or ""
    ).lower()
    if "live" in t:
        return True
    return any(
        isinstance(k, str) and "live" in k.lower() and "location" in k.lower()
        for k in data
    )


class GoWALocation(BaseModel):
    latitude: float
    longitude: float
    name: str | None = None
    address: str | None = None
    is_live: bool = False

    @model_validator(mode="before")
    @classmethod
    def from_gowa_coords(cls, data: Any) -> Any:
        if isinstance(data, dict):
            parsed = _extract_location_dict(data)
            if parsed:
                return parsed
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
        if self.location is not None:
            return True
        t = (self.type or "").lower()
        if any(
            x in t
            for x in (
                "location",
                "live_location",
                "locationmessage",
                "livelocation",
            )
        ):
            return True
        # Si el body/text contiene solo coordenadas numéricas, podría ser ubicación
        body = (self.body or self.text or "").strip()
        if body:
            parts = body.replace(",", " ").split()
            if len(parts) == 2:
                try:
                    lat = float(parts[0])
                    lng = float(parts[1])
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return True
                except (TypeError, ValueError):
                    pass
        return False

    @property
    def is_media(self) -> bool:
        if self.media_path:
            return True
        t = (self.type or "").lower()
        return t in (
            "image",
            "document",
            "video",
            "sticker",
            "audio",
            "file",
            "documentmessage",
            "imagemessage",
        )

    @property
    def is_text(self) -> bool:
        if self.is_location or self.is_media:
            return False
        return bool(self.plain_text)


class GoWAWebhookPayload(BaseModel):
    """Soporta webhook goWA (`event` + `payload`) y formato simplificado de pruebas."""

    event: str | None = None
    device_id: str | None = None
    payload: dict[str, Any] | None = None
    message: GoWAMessage | None = None
    sender: str | None = None
    phone: str | None = None
    from_me: bool = False

    @model_validator(mode="before")
    @classmethod
    def adapt_gowa_event(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Evento dedicado de ubicación (varias versiones de goWA)
        if data.get("event") in (
            "location", "live_location", "message.location",
            "locationMessage", "liveLocationMessage",
        ):
            p = data.get("payload") if isinstance(data.get("payload"), dict) else data
            loc = _extract_location_dict(p or {})
            if loc and data.get("event") in ("live_location", "liveLocationMessage"):
                loc["is_live"] = True
            sender = (
                p.get("from") if isinstance(p, dict) else None
            ) or data.get("sender") or data.get("phone")
            if loc:
                return {
                    "event": "message",
                    "message": {
                        "from": sender or "",
                        "id": (p or {}).get("id") if isinstance(p, dict) else None,
                        "type": "location",
                        "location": loc,
                    },
                }
            # Si es evento de ubicación pero no pudimos extraer coordenadas,
            # intentamos con el payload completo
            if isinstance(p, dict):
                loc2 = _extract_location_dict(p)
                if loc2 and data.get("event") in ("live_location", "liveLocationMessage"):
                    loc2["is_live"] = True
                if loc2:
                    return {
                        "event": "message",
                        "message": {
                            "from": sender or "",
                            "id": p.get("id"),
                            "type": "location",
                            "location": loc2,
                        },
                    }

        if data.get("event") == "message" and isinstance(data.get("payload"), dict):
            p = data["payload"]
            from_me = bool(p.get("fromMe") or p.get("from_me") or p.get("isFromMe"))
            msg_type = (p.get("type") or "text").lower()
            loc = _extract_location_dict(p)
            media_path = (
                p.get("path")
                or p.get("media_path")
                or p.get("file_path")
            )
            if not media_path and isinstance(p.get("image"), dict):
                media_path = p["image"].get("path")
            if not media_path and isinstance(p.get("document"), dict):
                media_path = p["document"].get("path")
            if not media_path and isinstance(p.get("documentMessage"), dict):
                media_path = p["documentMessage"].get("path")
            return {
                "event": data.get("event"),
                "device_id": data.get("device_id"),
                "from_me": from_me,
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
            msg = self.message
            if msg.is_location and msg.location is None and self.payload:
                loc = _extract_location_dict(self.payload)
                if loc:
                    return GoWAMessage.model_validate(
                        {**msg.model_dump(by_alias=True), "location": loc, "type": "location"}
                    )
            # Si el mensaje es texto pero contiene coordenadas GPS, intentar tratarlo como ubicación
            if not msg.is_location and msg.plain_text and self.payload:
                loc = _extract_location_dict(self.payload)
                if loc:
                    return GoWAMessage.model_validate(
                        {**msg.model_dump(by_alias=True), "location": loc, "type": "location"}
                    )
            return msg
        if self.payload:
            loc = _extract_location_dict(self.payload)
            if loc:
                return GoWAMessage.model_validate(
                    {
                        "from": self.payload.get("from", self.sender or self.phone or ""),
                        "type": "location",
                        "location": loc,
                    }
                )
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
        if self.event and self.event not in (
            "message",
            "location",
            "live_location",
            "message.location",
            "locationMessage",
            "liveLocationMessage",
            None,
        ):
            if self.event in ("status", "ack", "receipt", "connection"):
                return False
        # Ignorar mensajes enviados por el propio bot (outgoing)
        if self.from_me:
            return False
        p = self.payload or {}
        if p.get("fromMe") or p.get("from_me") or p.get("isFromMe"):
            return False
        return True


def normalize_phone(value: str) -> str:
    """Extrae dígitos del JID WhatsApp (ej. 34600111222@s.whatsapp.net)."""
    local = value.split("@")[0]
    return "".join(c for c in local if c.isdigit())


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
    digits = normalize_phone(phone)
    if not digits:
        return digits
    if digits.startswith("00"):
        digits = digits[2:]
    dial = dial_code(country_iso)
    if len(digits) >= 11 and digits.startswith(dial):
        return digits
    if len(digits) == 9 and digits[0] in "6789":
        return dial + digits
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
