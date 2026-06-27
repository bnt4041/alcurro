"""Genera el PDF de Registro Diario de Jornada (Real Decreto-ley 8/2019).

Documento legal por trabajador y mes, con fecha, hora de entrada/salida,
total de horas y líneas de firma para empresa y trabajador.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.reports_service import DayReportRow

W, H = A4
MARGIN = 2 * cm
CONTENT_W = W - 2 * MARGIN

_DARK = colors.HexColor("#1a1a2e")
_ACCENT = colors.HexColor("#2563eb")
_LIGHT_GRAY = colors.HexColor("#f1f5f9")
_MID_GRAY = colors.HexColor("#94a3b8")

styles = getSampleStyleSheet()

_MONTHS_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _style(name: str, **kwargs: object) -> ParagraphStyle:
    return ParagraphStyle(name, parent=styles["Normal"], **kwargs)


_TITLE = _style("JrnTitle", fontSize=18, textColor=_ACCENT, leading=22, fontName="Helvetica-Bold", alignment=1)
_SUBTITLE = _style("JrnSub", fontSize=10, textColor=_MID_GRAY, leading=14, alignment=1)
_LABEL = _style("JrnLabel", fontSize=9, textColor=_DARK, leading=14, fontName="Helvetica-Bold")
_VALUE = _style("JrnValue", fontSize=9, textColor=_DARK, leading=14)
_CELL = _style("JrnCell", fontSize=9, textColor=_DARK, leading=12)
_SIGN = _style("JrnSign", fontSize=8, textColor=_MID_GRAY, leading=11, alignment=1)


@dataclass
class JournalEmployeeMeta:
    full_name: str
    id_document: str | None = None
    company_name: str = "—"
    company_cif: str | None = None
    center_dept: str = "—"


def _accent(color_hex: str | None) -> colors.Color:
    if color_hex and color_hex.startswith("#") and len(color_hex) == 7:
        try:
            return colors.HexColor(color_hex)
        except ValueError:
            pass
    return _ACCENT


def _hours(minutes: int) -> str:
    return f"{minutes / 60:.2f} h"


def _info_block(label: str, value: str, accent: colors.Color) -> Table:
    items = [
        [Paragraph(label, _LABEL)],
        [Paragraph(value or "—", _VALUE)],
    ]
    t = Table(items, colWidths=[CONTENT_W / 2 - 6])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _build_block(
    meta: JournalEmployeeMeta,
    period_label: str,
    day_rows: list[DayReportRow],
    accent: colors.Color,
) -> list[object]:
    story: list[object] = []

    # ── Cabecera ─────────────────────────────────────────────────────────────
    story.append(Paragraph("REGISTRO DIARIO DE JORNADA", _style(
        "T", fontSize=18, textColor=accent, leading=22, fontName="Helvetica-Bold", alignment=1,
    )))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph("(Real Decreto-ley 8/2019, de 8 de marzo)", _SUBTITLE))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=accent))
    story.append(Spacer(1, 0.4 * cm))

    # ── Datos del trabajador / empresa ───────────────────────────────────────
    info_data = [
        [_info_block("Trabajador:", meta.full_name, accent),
         _info_block("Centro/Dept:", meta.center_dept, accent)],
        [_info_block("Empresa:", meta.company_name, accent),
         _info_block("CIF:", meta.company_cif or "—", accent)],
        [_info_block("Periodo:", period_label, accent),
         _info_block("", "", accent)],
    ]
    if meta.id_document:
        info_data.append(
            [_info_block("DNI/NIE:", meta.id_document, accent),
             _info_block("", "", accent)]
        )
    info_table = Table(info_data, colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Tabla de jornadas ────────────────────────────────────────────────────
    header = ["Fecha", "Hora Entrada", "Hora Salida", "Total Horas", "Firma Trabajador"]
    table_rows: list[list[object]] = [header]
    total_minutes = 0

    for day in day_rows:
        for entry in day.clock_entries:
            break_min = sum(b.duration_minutes for b in entry.breaks)
            net = max(0, entry.worked_minutes - break_min)
            total_minutes += net
            table_rows.append([
                Paragraph(day.report_date, _CELL),
                Paragraph(entry.entrada_at, _CELL),
                Paragraph(entry.salida_at or "—", _CELL),
                Paragraph(_hours(net) if entry.salida_at else "—", _CELL),
                Paragraph("", _CELL),
            ])

    if len(table_rows) == 1:
        table_rows.append([
            Paragraph("Sin fichajes en el periodo", _style("Empty", fontSize=9, textColor=_MID_GRAY, alignment=1)),
            "", "", "", "",
        ])

    table_rows.append([
        Paragraph("TOTAL HORAS MES:", _style("TotLbl", fontSize=9, fontName="Helvetica-Bold", textColor=_DARK, alignment=2)),
        "", "",
        Paragraph(_hours(total_minutes), _style("TotVal", fontSize=9, fontName="Helvetica-Bold", textColor=_DARK)),
        "",
    ])

    col_w = [
        CONTENT_W * 0.18, CONTENT_W * 0.18, CONTENT_W * 0.18,
        CONTENT_W * 0.16, CONTENT_W * 0.30,
    ]
    n_rows = len(table_rows)
    is_empty = len(day_rows) == 0 or all(not d.clock_entries for d in day_rows)
    jornada_table = Table(table_rows, colWidths=col_w, repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, _LIGHT_GRAY),
        # Fila TOTAL
        ("BACKGROUND", (0, n_rows - 1), (-1, n_rows - 1), _LIGHT_GRAY),
        ("SPAN", (0, n_rows - 1), (2, n_rows - 1)),
        ("LINEABOVE", (0, n_rows - 1), (-1, n_rows - 1), 1, accent),
    ]
    if not is_empty:
        table_style.append(("ROWBACKGROUNDS", (0, 1), (-1, n_rows - 2), [colors.white, colors.HexColor("#f8fafc")]))
    else:
        table_style.append(("SPAN", (0, 1), (-1, 1)))
    jornada_table.setStyle(TableStyle(table_style))
    story.append(jornada_table)
    story.append(Spacer(1, 2 * cm))

    # ── Firmas ───────────────────────────────────────────────────────────────
    sign_data = [
        [Paragraph("Firma de la Empresa / Sello", _SIGN),
         Paragraph("Firma del Trabajador", _SIGN)],
    ]
    sign_table = Table(sign_data, colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.45], spaceBefore=0)
    sign_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (0, 0), 0.5, _DARK),
        ("LINEABOVE", (1, 0), (1, 0), 0.5, _DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sign_table)

    return story


def generate_journal_pdf(
    *,
    rows: list[DayReportRow],
    emp_meta: dict[str, JournalEmployeeMeta],
    date_from: date,
    date_to: date,
    branding_color: str | None = None,
) -> bytes:
    """Genera el PDF con un bloque por (trabajador, mes) con fichajes en el rango."""
    accent = _accent(branding_color)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
        title="Registro Diario de Jornada",
    )

    # Agrupar por (empleado, año-mes), conservando orden cronológico de filas
    groups: dict[tuple[str, int, int], list[DayReportRow]] = {}
    for r in rows:
        y, m, _ = (int(p) for p in r.report_date.split("-"))
        groups.setdefault((r.employee_id, y, m), []).append(r)

    # Solo grupos con al menos un fichaje
    ordered_keys = [
        k for k in sorted(
            groups.keys(),
            key=lambda k: (emp_meta.get(k[0], JournalEmployeeMeta("")).full_name, k[1], k[2]),
        )
        if any(d.clock_entries for d in groups[k])
    ]

    story: list[object] = []
    for idx, key in enumerate(ordered_keys):
        emp_id, year, month = key
        meta = emp_meta.get(emp_id, JournalEmployeeMeta(full_name=emp_id))
        period_label = f"{_MONTHS_ES[month]} {year}"
        day_rows = [d for d in groups[key] if d.clock_entries]
        if idx > 0:
            story.append(PageBreak())
        story.extend(_build_block(meta, period_label, day_rows, accent))

    if not story:
        story.append(Paragraph("No hay fichajes en el periodo seleccionado.", _VALUE))

    doc.build(story)
    return buf.getvalue()
