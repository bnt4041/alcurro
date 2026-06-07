"""Genera el PDF de certificado de aceptación legal (todos los documentos en uno)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlmodel import Session

UPLOAD_DIR = Path("/app/uploads/legal")


@dataclass
class AcceptedDocData:
    title: str
    body: str
    version: int
    accepted_at: datetime
    channel: str = "web"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _wrap_lines(text: str, max_chars: int = 90) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > max_chars:
            split = paragraph.rfind(" ", 0, max_chars)
            if split == -1:
                split = max_chars
            lines.append(paragraph[:split])
            paragraph = paragraph[split:].lstrip()
        lines.append(paragraph)
    return lines


def _spain_dt(dt: datetime) -> datetime:
    from zoneinfo import ZoneInfo
    tz_aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return tz_aware.astimezone(ZoneInfo("Europe/Madrid"))


def generate_combined_acceptance_pdf(
    *,
    tenant_name: str,
    employee_name: str,
    docs: list[AcceptedDocData],
) -> bytes:
    """Genera UN PDF con todos los documentos legales aceptados."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    margin = 20 * mm

    def _header(page_title: str = "Certificado de aceptación legal") -> None:
        c.setFillColor(colors.HexColor("#12263a"))
        c.rect(0, h - 22 * mm, w, 22 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margin, h - 14 * mm, tenant_name)
        c.setFont("Helvetica", 9)
        c.drawRightString(w - margin, h - 14 * mm, page_title)

    def _footer(y_pos: float) -> None:
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#9ca3af"))
        now_str = _spain_dt(datetime.utcnow()).strftime("%d/%m/%Y %H:%M")
        c.drawRightString(w - margin, 10 * mm, f"Generado: {now_str}")

    # ── Cover page ────────────────────────────────────────────────────────────
    _header()
    y = h - 40 * mm

    c.setFillColor(colors.HexColor("#12263a"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, "Certificado de aceptación legal")
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#374151"))
    c.drawString(margin, y, f"Empleado: {employee_name}")
    y -= 7 * mm

    first_accepted = min(docs, key=lambda d: d.accepted_at)
    last_accepted = max(docs, key=lambda d: d.accepted_at)
    c.drawString(
        margin,
        y,
        f"Periodo de aceptación: {_spain_dt(first_accepted.accepted_at).strftime('%d/%m/%Y')} "
        f"– {_spain_dt(last_accepted.accepted_at).strftime('%d/%m/%Y')}",
    )
    y -= 12 * mm

    # Summary table of all docs
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#12263a"))
    c.drawString(margin, y, "Documentos aceptados")
    y -= 6 * mm
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(0.5)
    c.line(margin, y, w - margin, y)
    y -= 7 * mm

    for i, doc in enumerate(docs, 1):
        sdt = _spain_dt(doc.accepted_at)
        channel_label = "WhatsApp" if doc.channel == "whatsapp" else "Web"
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#12263a"))
        c.drawString(margin, y, f"{i}. {doc.title} (v{doc.version})")
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(margin + 4 * mm, y - 5 * mm, f"Aceptado el {sdt.strftime('%d/%m/%Y')} a las {sdt.strftime('%H:%M')} vía {channel_label}")
        y -= 13 * mm
        if y < 25 * mm:
            _footer(y)
            c.showPage()
            _header()
            y = h - 35 * mm

    _footer(y)

    # ── One section per document ───────────────────────────────────────────────
    for doc in docs:
        c.showPage()
        _header()
        y = h - 36 * mm

        # Doc title block
        c.setFillColor(colors.HexColor("#12263a"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, doc.title)
        y -= 7 * mm

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(margin, y, f"Versión {doc.version}")
        y -= 12 * mm

        # Meta block
        sdt = _spain_dt(doc.accepted_at)
        channel_label = "WhatsApp" if doc.channel == "whatsapp" else "Aplicación web"
        c.setFillColor(colors.HexColor("#f1f5f9"))
        c.rect(margin, y - 22 * mm, w - 2 * margin, 22 * mm, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#12263a"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin + 5 * mm, y - 6 * mm, "Empleado:")
        c.drawString(margin + 5 * mm, y - 12 * mm, "Fecha y hora:")
        c.drawString(margin + 5 * mm, y - 18 * mm, "Canal:")
        c.setFont("Helvetica", 9)
        c.drawString(margin + 42 * mm, y - 6 * mm, employee_name)
        c.drawString(margin + 42 * mm, y - 12 * mm, sdt.strftime("%d/%m/%Y %H:%M:%S"))
        c.drawString(margin + 42 * mm, y - 18 * mm, channel_label)
        y -= 28 * mm

        # Body
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#12263a"))
        c.drawString(margin, y, "Contenido del documento")
        y -= 6 * mm
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.setLineWidth(0.5)
        c.line(margin, y, w - margin, y)
        y -= 6 * mm

        plain = _strip_html(doc.body)
        lines = _wrap_lines(plain, max_chars=92)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#374151"))
        line_h = 5 * mm
        for line in lines:
            if y < 30 * mm:
                _footer(y)
                c.showPage()
                _header()
                y = h - 35 * mm
                c.setFont("Helvetica", 8.5)
                c.setFillColor(colors.HexColor("#374151"))
            c.drawString(margin, y, line)
            y -= line_h

        y -= 8 * mm

        # Signature footer
        if y < 40 * mm:
            _footer(y)
            c.showPage()
            _header()
            y = h - 35 * mm

        c.setFillColor(colors.HexColor("#f1f5f9"))
        c.rect(margin, y - 18 * mm, w - 2 * margin, 18 * mm, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#374151"))
        c.setFont("Helvetica", 8)
        c.drawString(
            margin + 5 * mm,
            y - 7 * mm,
            f"El empleado {employee_name} ha leído y aceptado el documento «{doc.title}»",
        )
        c.drawString(
            margin + 5 * mm,
            y - 12 * mm,
            f"(versión {doc.version}) el {sdt.strftime('%d/%m/%Y')} a las {sdt.strftime('%H:%M')} vía {channel_label}.",
        )
        _footer(y)

    c.save()
    return buf.getvalue()


def store_combined_acceptance_pdf(
    session: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    tenant_name: str,
    employee_name: str,
    docs: list[AcceptedDocData],
) -> "DocumentDelivery":
    """Genera el PDF combinado y lo guarda como DocumentDelivery."""
    from app.models.documents import DocumentDelivery
    from app.services.document_service import create_delivery, store_upload_file

    pdf_bytes = generate_combined_acceptance_pdf(
        tenant_name=tenant_name,
        employee_name=employee_name,
        docs=docs,
    )

    from datetime import date as _date
    filename = f"legal_aceptacion_{_date.today().isoformat()}.pdf"
    file_path, stored_name = store_upload_file(UPLOAD_DIR, filename, pdf_bytes)

    delivery = create_delivery(
        session,
        tenant_id=tenant_id,
        company_id=None,
        employee_id=employee_id,
        document_type_id=None,
        document_type_code="legal_acceptance",
        file_path=file_path,
        file_name=stored_name,
        title=f"Certificado de aceptación legal ({_date.today().strftime('%d/%m/%Y')})",
        requires_acknowledgment=False,
    )
    return delivery


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.documents import DocumentDelivery
