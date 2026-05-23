import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { BreakType } from "../api/types";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

interface WorkBreak {
  id: string;
  employee_id: string;
  record_type: BreakType;
  recorded_at: string;
  source: string;
  notes: string | null;
}

interface BreakSummaryRow {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  company_id: string;
  total_minutes: number;
  total_hours: number;
  break_starts: number;
  break_ends: number;
  open_breaks: number;
}

interface BreakCompanySummary {
  company_id: string;
  company_name: string;
  total_minutes: number;
  total_hours: number;
  employee_count: number;
}

interface BreakSummaryResponse {
  rows: BreakSummaryRow[];
  by_company: BreakCompanySummary[];
  period_from: string | null;
  period_to: string | null;
}

const BREAK_LABELS: Record<BreakType, string> = {
  inicio_parada: "Inicio parada",
  fin_parada: "Fin parada",
};

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return `${h} h ${m} min`;
}

export default function BreaksPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const [rows, setRows] = useState<WorkBreak[]>([]);
  const [summary, setSummary] = useState<BreakSummaryResponse | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    employee_id: "",
    record_type: "inicio_parada" as BreakType,
    notes: "",
  });
  const canWrite = user && canModule(user.permissions, "write", "clock_ins");

  const load = useCallback(async () => {
    const path = buildQuery({
      q: search || undefined,
      record_type: typeFilter || undefined,
      limit: "300",
    });
    const summaryPath = buildQuery({
      from: fromDate || undefined,
      to: toDate || undefined,
    });
    const [list, sum] = await Promise.all([
      api.get<WorkBreak[]>(`/breaks${path}`),
      api.get<BreakSummaryResponse>(`/breaks/summary${summaryPath}`),
    ]);
    setRows(list);
    setSummary(sum);
  }, [search, typeFilter, fromDate, toDate]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/breaks", { ...form, notes: form.notes || null });
    setOpen(false);
    load();
  };

  return (
    <>
      <PageHeader
        title="Paradas"
        subtitle="Descansos durante la jornada — filtrados por empresa/centro/departamento"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
              + Parada manual
            </button>
          ) : undefined
        }
      />

      <section className="card settings-section">
        <h3>Resumen por empresa (ámbito actual)</h3>
        <div className="form-grid" style={{ marginBottom: "1rem" }}>
          <label>
            Desde
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
            />
          </label>
          <label>
            Hasta
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </label>
          <div className="form-actions" style={{ alignSelf: "end" }}>
            <button type="button" className="btn btn-ghost" onClick={load}>
              Actualizar resumen
            </button>
          </div>
        </div>
        {summary && summary.by_company.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Empresa</th>
                  <th>Empleados</th>
                  <th>Tiempo en parada</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_company.map((c) => (
                  <tr key={c.company_id}>
                    <td>{c.company_name}</td>
                    <td>{c.employee_count}</td>
                    <td>{formatDuration(c.total_minutes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted small">Sin paradas en el periodo seleccionado.</p>
        )}
      </section>

      {summary && summary.rows.length > 0 && (
        <section className="card settings-section">
          <h3>Detalle por empleado</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Empleado</th>
                  <th>Código</th>
                  <th>Tiempo parada</th>
                  <th>Inicios</th>
                  <th>Fines</th>
                  <th>Abiertas</th>
                </tr>
              </thead>
              <tbody>
                {summary.rows
                  .filter((r) => r.total_minutes > 0 || r.break_starts > 0)
                  .map((r) => (
                    <tr key={r.employee_id}>
                      <td>{r.employee_name}</td>
                      <td>
                        <code>{r.employee_code}</code>
                      </td>
                      <td>{formatDuration(r.total_minutes)}</td>
                      <td>{r.break_starts}</td>
                      <td>{r.break_ends}</td>
                      <td>{r.open_breaks > 0 ? r.open_breaks : "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <TableToolbar
        search={search}
        onSearchChange={setSearch}
        onSubmit={load}
        placeholder="Buscar por empleado…"
        filters={[
          {
            label: "Tipo",
            value: typeFilter,
            onChange: setTypeFilter,
            options: [
              { value: "inicio_parada", label: "Inicio parada" },
              { value: "fin_parada", label: "Fin parada" },
            ],
          },
        ]}
      />
      <div className="table-wrap card">
        <table>
          <thead>
            <tr>
              <th>Fecha/hora</th>
              <th>Empleado</th>
              <th>Tipo</th>
              <th>Origen</th>
              <th>Notas</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{new Date(r.recorded_at).toLocaleString("es-ES")}</td>
                <td>{byId(r.employee_id)}</td>
                <td>
                  <span className="badge">{BREAK_LABELS[r.record_type]}</span>
                </td>
                <td>{r.source}</td>
                <td>{r.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal title="Parada manual" open={open && !!canWrite} onClose={() => setOpen(false)}>
        <form onSubmit={save} className="form-grid">
          <label>
            Empleado
            <select
              required
              value={form.employee_id}
              onChange={(ev) => setForm({ ...form, employee_id: ev.target.value })}
            >
              <option value="">Seleccionar…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name} ({e.employee_code})
                </option>
              ))}
            </select>
          </label>
          <label>
            Tipo
            <select
              value={form.record_type}
              onChange={(ev) =>
                setForm({ ...form, record_type: ev.target.value as BreakType })
              }
            >
              <option value="inicio_parada">Inicio de parada</option>
              <option value="fin_parada">Fin de parada</option>
            </select>
          </label>
          <label>
            Notas
            <input
              value={form.notes}
              onChange={(ev) => setForm({ ...form, notes: ev.target.value })}
            />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Registrar
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
