import { useState, useCallback, useEffect, useRef } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import { api } from "../api/client";
import type {
  DayReportRow,
  EmployeeSummaryRow,
  ClockEntryReport,
  BreakPairReport,
  LeaveReportRow,
  IncidentReportRow,
} from "../api/types";
import { getStoredTenantSlug } from "../hooks/useBranding";
import PageHeader from "../components/PageHeader";

// ═══════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════

function fmtMin(minutes: number): string {
  if (!minutes) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, "0")}h ${String(m).padStart(2, "0")}m`;
}
function fmtDate(iso: string): string {
  const [y, mo, d] = iso.split("-");
  return `${d}/${mo}/${y}`;
}
function firstDayOfMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}
function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}
const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente", approved: "Aprobado", rejected: "Rechazado",
  cancelled: "Cancelado", open: "Abierta", resolved: "Resuelta",
};

// ═══════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════

interface FilterOption { id: string; name: string; }
interface FilterOptions {
  companies: FilterOption[];
  work_centers: FilterOption[];
  departments: FilterOption[];
  supervisors: FilterOption[];
  employees: FilterOption[];
}
interface Branding { name: string; primary_color: string; logo_url: string | null; }
interface Filters {
  employee_ids: string[];
  supervisor_ids: string[];
  company_ids: string[];
  work_center_ids: string[];
  department_ids: string[];
}

// ═══════════════════════════════════════════════════
// MultiSearchSelect component
// ═══════════════════════════════════════════════════

interface MultiSearchSelectProps {
  options: FilterOption[];
  value: string[];
  onChange: (v: string[]) => void;
  placeholder: string;
}

function MultiSearchSelect({ options, value, onChange, placeholder }: MultiSearchSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = search.trim()
    ? options.filter((o) => o.name.toLowerCase().includes(search.toLowerCase().trim()))
    : options;

  const toggle = (id: string) =>
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);

  const triggerLabel =
    value.length === 0
      ? placeholder
      : value.length === 1
      ? (options.find((o) => o.id === value[0])?.name ?? placeholder)
      : `${value.length} seleccionados`;

  return (
    <div className="ss-wrap" ref={ref}>
      <button
        type="button"
        className={`ss-trigger${open ? " open" : ""}${value.length > 0 ? " has-value" : ""}`}
        onClick={() => { setOpen((p) => !p); setSearch(""); }}
      >
        <span className="ss-label">{triggerLabel}</span>
        <span className="ss-caret">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="ss-dropdown">
          <input
            className="ss-search"
            type="text"
            autoFocus
            placeholder="Buscar…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <ul className="ss-list">
            {value.length > 0 && (
              <li className="ss-item ss-clear-item" onClick={() => onChange([])}>
                ✕ Limpiar selección ({value.length})
              </li>
            )}
            {filtered.length === 0 && (
              <li className="ss-empty">Sin resultados</li>
            )}
            {filtered.map((o) => {
              const checked = value.includes(o.id);
              return (
                <li
                  key={o.id}
                  className={`ss-item ss-check-item${checked ? " selected" : ""}`}
                  onClick={() => toggle(o.id)}
                >
                  <span className="ss-checkbox" aria-hidden>{checked ? "☑" : "☐"}</span>
                  {o.name}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════
// Export helpers
// ═══════════════════════════════════════════════════

function buildChronoXlsRows(rows: DayReportRow[]): (string | number)[][] {
  return rows.map((r) => [
    fmtDate(r.report_date),
    r.weekday,
    r.employee_name,
    r.clock_entries.map((e) => `${e.entrada_at}→${e.salida_at ?? "abierto"}`).join(" | ") || "—",
    fmtMin(r.worked_minutes),
    fmtMin(r.break_minutes),
    fmtMin(r.net_minutes),
    r.leaves.map((l) => l.leave_type_name ?? "Permiso").join(", ") || "—",
    r.incidents.length || "—",
  ]);
}
function buildSummaryXlsRows(rows: EmployeeSummaryRow[]): (string | number)[][] {
  return rows.map((r) => [
    r.employee_name,
    r.days_worked,
    fmtMin(r.total_worked_minutes),
    fmtMin(r.total_break_minutes),
    fmtMin(r.total_net_minutes),
    r.total_leave_days.toFixed(1),
    r.total_incidents,
    Object.entries(r.leave_by_type).map(([t, d]) => `${t}: ${d.toFixed(1)}d`).join(", ") || "—",
  ]);
}

async function logoDataURL(url: string): Promise<string | null> {
  try {
    const resp = await fetch(url, { mode: "cors" });
    const blob = await resp.blob();
    return await new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => resolve(null);
      reader.readAsDataURL(blob);
    });
  } catch { return null; }
}

async function exportPDF(
  tab: "chronological" | "summary",
  chronoRows: DayReportRow[],
  summaryRows: EmployeeSummaryRow[],
  dateFrom: string,
  dateTo: string,
  branding: Branding | null,
) {
  const doc = new jsPDF({ orientation: "landscape", format: "a4" });
  const hex = (branding?.primary_color ?? "#12263a").replace("#", "");
  const rgb = (h: string): [number, number, number] => [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];

  if (branding?.logo_url) {
    const dataUrl = await logoDataURL(branding.logo_url);
    if (dataUrl) { try { doc.addImage(dataUrl, 8, 4, 28, 14); } catch { /* ignore */ } }
  }
  doc.setFontSize(14);
  doc.setTextColor(...rgb(hex));
  doc.text(branding?.name ?? "Informe", 148, 10, { align: "center" });
  doc.setFontSize(10);
  doc.setTextColor(80, 80, 80);
  doc.text(
    `${tab === "chronological" ? "Informe Cronológico" : "Informe Resumen"} — ${fmtDate(dateFrom)} a ${fmtDate(dateTo)}`,
    148, 17, { align: "center" },
  );
  doc.setDrawColor(...rgb(hex));
  doc.setLineWidth(0.5);
  doc.line(8, 20, 289, 20);

  if (tab === "chronological") {
    const totals = computeChronoTotals(chronoRows);
    autoTable(doc, {
      startY: 24,
      head: [["Fecha", "Día", "Empleado", "Fichajes", "Horas", "Pausas", "Horas netas", "Permiso", "Inc."]],
      body: buildChronoXlsRows(chronoRows),
      foot: [["TOTAL", "", "", "", fmtMin(totals.worked), fmtMin(totals.breaks), fmtMin(totals.net), `${totals.leaves} perm.`, totals.incidents]],
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: rgb(hex), textColor: 255, fontStyle: "bold" },
      footStyles: { fillColor: [241, 245, 249] as [number, number, number], fontStyle: "bold" },
      alternateRowStyles: { fillColor: [248, 250, 252] as [number, number, number] },
    });
  } else {
    const totals = computeSummaryTotals(summaryRows);
    autoTable(doc, {
      startY: 24,
      head: [["Empleado", "Días", "Horas", "Pausas", "Horas netas", "Días permiso", "Inc.", "Permisos por tipo"]],
      body: buildSummaryXlsRows(summaryRows),
      foot: [["TOTAL", totals.days, fmtMin(totals.worked), fmtMin(totals.breaks), fmtMin(totals.net), totals.leave.toFixed(1), totals.incidents, ""]],
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: rgb(hex), textColor: 255, fontStyle: "bold" },
      footStyles: { fillColor: [241, 245, 249] as [number, number, number], fontStyle: "bold" },
      alternateRowStyles: { fillColor: [248, 250, 252] as [number, number, number] },
    });
  }

  const pageCount = (doc as unknown as { internal: { getNumberOfPages: () => number } }).internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(150);
    doc.text(`Página ${i} de ${pageCount}`, 289, 207, { align: "right" });
  }
  doc.save(`${tab === "chronological" ? "informe-cronologico" : "informe-resumen"}_${dateFrom}_${dateTo}.pdf`);
}

function exportExcel(
  tab: "chronological" | "summary",
  chronoRows: DayReportRow[],
  summaryRows: EmployeeSummaryRow[],
  dateFrom: string,
  dateTo: string,
) {
  const wb = XLSX.utils.book_new();
  if (tab === "chronological") {
    const totals = computeChronoTotals(chronoRows);
    const header = ["Fecha", "Día", "Empleado", "Fichajes", "Horas", "Pausas", "Horas netas", "Permiso", "Incidencias"];
    const totRow = ["TOTAL", "", "", "", fmtMin(totals.worked), fmtMin(totals.breaks), fmtMin(totals.net), `${totals.leaves} perm.`, totals.incidents];
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([header, ...buildChronoXlsRows(chronoRows), totRow]), "Cronológico");
  } else {
    const totals = computeSummaryTotals(summaryRows);
    const header = ["Empleado", "Días trabajados", "Horas", "Pausas", "Horas netas", "Días permiso", "Incidencias", "Permisos por tipo"];
    const totRow = ["TOTAL", totals.days, fmtMin(totals.worked), fmtMin(totals.breaks), fmtMin(totals.net), totals.leave.toFixed(1), totals.incidents, ""];
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([header, ...buildSummaryXlsRows(summaryRows), totRow]), "Resumen");
  }
  XLSX.writeFile(wb, `${tab === "chronological" ? "informe-cronologico" : "informe-resumen"}_${dateFrom}_${dateTo}.xlsx`);
}

// ═══════════════════════════════════════════════════
// Totals
// ═══════════════════════════════════════════════════

interface ChronoTotals { worked: number; breaks: number; net: number; incidents: number; leaves: number; }
function computeChronoTotals(rows: DayReportRow[]): ChronoTotals {
  return rows.reduce(
    (acc, r) => ({
      worked: acc.worked + r.worked_minutes,
      breaks: acc.breaks + r.break_minutes,
      net: acc.net + r.net_minutes,
      incidents: acc.incidents + r.incidents.length,
      leaves: acc.leaves + r.leaves.length,
    }),
    { worked: 0, breaks: 0, net: 0, incidents: 0, leaves: 0 },
  );
}
interface SummaryTotals { days: number; worked: number; breaks: number; net: number; leave: number; incidents: number; }
function computeSummaryTotals(rows: EmployeeSummaryRow[]): SummaryTotals {
  return rows.reduce(
    (acc, r) => ({
      days: acc.days + r.days_worked,
      worked: acc.worked + r.total_worked_minutes,
      breaks: acc.breaks + r.total_break_minutes,
      net: acc.net + r.total_net_minutes,
      leave: acc.leave + r.total_leave_days,
      incidents: acc.incidents + r.total_incidents,
    }),
    { days: 0, worked: 0, breaks: 0, net: 0, leave: 0, incidents: 0 },
  );
}

// ═══════════════════════════════════════════════════
// Detail sub-components
// ═══════════════════════════════════════════════════

function ClockDetail({ entry }: { entry: ClockEntryReport }) {
  return (
    <div className="report-clock-detail">
      <span className="report-clock-times">
        <span className="report-time in">{entry.entrada_at}</span>
        <span className="report-arrow">→</span>
        <span className={`report-time out${entry.is_open ? " open" : ""}`}>
          {entry.salida_at ?? "Abierto"}
        </span>
      </span>
      {entry.project_name && <span className="report-tag project">{entry.project_name}</span>}
      {entry.address && <span className="report-tag addr" title={entry.address}>📍 {entry.address}</span>}
      {entry.breaks.length > 0 && (
        <div className="report-breaks-list">
          <span className="report-breaks-label">Pausas:</span>
          {entry.breaks.map((b: BreakPairReport, i: number) => (
            <span key={i} className="report-break-badge">
              {b.inicio_at}→{b.fin_at ?? "…"}
              {b.duration_minutes > 0 && <span className="report-break-dur"> ({fmtMin(b.duration_minutes)})</span>}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function LeaveDetail({ lr }: { lr: LeaveReportRow }) {
  const cls = lr.status === "approved" ? "approved" : lr.status === "pending" ? "pending" : "other";
  return (
    <div className={`report-leave-detail ${cls}`}>
      <span>🏖️</span>
      <span className="report-leave-type">{lr.leave_type_name ?? "Permiso"}</span>
      <span className="report-leave-status">{STATUS_LABEL[lr.status] ?? lr.status}</span>
      {lr.reason && <span className="report-leave-reason">— {lr.reason}</span>}
    </div>
  );
}

function IncidentDetail({ inc }: { inc: IncidentReportRow }) {
  return (
    <div className="report-incident-detail">
      <span>⚠️</span>
      <span className="report-incident-title">{inc.title}</span>
      {inc.minutes_late != null && <span className="report-incident-late">{inc.minutes_late} min tarde</span>}
      <span className="report-incident-status">{STATUS_LABEL[inc.status] ?? inc.status}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// Chronological table
// ═══════════════════════════════════════════════════

function ChronologicalTable({ rows }: { rows: DayReportRow[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggle = (key: string) =>
    setExpanded((prev) => { const next = new Set(prev); next.has(key) ? next.delete(key) : next.add(key); return next; });

  const totals = computeChronoTotals(rows);
  if (rows.length === 0) return <p className="report-empty">Sin datos para los filtros aplicados.</p>;

  return (
    <div className="report-chrono-wrap">
      <table className="report-chrono-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Empleado</th>
            <th>Fichajes</th>
            <th className="num">Horas</th>
            <th className="num">Pausas</th>
            <th className="num">Horas netas</th>
            <th>Permiso</th>
            <th className="center">Inc.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const key = `${row.employee_id}_${row.report_date}`;
            const hasDetail = row.clock_entries.length > 0 || row.leaves.length > 0 || row.incidents.length > 0;
            const isExp = expanded.has(key);
            return (
              <>
                <tr
                  key={key}
                  className={`report-chrono-row${isExp ? " expanded" : ""}${hasDetail ? " clickable" : ""}`}
                  onClick={hasDetail ? () => toggle(key) : undefined}
                >
                  <td>
                    <span className="report-date-day">{fmtDate(row.report_date)}</span>
                    <span className="report-date-wd">{row.weekday}</span>
                  </td>
                  <td className="report-col-emp">{row.employee_name}</td>
                  <td>
                    {row.clock_entries.length === 0
                      ? <span className="muted">—</span>
                      : row.clock_entries.map((e) => (
                          <span key={e.id} className="report-entry-pill">
                            {e.entrada_at} → {e.salida_at ?? <em>abierto</em>}
                          </span>
                        ))}
                  </td>
                  <td className="num">{fmtMin(row.worked_minutes)}</td>
                  <td className="num">{fmtMin(row.break_minutes)}</td>
                  <td className="num">{fmtMin(row.net_minutes)}</td>
                  <td>
                    {row.leaves.length > 0
                      ? <span className="report-leave-pill">{row.leaves.map((l) => l.leave_type_name ?? "Permiso").join(", ")}</span>
                      : <span className="muted">—</span>}
                  </td>
                  <td className="center">
                    {row.incidents.length > 0
                      ? <span className="report-inc-badge">{row.incidents.length}</span>
                      : <span className="muted">—</span>}
                  </td>
                  <td>{hasDetail && <button type="button" className="report-toggle-btn" tabIndex={-1}>{isExp ? "▲" : "▼"}</button>}</td>
                </tr>
                {isExp && (
                  <tr key={`${key}_detail`} className="report-detail-row">
                    <td colSpan={9}>
                      <div className="report-detail-panel">
                        {row.clock_entries.map((e) => <ClockDetail key={e.id} entry={e} />)}
                        {row.leaves.map((lr) => <LeaveDetail key={lr.id} lr={lr} />)}
                        {row.incidents.map((inc) => <IncidentDetail key={inc.id} inc={inc} />)}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="report-totals-row">
            <td colSpan={2}><strong>TOTAL — {rows.length} registros</strong></td>
            <td></td>
            <td className="num"><strong>{fmtMin(totals.worked)}</strong></td>
            <td className="num"><strong>{fmtMin(totals.breaks)}</strong></td>
            <td className="num"><strong>{fmtMin(totals.net)}</strong></td>
            <td><strong>{totals.leaves > 0 ? `${totals.leaves} permisos` : "—"}</strong></td>
            <td className="center"><strong>{totals.incidents > 0 ? <span className="report-inc-badge">{totals.incidents}</span> : "—"}</strong></td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// Summary modal
// ═══════════════════════════════════════════════════

function SummaryModal({ summary, days, onClose }: { summary: EmployeeSummaryRow; days: DayReportRow[]; onClose: () => void }) {
  const empDays = days.filter((d) => d.employee_id === summary.employee_id);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggle = (key: string) =>
    setExpanded((prev) => { const next = new Set(prev); next.has(key) ? next.delete(key) : next.add(key); return next; });

  return (
    <div className="modal-backdrop">
      <div className="modal-box report-summary-modal">
        <div className="modal-header">
          <h2>{summary.employee_name} — Detalle</h2>
          <button type="button" className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="report-kpi-strip">
          {[
            { label: "Días trabajados", val: String(summary.days_worked) },
            { label: "Horas fichadas", val: fmtMin(summary.total_worked_minutes) },
            { label: "En pausa", val: fmtMin(summary.total_break_minutes) },
            { label: "Horas netas", val: fmtMin(summary.total_net_minutes) },
            { label: "Días permiso", val: summary.total_leave_days.toFixed(1) },
            { label: "Incidencias", val: String(summary.total_incidents) },
          ].map((k) => (
            <div key={k.label} className="report-kpi">
              <span className="report-kpi-val">{k.val}</span>
              <span className="report-kpi-label">{k.label}</span>
            </div>
          ))}
        </div>
        {Object.keys(summary.leave_by_type).length > 0 && (
          <div className="report-leave-breakdown">
            {Object.entries(summary.leave_by_type).map(([t, d]) => (
              <span key={t} className="report-leave-chip">{t}: <strong>{d.toFixed(1)}d</strong></span>
            ))}
          </div>
        )}
        <div className="report-modal-chrono">
          <table className="report-chrono-table compact">
            <thead>
              <tr>
                <th>Fecha</th><th>Fichajes</th>
                <th className="num">Horas</th><th className="num">Pausas</th><th className="num">H. netas</th>
                <th>Permiso</th><th className="center">Inc.</th><th></th>
              </tr>
            </thead>
            <tbody>
              {empDays.map((row) => {
                const key = `m_${row.employee_id}_${row.report_date}`;
                const hasDetail = row.clock_entries.length > 0 || row.leaves.length > 0 || row.incidents.length > 0;
                const isExp = expanded.has(key);
                return (
                  <>
                    <tr
                      key={key}
                      className={`report-chrono-row${isExp ? " expanded" : ""}${hasDetail ? " clickable" : ""}`}
                      onClick={hasDetail ? () => toggle(key) : undefined}
                    >
                      <td>
                        <span className="report-date-day">{fmtDate(row.report_date)}</span>
                        <span className="report-date-wd">{row.weekday}</span>
                      </td>
                      <td>
                        {row.clock_entries.length === 0
                          ? <span className="muted">—</span>
                          : row.clock_entries.map((e) => <span key={e.id} className="report-entry-pill">{e.entrada_at}→{e.salida_at ?? "abierto"}</span>)}
                      </td>
                      <td className="num">{fmtMin(row.worked_minutes)}</td>
                      <td className="num">{fmtMin(row.break_minutes)}</td>
                      <td className="num">{fmtMin(row.net_minutes)}</td>
                      <td>
                        {row.leaves.length > 0
                          ? <span className="report-leave-pill">{row.leaves[0].leave_type_name ?? "Permiso"}</span>
                          : <span className="muted">—</span>}
                      </td>
                      <td className="center">
                        {row.incidents.length > 0
                          ? <span className="report-inc-badge">{row.incidents.length}</span>
                          : <span className="muted">—</span>}
                      </td>
                      <td>{hasDetail && <button type="button" className="report-toggle-btn" tabIndex={-1}>{isExp ? "▲" : "▼"}</button>}</td>
                    </tr>
                    {isExp && (
                      <tr key={`${key}_d`} className="report-detail-row">
                        <td colSpan={8}>
                          <div className="report-detail-panel">
                            {row.clock_entries.map((e) => <ClockDetail key={e.id} entry={e} />)}
                            {row.leaves.map((lr) => <LeaveDetail key={lr.id} lr={lr} />)}
                            {row.incidents.map((inc) => <IncidentDetail key={inc.id} inc={inc} />)}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// Summary table
// ═══════════════════════════════════════════════════

function SummaryTable({ rows, days }: { rows: EmployeeSummaryRow[]; days: DayReportRow[] }) {
  const [modal, setModal] = useState<EmployeeSummaryRow | null>(null);
  const totals = computeSummaryTotals(rows);
  if (rows.length === 0) return <p className="report-empty">Sin datos para los filtros aplicados.</p>;

  return (
    <>
      <div className="report-chrono-wrap">
        <table className="report-chrono-table">
          <thead>
            <tr>
              <th>Empleado</th>
              <th className="center">Días</th>
              <th className="num">Horas</th>
              <th className="num">Pausas</th>
              <th className="num">Horas netas</th>
              <th className="center">Días permiso</th>
              <th className="center">Incidencias</th>
              <th>Permisos por tipo</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.employee_id} className="report-chrono-row clickable" onClick={() => setModal(r)}>
                <td className="report-col-emp">{r.employee_name}</td>
                <td className="center">{r.days_worked}</td>
                <td className="num">{fmtMin(r.total_worked_minutes)}</td>
                <td className="num">{fmtMin(r.total_break_minutes)}</td>
                <td className="num">{fmtMin(r.total_net_minutes)}</td>
                <td className="center">{r.total_leave_days > 0 ? r.total_leave_days.toFixed(1) : "—"}</td>
                <td className="center">{r.total_incidents > 0 ? <span className="report-inc-badge">{r.total_incidents}</span> : "—"}</td>
                <td>
                  {Object.keys(r.leave_by_type).length > 0
                    ? Object.entries(r.leave_by_type).map(([t, d]) => <span key={t} className="report-leave-chip">{t}: {d.toFixed(1)}d</span>)
                    : <span className="muted">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="report-totals-row">
              <td><strong>TOTAL — {rows.length} empleados</strong></td>
              <td className="center"><strong>{totals.days}</strong></td>
              <td className="num"><strong>{fmtMin(totals.worked)}</strong></td>
              <td className="num"><strong>{fmtMin(totals.breaks)}</strong></td>
              <td className="num"><strong>{fmtMin(totals.net)}</strong></td>
              <td className="center"><strong>{totals.leave > 0 ? totals.leave.toFixed(1) : "—"}</strong></td>
              <td className="center"><strong>{totals.incidents > 0 ? <span className="report-inc-badge">{totals.incidents}</span> : "—"}</strong></td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="report-hint">Haz clic en un empleado para ver su detalle cronológico.</p>
      {modal && <SummaryModal summary={modal} days={days} onClose={() => setModal(null)} />}
    </>
  );
}

// ═══════════════════════════════════════════════════
// Main page
// ═══════════════════════════════════════════════════

const EMPTY_FILTERS: Filters = {
  employee_ids: [],
  supervisor_ids: [],
  company_ids: [],
  work_center_ids: [],
  department_ids: [],
};

type ReportTab = "chronological" | "summary" | "journal";

export default function ReportsPage() {
  const [tab, setTab] = useState<ReportTab>("chronological");
  const [dateFrom, setDateFrom] = useState(firstDayOfMonth());
  const [dateTo, setDateTo] = useState(todayStr());
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);

  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    companies: [], work_centers: [], departments: [], supervisors: [], employees: [],
  });
  const [branding, setBranding] = useState<Branding | null>(null);

  const [chronoData, setChronoData] = useState<DayReportRow[]>([]);
  const [summaryData, setSummaryData] = useState<EmployeeSummaryRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api.get<FilterOptions>("/reports/filter-options").then(setFilterOptions).catch(() => {});
    const slug = getStoredTenantSlug();
    if (slug) {
      api.get<Branding>(`/tenants/public/${slug}/branding`).then(setBranding).catch(() => {});
    }
  }, []);

  const setFilter = (key: keyof Filters) => (val: string[]) =>
    setFilters((prev) => ({ ...prev, [key]: val }));

  const buildQuery = useCallback(() => {
    const p = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
    filters.employee_ids.forEach((id) => p.append("employee_ids", id));
    filters.supervisor_ids.forEach((id) => p.append("supervisor_ids", id));
    filters.company_ids.forEach((id) => p.append("company_ids", id));
    filters.work_center_ids.forEach((id) => p.append("work_center_ids", id));
    filters.department_ids.forEach((id) => p.append("department_ids", id));
    return p.toString();
  }, [dateFrom, dateTo, filters]);

  const load = useCallback(async () => {
    if (!dateFrom || !dateTo) return;
    setLoading(true);
    setError(null);
    try {
      const q = buildQuery();
      const [chrono, summary] = await Promise.all([
        api.get<DayReportRow[]>(`/reports/chronological?${q}`),
        api.get<EmployeeSummaryRow[]>(`/reports/summary?${q}`),
      ]);
      setChronoData(chrono);
      setSummaryData(summary);
      setLoaded(true);
    } catch {
      setError("Error al cargar los informes.");
    } finally {
      setLoading(false);
    }
  }, [buildQuery]);

  const handleExportPDF = async () => {
    if (tab === "journal") return;
    setExporting(true);
    try { await exportPDF(tab, chronoData, summaryData, dateFrom, dateTo, branding); }
    finally { setExporting(false); }
  };

  const handleJournalPDF = async () => {
    setExporting(true);
    try {
      await api.download(
        `/reports/journal-pdf?${buildQuery()}`,
        `registro-jornada_${dateFrom}_${dateTo}.pdf`,
      );
    } catch {
      setError("No se pudo generar el registro de jornada.");
    } finally {
      setExporting(false);
    }
  };

  const activeFilterCount = Object.values(filters).reduce((n, arr) => n + arr.length, 0);

  return (
    <div className="page-content">
      <PageHeader title="Informes" subtitle="Cronológico y resumen por empleado" />

      <div className="report-filters">
        <div className="report-filter-group">
          <label className="report-filter-label">Desde</label>
          <input type="date" className="report-date-input" value={dateFrom} max={dateTo} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="report-filter-group">
          <label className="report-filter-label">Hasta</label>
          <input type="date" className="report-date-input" value={dateTo} min={dateFrom} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        <div className="report-filter-group">
          <label className="report-filter-label">Empleado</label>
          <MultiSearchSelect options={filterOptions.employees} value={filters.employee_ids} onChange={setFilter("employee_ids")} placeholder="Todos" />
        </div>
        <div className="report-filter-group">
          <label className="report-filter-label">Responsable</label>
          <MultiSearchSelect options={filterOptions.supervisors} value={filters.supervisor_ids} onChange={setFilter("supervisor_ids")} placeholder="Todos" />
        </div>
        <div className="report-filter-group">
          <label className="report-filter-label">Empresa</label>
          <MultiSearchSelect options={filterOptions.companies} value={filters.company_ids} onChange={setFilter("company_ids")} placeholder="Todas" />
        </div>
        <div className="report-filter-group">
          <label className="report-filter-label">Centro de trabajo</label>
          <MultiSearchSelect options={filterOptions.work_centers} value={filters.work_center_ids} onChange={setFilter("work_center_ids")} placeholder="Todos" />
        </div>
        <div className="report-filter-group">
          <label className="report-filter-label">Departamento</label>
          <MultiSearchSelect options={filterOptions.departments} value={filters.department_ids} onChange={setFilter("department_ids")} placeholder="Todos" />
        </div>
        <div className="report-filter-actions">
          {activeFilterCount > 0 && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setFilters(EMPTY_FILTERS)}>
              ✕ {activeFilterCount}
            </button>
          )}
          <button type="button" className="btn btn-primary" onClick={load} disabled={loading}>
            {loading ? "Cargando…" : "Aplicar"}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="report-bar">
        <div className="tabs">
          <button type="button" className={tab === "chronological" ? "tab active" : "tab"} onClick={() => setTab("chronological")}>
            Cronológico
          </button>
          <button type="button" className={tab === "summary" ? "tab active" : "tab"} onClick={() => setTab("summary")}>
            Resumen
          </button>
          <button type="button" className={tab === "journal" ? "tab active" : "tab"} onClick={() => setTab("journal")}>
            Registro de jornada
          </button>
        </div>
        {loaded && tab !== "journal" && (
          <div className="report-export-btns">
            <button type="button" className="btn btn-sm" onClick={() => exportExcel(tab, chronoData, summaryData, dateFrom, dateTo)}>
              Exportar Excel
            </button>
            <button type="button" className="btn btn-sm" onClick={handleExportPDF} disabled={exporting}>
              {exporting ? "Generando…" : "Exportar PDF"}
            </button>
          </div>
        )}
      </div>

      {!loaded && !loading && (
        <div className="report-placeholder">
          Selecciona un rango de fechas y pulsa <strong>Aplicar</strong> para generar el informe.
        </div>
      )}

      {loaded && tab === "chronological" && <ChronologicalTable rows={chronoData} />}
      {loaded && tab === "summary" && <SummaryTable rows={summaryData} days={chronoData} />}
      {loaded && tab === "journal" && (
        <div className="report-journal-panel">
          <div className="report-journal-info">
            <h3>Registro Diario de Jornada</h3>
            <p>
              Documento oficial según el <strong>Real Decreto-ley 8/2019, de 8 de marzo</strong>.
              Se genera un PDF con un registro por trabajador y mes para el rango y los filtros
              seleccionados, con hora de entrada, hora de salida, total de horas y líneas de firma
              para la empresa y el trabajador.
            </p>
            <p className="report-hint">
              Solo se incluyen los trabajadores con fichajes en el periodo. Ajusta los filtros de
              arriba para limitar el documento (por empleado, centro, etc.).
            </p>
          </div>
          <button type="button" className="btn btn-primary" onClick={handleJournalPDF} disabled={exporting}>
            {exporting ? "Generando…" : "Descargar registro (PDF)"}
          </button>
        </div>
      )}
    </div>
  );
}
