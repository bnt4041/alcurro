"""Generación de PDF de factura con reportlab."""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.invoice import Invoice, InvoiceStatus
from app.models.platform_settings import PlatformSettings

W, H = A4
MARGIN = 2 * cm
CONTENT_W = W - 2 * MARGIN

_DARK = colors.HexColor("#1a1a2e")
_ACCENT = colors.HexColor("#2563eb")
_LIGHT_GRAY = colors.HexColor("#f1f5f9")
_MID_GRAY = colors.HexColor("#94a3b8")
_DANGER = colors.HexColor("#dc2626")

styles = getSampleStyleSheet()


def _style(name: str, **kwargs: object) -> ParagraphStyle:
    base = styles["Normal"]
    return ParagraphStyle(name, parent=base, **kwargs)


_TITLE_STYLE = _style("InvTitle", fontSize=22, textColor=_ACCENT, leading=26, fontName="Helvetica-Bold")
_H2 = _style("InvH2", fontSize=10, textColor=_DARK, leading=14, fontName="Helvetica-Bold")
_BODY = _style("InvBody", fontSize=9, textColor=_DARK, leading=13)
_MUTED = _style("InvMuted", fontSize=8, textColor=_MID_GRAY, leading=11)
_RIGHT = _style("InvRight", fontSize=9, textColor=_DARK, leading=13, alignment=2)
_TOTAL_LABEL = _style("InvTotalLabel", fontSize=11, textColor=_DARK, leading=15, fontName="Helvetica-Bold", alignment=2)
_TOTAL_VALUE = _style("InvTotalValue", fontSize=13, textColor=_ACCENT, leading=18, fontName="Helvetica-Bold", alignment=2)


def _money(cents: int, currency: str = "EUR") -> str:
    symbol = "€" if currency == "EUR" else currency
    return f"{cents / 100:,.2f} {symbol}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date(d: date | None) -> str:
    if not d:
        return "—"
    return d.strftime("%d/%m/%Y")


def _status_label(status: InvoiceStatus) -> str:
    return {
        InvoiceStatus.DRAFT: "BORRADOR",
        InvoiceStatus.SENT: "ENVIADA",
        InvoiceStatus.PAID: "PAGADA",
        InvoiceStatus.CANCELLED: "ANULADA",
        InvoiceStatus.CREDIT_NOTE: "FACTURA RECTIFICATIVA",
    }.get(status, status.upper())


def generate_invoice_pdf(invoice: Invoice, settings: PlatformSettings) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    story = []

    # ── Header: título + número ──────────────────────────────────────────────
    is_credit = invoice.status == InvoiceStatus.CREDIT_NOTE
    doc_title = "FACTURA RECTIFICATIVA" if is_credit else "FACTURA"
    header_data = [
        [Paragraph(doc_title, _TITLE_STYLE), Paragraph(invoice.number, _TITLE_STYLE)],
    ]
    header_table = Table(header_data, colWidths=[CONTENT_W * 0.6, CONTENT_W * 0.4])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, _ACCENT),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Emisor y receptor ────────────────────────────────────────────────────
    def _block(label: str, lines: list[str]) -> list[object]:
        items: list[object] = [Paragraph(label, _H2)]
        for line in lines:
            if line:
                items.append(Paragraph(line, _BODY))
        return items

    issuer_lines = [
        settings.legal_name,
        f"CIF/NIF: {settings.tax_id}" if settings.tax_id else "",
        settings.billing_address or "",
        f"{settings.billing_postal_code or ''} {settings.billing_city or ''}".strip(),
        settings.billing_province or "",
        settings.billing_country or "ES",
        settings.billing_email or "",
        settings.billing_phone or "",
        settings.website or "",
    ]
    recipient_lines = [
        invoice.recipient_legal_name or "—",
        f"CIF/NIF: {invoice.recipient_tax_id}" if invoice.recipient_tax_id else "",
        invoice.recipient_address or "",
        f"{invoice.recipient_postal_code or ''} {invoice.recipient_city or ''}".strip(),
        invoice.recipient_province or "",
        invoice.recipient_country or "ES",
        invoice.recipient_email or "",
    ]

    from reportlab.platypus import KeepTogether  # local import ok
    parties_data = [
        [
            KeepTogether(_block("EMISOR", issuer_lines)),
            KeepTogether(_block("CLIENTE", recipient_lines)),
        ]
    ]
    parties_table = Table(parties_data, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    parties_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), _LIGHT_GRAY),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (0, 0), (0, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("LEFTPADDING", (1, 0), (1, 0), 16),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Metadatos de factura ─────────────────────────────────────────────────
    status_color = _DANGER if is_credit else _ACCENT
    meta_data = [
        ["Fecha emisión", "Fecha vencimiento", "Estado"],
        [
            Paragraph(_date(invoice.issue_date), _BODY),
            Paragraph(_date(invoice.due_date), _BODY),
            Paragraph(_status_label(invoice.status), _style("InvStatus", fontSize=9, textColor=status_color, fontName="Helvetica-Bold")),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[CONTENT_W / 3] * 3)
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Líneas de factura ────────────────────────────────────────────────────
    lines_header = ["Concepto", "Base imponible", f"IVA ({invoice.vat_rate}%)", "Total"]
    lines_data = [
        lines_header,
        [
            Paragraph(invoice.concept, _BODY),
            Paragraph(_money(invoice.base_cents, invoice.currency), _RIGHT),
            Paragraph(_money(invoice.vat_cents, invoice.currency), _RIGHT),
            Paragraph(_money(invoice.total_cents, invoice.currency), _RIGHT),
        ],
    ]
    col_w = [CONTENT_W * 0.46, CONTENT_W * 0.18, CONTENT_W * 0.18, CONTENT_W * 0.18]
    lines_table = Table(lines_data, colWidths=col_w, repeatRows=1)
    lines_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, _LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_GRAY]),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    ]))
    story.append(lines_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Totales ──────────────────────────────────────────────────────────────
    totals_data = [
        [Paragraph("Base imponible:", _RIGHT), Paragraph(_money(invoice.base_cents, invoice.currency), _RIGHT)],
        [Paragraph(f"IVA ({invoice.vat_rate}%):", _RIGHT), Paragraph(_money(invoice.vat_cents, invoice.currency), _RIGHT)],
        [Paragraph("TOTAL:", _TOTAL_LABEL), Paragraph(_money(invoice.total_cents, invoice.currency), _TOTAL_VALUE)],
    ]
    totals_table = Table(totals_data, colWidths=[CONTENT_W * 0.75, CONTENT_W * 0.25])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, 2), (-1, 2), 1.5, _ACCENT),
        ("TOPPADDING", (0, 2), (-1, 2), 8),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 8),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Información de pago ──────────────────────────────────────────────────
    if settings.iban or settings.bank_name:
        story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=_MID_GRAY))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("DATOS PARA TRANSFERENCIA BANCARIA", _H2))
        if settings.bank_name:
            story.append(Paragraph(f"Entidad: {settings.bank_name}", _BODY))
        if settings.iban:
            story.append(Paragraph(f"IBAN: {settings.iban}", _BODY))
        if settings.swift_bic:
            story.append(Paragraph(f"SWIFT/BIC: {settings.swift_bic}", _BODY))
        story.append(Paragraph(f"Concepto: {invoice.number}", _BODY))
        story.append(Spacer(1, 0.4 * cm))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=_MID_GRAY))
    story.append(Spacer(1, 0.25 * cm))
    if settings.invoice_footer_text:
        story.append(Paragraph(settings.invoice_footer_text, _MUTED))
    story.append(
        Paragraph(
            f"{settings.legal_name} · {settings.tax_id} · {settings.billing_email or ''}",
            _MUTED,
        )
    )

    doc.build(story)
    return buf.getvalue()
