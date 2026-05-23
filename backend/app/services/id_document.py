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
