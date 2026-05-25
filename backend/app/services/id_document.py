"""Validación y normalización de DNI/NIE español."""

from __future__ import annotations

import re

_ID_DOC_RE = re.compile(r"^(?:\d{8}|[XYZ]\d{7})[A-Z]$", re.IGNORECASE)


def normalize_id_document(value: str) -> str:
    return value.strip().upper().replace(" ", "").replace("-", "")


def validate_id_document(value: str) -> str:
    normalized = normalize_id_document(value)
    if not _ID_DOC_RE.match(normalized):
        raise ValueError("DNI/NIE no válido (formato esperado: 12345678Z o X1234567L)")
    return normalized


_FIND_ID_RE = re.compile(r"\b(\d{8}|[XYZ]\d{7})[A-Z]\b", re.IGNORECASE)


def find_id_documents_in_text(text: str) -> list[str]:
    """Extrae DNI/NIE válidos de un texto (p. ej. página de nómina)."""
    found: list[str] = []
    for match in _FIND_ID_RE.finditer(text or ""):
        try:
            doc = validate_id_document(match.group(0))
        except ValueError:
            continue
        if doc not in found:
            found.append(doc)
    return found
