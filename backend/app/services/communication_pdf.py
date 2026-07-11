"""Renderiza un comunicado (título + cuerpo) a PDF para el modo 'con firma'."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_communication_pdf(title: str, body: str, *, company_name: str | None = None) -> bytes:
    """Devuelve los bytes de un PDF A4 con el comunicado, listo para firmar."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title=title or "Comunicado",
    )
    styles = getSampleStyleSheet()
    h_style = ParagraphStyle(
        "CommTitle",
        parent=styles["Title"],
        alignment=TA_LEFT,
        fontSize=18,
        spaceAfter=10,
    )
    meta_style = ParagraphStyle(
        "CommMeta",
        parent=styles["Normal"],
        fontSize=9,
        textColor="#666666",
        spaceAfter=14,
    )
    body_style = ParagraphStyle(
        "CommBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
    )

    flow = [Paragraph(_escape(title), h_style)]
    if company_name:
        flow.append(Paragraph(_escape(company_name), meta_style))
    flow.append(Spacer(1, 4))
    for block in (body or "").split("\n"):
        if block.strip():
            flow.append(Paragraph(_escape(block), body_style))
        else:
            flow.append(Spacer(1, 8))
    doc.build(flow)
    return buf.getvalue()
