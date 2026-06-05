import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, buildQuery } from "../api/client";
import type {
  ClockIn,
  ClockSettings,
  EmployeeDayReport,
  Project,
} from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

type ClockInRow = ClockIn & {
  employee_name: string;
  entrada_label: string;
  salida_label: string;
  duration_label: string;
  gps_label: string;
  project_label: string;
};

function formatMins(m: number) {
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h} h ${r} min` : `${h} h`;
}

function durationMins(entrada: string, salida: string | null): number | null {
  if (!salida) return null;
  return Math.round((new Date(salida).getTime() - new Date(entrada).getTime()) / 60000);
}

export default function ClockInsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const [rows, setRows] = useState<ClockIn[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [report, setReport] = useState<EmployeeDayReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportForm, setReportForm] = useState({
    employee_id: "",
    report_date: new Date().toISOString().slice(0, 10),
  });
  const [clockSettings, setClockSettings] = useState<ClockSettings | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const now = new Date().toISOString().slice(0, 16);
  const [form, setForm] = useState({
    employee_id: "",
    entrada_at: now,
    salida_at: "",
    notes: "",
    work_summary: "",
    project_id: "",
  });
  const canCreate = user && canModule(user.permissions, "create", "clock_ins");
  const canRead = user && canModule(user.permissions, "read", "clock_ins");
  const canConfig = user && canModule(user.permissions, "write", "clock_ins");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const path = buildQuery({ limit: "2000" });
      setRows(await api.get<ClockIn[]>(`/clock-ins${path}`));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!canConfig) return;
    api.get<ClockSettings>("/clock-settings").then(setClockSettings).catch(() => {});
    api.get<Project[]>("/projects").then(setProjects).catch(() => setProjects([]));
  }, [canConfig]);

  const tableData = useMemo<ClockInRow[]>(
    () =>
      rows.map((r) => {
        const mins = durationMins(r.entrada_at, r.salida_at);
        return {
          ...r,
          employee_name: byId(r.employee_id),
          entrada_label: new Date(r.entrada_at).toLocaleString("es-ES"),
          salida_label: r.salida_at ? new Date(r.salida_at).toLocaleString("es-ES") : "—",
          duration_label: mins != null ? formatMins(mins) : "En curso",
          gps_label:
            r.latitude != null
              ? `${r.latitude.toFixed(4)}, ${r.longitude?.toFixed(4)}`
              : "—",
          project_label: r.project_name ?? "—",
        };
      }),
    [rows, byId]
  );

  const requireProject = clockSettings?.require_project_on_clock_in ?? false;

  const columns = useMemo<DataTableColumn<ClockInRow>[]>(
    () => [
      {
        title: "Entrada",
        field: "entrada_at",
        headerFilter: "input",
        sorter: "datetime",
        formatter: (c) => new Date(String(c.getValue())).toLocaleString("es-ES"),
        minWidth: 155,
      },
      {
        title: "Salida",
        field: "salida_label",
        headerFilter: "input",
        minWidth: 155,
      },
      {
        title: "Duración",
        field: "duration_label",
        minWidth: 100,
      },
      {
        title: "Empleado",
        field: "employee_name",
        headerFilter: "input",
        minWidth: 160,
      },
      {
        title: "Proyecto",
        field: "project_label",
        headerFilter: "input",
        minWidth: 130,
      },
      {
        title: "Origen",
        field: "source",
        headerFilter: "input",
        width: 100,
      },
      {
        title: "GPS",
        field: "gps_label",
        headerFilter: "input",
        minWidth: 140,
      },
      {
        title: "Resumen del día",
        field: "work_summary",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 160,
      },
      {
        title: "Notas",
        field: "notes",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 120,
      },
    ],
    []
  );

  const save = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/clock-ins", {
      employee_id: form.employee_id,
      entrada_at: new Date(form.entrada_at).toISOString(),
      salida_at: form.salida_at ? new Date(form.salida_at).toISOString() : null,
      notes: form.notes || null,
      work_summary: form.work_summary || null,
      project_id: form.project_id || null,
      source: "panel",
      latitude: null,
      longitude: null,
    });
    setOpen(false);
    setForm({ employee_id: "", entrada_at: now, salida_at: "", notes: "", work_summary: "", project_id: "" });
    load();
  };

  const loadReport = async (e: FormEvent) => {
    e.preventDefault();
    if (!reportForm.employee_id) return;
    setReportLoading(true);
    try {
      const q = buildQuery({ employee_id: reportForm.employee_id, report_date: reportForm.report_date });
      setReport(await api.get<EmployeeDayReport>(`/clock-ins/reports/day${q}`));
    } catch (err) {
      setReport(null);
      alert(String(err));
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Fichajes"
        subtitle="Registro inalterable — un registro por jornada con entrada y salida"
        action={
          <div className="header-actions">
            {canRead && (
              <button type="button" className="btn" onClick={() => setReportOpen(true)}>
                Informe del día
              </button>
            )}
            {canRead && (
              <Link to="/app/incidencias" className="btn">Incidencias</Link>
            )}
            {canConfig && (
              <Link to="/app/fichajes/configuracion" className="btn">Configuración</Link>
            )}
            {canCreate && (
              <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
                + Fichaje manual
              </button>
            )}
          </div>
        }
      />
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="fichajes"
        height="560px"
        onImportComplete={load}
      />

      <Modal title="Informe de fichajes y paradas" open={reportOpen} onClose={() => setReportOpen(false)} wide>
        <form onSubmit={loadReport} className="form-grid">
          <label>
            Empleado
            <select required value={reportForm.employee_id}
              onChange={(ev) => setReportForm({ ...reportForm, employee_id: ev.target.value })}>
              <option value="">Seleccionar…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>{e.full_name}</option>
              ))}
            </select>
          </label>
          <label>
            Fecha
            <input type="date" required value={reportForm.report_date}
              onChange={(ev) => setReportForm({ ...reportForm, report_date: ev.target.value })} />
          </label>
          <div className="form-actions form-grid-full">
            <button type="submit" className="btn btn-primary" disabled={reportLoading}>
              {reportLoading ? "Cargando…" : "Generar informe"}
            </button>
          </div>
        </form>
        {report && (
          <div className="day-report" style={{ marginTop: "1rem" }}>
            <p>
              <strong>{report.employee_name}</strong> ·{" "}
              {new Date(report.report_date).toLocaleDateString("es-ES")}
            </p>
            <p className="muted small">
              Trabajado: {formatMins(report.worked_minutes)}
              {report.break_minutes > 0 && ` · Paradas: ${formatMins(report.break_minutes)}`}
            </p>
            <ul className="day-report-timeline">
              {report.timeline.map((it, i) => (
                <li key={i} className={it.kind === "parada" ? "is-break" : ""}>
                  <span className="day-report-time">{it.time_label}</span>
                  <span className="day-report-label">{it.label}</span>
                  {it.detail && <span className="muted small"> — {it.detail}</span>}
                </li>
              ))}
            </ul>
            {report.timeline.length === 0 && <p className="muted">Sin fichajes ese día.</p>}
          </div>
        )}
      </Modal>

      <Modal title="Fichaje manual" open={open && !!canCreate} onClose={() => setOpen(false)}>
        <form onSubmit={save} className="form-grid">
          <label>
            Empleado
            <select required value={form.employee_id}
              onChange={(ev) => setForm({ ...form, employee_id: ev.target.value })}>
              <option value="">Seleccionar…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>{e.full_name} ({e.employee_code})</option>
              ))}
            </select>
          </label>
          <label>
            Hora de entrada
            <input type="datetime-local" required value={form.entrada_at}
              onChange={(ev) => setForm({ ...form, entrada_at: ev.target.value })} />
          </label>
          <label>
            Hora de salida (opcional)
            <input type="datetime-local" value={form.salida_at}
              onChange={(ev) => setForm({ ...form, salida_at: ev.target.value })} />
          </label>
          {(requireProject || projects.length > 0) && (
            <label>
              Proyecto{requireProject ? "" : " (opcional)"}
              <select required={requireProject} value={form.project_id}
                onChange={(ev) => setForm({ ...form, project_id: ev.target.value })}>
                <option value="">{requireProject ? "Seleccionar proyecto…" : "Sin proyecto"}</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                ))}
              </select>
            </label>
          )}
          <label>
            Resumen del día
            <input value={form.work_summary}
              onChange={(ev) => setForm({ ...form, work_summary: ev.target.value })}
              placeholder="Qué ha hecho el empleado…" />
          </label>
          <label>
            Notas internas
            <input value={form.notes}
              onChange={(ev) => setForm({ ...form, notes: ev.target.value })} />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">Registrar</button>
          </div>
        </form>
      </Modal>
    </>
  );
}
