"""Empaquetado ZIP de documentos."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from app.models.documents import DocumentDelivery


def build_documents_zip(rows: list[DocumentDelivery]) -> tuple[BytesIO, int]:
    buf = BytesIO()
    added = 0
    used_names: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            path = Path(row.file_path)
            if not path.is_file():
                continue
            base = row.file_name or path.name
            arcname = base
            n = 1
            while arcname in used_names:
                stem = Path(base).stem
                suffix = Path(base).suffix
                arcname = f"{stem}_{n}{suffix}"
                n += 1
            used_names.add(arcname)
            zf.write(path, arcname)
            added += 1
    buf.seek(0)
    return buf, added
