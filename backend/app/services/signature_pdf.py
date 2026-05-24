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
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlmodel import Session, select

from app.models.signature import (
    SignatureEnvelope,
    SignatureEvent,
    SignatureSigner,
)
from app.models.tenant import Tenant

STAMP_UNIT = 21 * mm
# Proporción 3:2 apaisada; al rotar 90° el lado largo queda a lo largo de la página
STAMP_LONG = STAMP_UNIT * 3  # 63 mm — vertical en la página
STAMP_SHORT = STAMP_UNIT * 2  # 42 mm — profundidad en el margen
STAMP_MARGIN = 4 * mm
STAMP_RGBA_GREEN = (30, 107, 79, 255)
STAMP_RGBA_TEXT = (51, 65, 85, 255)
STAMP_RGBA_MUTED = (100, 116, 139, 255)
STAMP_DPI = 120


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
    stamped = _apply_lateral_stamp_all_pages(merged, envelope, signers)
    signed_pdf.write_bytes(stamped)
    signed_hash = hashlib.sha256(stamped).hexdigest()

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


def _fmt_signed_at(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M UTC")


def _mm_to_px(value_mm: float) -> int:
    return max(1, int(value_mm / 25.4 * STAMP_DPI))


def _load_stamp_fonts() -> tuple:
    from PIL import ImageFont

    paths = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    sizes = (11, 9, 7)
    fonts = []
    for path, size in zip(paths, sizes, strict=True):
        try:
            fonts.append(ImageFont.truetype(path, size))
        except OSError:
            fonts.append(ImageFont.load_default())
    return tuple(fonts)


def _render_stamp_png(
    envelope: SignatureEnvelope,
    signers: list[SignatureSigner],
    document_hash: str,
) -> bytes:
    """Sello 3:2 (largo×ancho) con fondo transparente; firmas en fila."""
    from PIL import Image, ImageDraw

    long_px = _mm_to_px(STAMP_LONG / mm)
    short_px = _mm_to_px(STAMP_SHORT / mm)
    pad = _mm_to_px(2.2)

    img = Image.new("RGBA", (long_px, short_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle(
        (1, 1, long_px - 2, short_px - 2),
        outline=STAMP_RGBA_GREEN,
        width=2,
    )

    font_b, font, font_s = _load_stamp_fonts()
    signed = [s for s in sorted(signers, key=lambda z: z.sign_order) if s.signed_at]

    draw.text((pad, pad), "SELLO DE FIRMA", fill=STAMP_RGBA_GREEN, font=font_b)
    draw.text(
        (pad, pad + _mm_to_px(4)),
        envelope.reference[:36],
        fill=STAMP_RGBA_GREEN,
        font=font,
    )

    sig_y = _mm_to_px(13)
    sig_h = _mm_to_px(9)
    n = max(len(signed), 1)
    cell_w = (long_px - 2 * pad) / n

    for i, signer in enumerate(signed):
        cell_x = pad + i * cell_w
        cx = cell_x + cell_w / 2
        sig_w = min(int(cell_w - _mm_to_px(1.2)), _mm_to_px(16))
        if signer.signature_path and Path(signer.signature_path).exists():
            try:
                sig = Image.open(signer.signature_path).convert("RGBA")
                sig.thumbnail((sig_w, sig_h), Image.Resampling.LANCZOS)
                paste_x = int(cx - sig.width / 2)
                img.paste(sig, (paste_x, sig_y), sig)
            except Exception:
                pass
        name = (signer.signer_name or signer.full_name or "")[:16]
        ts = _fmt_signed_at(signer.signed_at)
        if len(ts) > 16:
            ts = ts[0:11] + " " + ts[12:16]
        name_bbox = draw.textbbox((0, 0), name, font=font_s)
        name_w = name_bbox[2] - name_bbox[0]
        draw.text(
            (cx - name_w / 2, sig_y + sig_h + _mm_to_px(0.8)),
            name,
            fill=STAMP_RGBA_TEXT,
            font=font_s,
        )
        ts_bbox = draw.textbbox((0, 0), ts, font=font_s)
        ts_w = ts_bbox[2] - ts_bbox[0]
        draw.text(
            (cx - ts_w / 2, sig_y + sig_h + _mm_to_px(3.2)),
            ts,
            fill=STAMP_RGBA_MUTED,
            font=font_s,
        )

    hash_y = short_px - _mm_to_px(11)
    draw.text(
        (pad, hash_y),
        f"SHA-256: {document_hash[:30]}",
        fill=STAMP_RGBA_TEXT,
        font=font_s,
    )
    draw.text(
        (pad, hash_y + _mm_to_px(2.8)),
        document_hash[30:58],
        fill=STAMP_RGBA_TEXT,
        font=font_s,
    )
    draw.text(
        (pad, short_px - _mm_to_px(3.5)),
        "alcurro HRM",
        fill=STAMP_RGBA_MUTED,
        font=font_s,
    )

    # Rotar para colocar el lado largo a lo largo de la página
    img = img.rotate(90, expand=True)

    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _stamp_png_to_pdf(png_bytes: bytes) -> bytes:
    """PDF del tamaño del sello con la PNG y transparencia."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(STAMP_SHORT, STAMP_LONG))
    c.drawImage(
        ImageReader(BytesIO(png_bytes)),
        0,
        0,
        width=STAMP_SHORT,
        height=STAMP_LONG,
        mask="auto",
    )
    c.save()
    return buf.getvalue()


def _apply_lateral_stamp_all_pages(
    pdf_bytes: bytes,
    envelope: SignatureEnvelope,
    signers: list[SignatureSigner],
) -> bytes:
    """Estampa el sello lateral en cada página del PDF."""
    try:
        from pypdf import PdfReader, PdfWriter, Transformation
    except ImportError:
        return pdf_bytes

    document_hash = hashlib.sha256(pdf_bytes).hexdigest()
    stamp_png = _render_stamp_png(envelope, signers, document_hash)
    stamp_pdf = _stamp_png_to_pdf(stamp_png)
    stamp_page = PdfReader(BytesIO(stamp_pdf)).pages[0]

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        page_h = float(page.mediabox.height)
        y = (page_h - STAMP_LONG) / 2
        page.merge_transformed_page(
            stamp_page,
            Transformation().translate(STAMP_MARGIN, y),
        )
        writer.add_page(page)

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
