"""Reverse geocoding via Nominatim (OpenStreetMap) — free, no API key required."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_HEADERS = {"User-Agent": "Alcurro-HRM/1.0 (contact@alcurro.com)"}


async def reverse_geocode(lat: float, lng: float) -> str | None:
    """Return a short human-readable address for the given coordinates, or None."""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                _NOMINATIM_URL,
                params={"lat": lat, "lon": lng, "format": "json", "zoom": 17},
                headers=_HEADERS,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return _format_address(data)
    except Exception as exc:
        logger.debug("reverse_geocode error: %s", exc)
        return None


def _format_address(data: dict) -> str | None:
    addr = data.get("address", {})
    parts: list[str] = []

    road = addr.get("road") or addr.get("pedestrian") or addr.get("path") or ""
    number = addr.get("house_number", "")
    if road:
        parts.append(f"{road}{' ' + number if number else ''}")

    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
        or ""
    )
    if city:
        parts.append(city)

    if parts:
        return ", ".join(parts)

    display = data.get("display_name", "")
    return display[:200] if display else None
