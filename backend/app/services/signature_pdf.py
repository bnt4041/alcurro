"""Generación de PDF firmado y certificado de cumplimiento."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlmodel import Session, select

from app.models.signature import SignatureEnvelope, SignatureEvent, SignatureSigner
from app.models.tenant import Tenant


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_certificate_pdf(
    envelope: SignatureEnvelope,
    signers: list[SignatureSigner],
    tenant_name: str,
    events: list[SignatureEvent],
) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 25 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(25 * mm, y, "Certificado de firma electrónica")
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    lines = [
        f"Empresa: {tenant_name}",
        f"Referencia: {envelope.reference}",
        f"Documento: {envelope.title}",
        f"Hash original (SHA-256): {envelope.original_hash}",
        f"Estado: {envelope.status}",
        f"Completado: {envelope.completed_at or '—'}",
    ]
    for line in lines:
        c.drawString(25 * mm, y, line)
        y -= 6 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(25 * mm, y, "Firmantes")
    y -= 8 * mm
    c.setFont("Helvetica", 9)

    for s in sorted(signers, key=lambda x: x.sign_order):
        block = [
            f"{s.sign_order}. {s.signer_name or s.full_name} — DNI/NIE {s.id_document}",
            f"   Firmado: {s.signed_at} · IP: {s.ip_address or '—'}",
        ]
        for line in block:
            c.drawString(25 * mm, y, line)
            y -= 5 * mm
        if s.signature_path and Path(s.signature_path).exists():
            try:
                c.drawImage(
                    s.signature_path,
                    25 * mm,
                    y - 18 * mm,
                    width=50 * mm,
                    height=15 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                y -= 22 * mm
            except Exception:
                y -= 4 * mm
        y -= 2 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(25 * mm, y, "Cadena de auditoría")
    y -= 7 * mm
    c.setFont("Helvetica", 7)
    for ev in events[-15:]:
        line = f"{ev.created_at:%Y-%m-%d %H:%M} · {ev.event_type} · {ev.event_hash[:16]}…"
        c.drawString(25 * mm, y, line)
        y -= 4 * mm
        if y < 30 * mm:
            c.showPage()
            y = h - 25 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        25 * mm,
        15 * mm,
        "Documento generado por alcurro HRM. Firma simple con trazabilidad interna.",
    )
    c.save()
    return buf.getvalue()


def finalize_signed_pdf(
    session: Session,
    envelope: SignatureEnvelope,
    base_dir: Path,
) -> dict[str, str]:
    tenant = session.get(Tenant, envelope.tenant_id)
    tenant_name = tenant.name if tenant else "Empresa"

    signers = list(
        session.exec(
            select(SignatureSigner)
            .where(SignatureSigner.envelope_id == envelope.id)
            .order_by(SignatureSigner.sign_order)  # type: ignore[attr-defined]
        ).all()
    )
    events = list(
        session.exec(
            select(SignatureEvent)
            .where(SignatureEvent.envelope_id == envelope.id)
            .order_by(SignatureEvent.created_at)  # type: ignore[attr-defined]
        ).all()
    )

    cert_bytes = _build_certificate_pdf(envelope, signers, tenant_name, events)
    env_dir = base_dir / "firma" / f"envelope-{envelope.id}"
    env_dir.mkdir(parents=True, exist_ok=True)

    cert_pdf = env_dir / f"{envelope.reference}_cert.pdf"
    cert_json = env_dir / f"{envelope.reference}_cert.json"
    signed_pdf = env_dir / f"{envelope.reference}_signed.pdf"

    cert_pdf.write_bytes(cert_bytes)
    cert_json.write_text(
        json.dumps(
            {
                "reference": envelope.reference,
                "title": envelope.title,
                "original_hash": envelope.original_hash,
                "completed_at": envelope.completed_at.isoformat()
                if envelope.completed_at
                else None,
                "signers": [
                    {
                        "order": s.sign_order,
                        "name": s.signer_name or s.full_name,
                        "id_document": s.id_document,
                        "signed_at": s.signed_at.isoformat() if s.signed_at else None,
                        "ip": s.ip_address,
                        "signature_sha256": file_sha256(Path(s.signature_path))
                        if s.signature_path and Path(s.signature_path).exists()
                        else None,
                    }
                    for s in signers
                ],
                "audit_chain": [
                    {
                        "type": e.event_type,
                        "hash": e.event_hash,
                        "prev": e.prev_hash,
                        "at": e.created_at.isoformat(),
                    }
                    for e in events
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    original = Path(envelope.original_path)
    merged = _merge_original_and_certificate(original, cert_bytes)

    signed_pdf.write_bytes(merged)
    signed_hash = file_sha256(signed_pdf)

    return {
        "signed_path": str(signed_pdf),
        "signed_hash": signed_hash,
        "certificate_path": str(cert_pdf),
        "certificate_json_path": str(cert_json),
    }


def _merge_original_and_certificate(original: Path, cert_bytes: bytes) -> bytes:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return cert_bytes

    writer = PdfWriter()
    if original.exists() and original.stat().st_size > 0:
        suffix = original.suffix.lower()
        if suffix == ".pdf":
            try:
                reader = PdfReader(str(original))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception:
                pass
        elif suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            img_pdf = _image_to_pdf_bytes(original)
            if img_pdf:
                img_reader = PdfReader(BytesIO(img_pdf))
                for page in img_reader.pages:
                    writer.add_page(page)

    cert_reader = PdfReader(BytesIO(cert_bytes))
    for page in cert_reader.pages:
        writer.add_page(page)

    if len(writer.pages) == 0:
        return cert_bytes

    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _image_to_pdf_bytes(image_path: Path) -> bytes | None:
    try:
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return None
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    img = ImageReader(str(image_path))
    iw, ih = img.getSize()
    scale = min((w - 40 * mm) / iw, (h - 40 * mm) / ih)
    c.drawImage(
        img,
        20 * mm,
        h - 20 * mm - ih * scale,
        width=iw * scale,
        height=ih * scale,
        preserveAspectRatio=True,
        mask="auto",
    )
    c.save()
    return buf.getvalue()
