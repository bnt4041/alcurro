import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { BreakType } from "../api/types";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import DataTable, { type DataTableColumn } from "../components/DataTable";
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

type BreakRow = WorkBreak & {
  employee_name: string;
  recorded_at_label: string;
  type_label: string;
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
  const [loading, setLoading] = useState(true);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    employee_id: "",
    record_type: "inicio_parada" as BreakType,
    notes: "",
  });
  const canCreate = user && canModule(user.permissions, "create", "breaks");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const summaryPath = buildQuery({
        from: fromDate || undefined,
        to: toDate || undefined,
      });
      const [list, sum] = await Promise.all([
        api.get<WorkBreak[]>(`/breaks?limit=2000`),
        api.get<BreakSummaryResponse>(`/breaks/summary${summaryPath}`),
      ]);
      setRows(list);
      setSummary(sum);
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    load();
  }, [load]);

  const breakTableData = rows.map((r) => ({
    ...r,
    employee_name: byId(r.employee_id),
    recorded_at_label: new Date(r.recorded_at).toLocaleString("es-ES"),
    type_label: BREAK_LABELS[r.record_type],
  }));

  const breakColumns: DataTableColumn<BreakRow>[] = [
    {
      title: "Fecha/hora",
      field: "recorded_at",
      headerFilter: "input",
      sorter: "datetime",
      formatter: (c) => new Date(String(c.getValue())).toLocaleString("es-ES"),
      minWidth: 160,
    },
    { title: "Empleado", field: "employee_name", headerFilter: "input", minWidth: 140 },
    {
      title: "Tipo",
      field: "type_label",
      headerFilter: "select",
      headerFilterParams: {
        values: {
          "": "Todos",
          "Inicio parada": "Inicio parada",
          "Fin parada": "Fin parada",
        },
      },
      width: 130,
    },
    { title: "Origen", field: "source", headerFilter: "input", width: 100 },
    {
      title: "Notas",
      field: "notes",
      headerFilter: "input",
      formatter: (c) => String(c.getValue() ?? "—"),
    },
  ];

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
          canCreate ? (
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
          <DataTable
            data={summary.by_company.map((c) => ({
              ...c,
              duration_label: formatDuration(c.total_minutes),
            }))}
            columns={[
              { title: "Empresa", field: "company_name", headerFilter: "input" },
              { title: "Empleados", field: "employee_count", headerFilter: "number" },
              { title: "Tiempo en parada", field: "duration_label", headerFilter: "input" },
            ]}
            exportFilename="resumen_paradas_empresa"
            height="220px"
          />
        ) : (
          <p className="muted small">Sin paradas en el periodo seleccionado.</p>
        )}
      </section>

      {summary && summary.rows.length > 0 && (
        <section className="card settings-section">
          <h3>Detalle por empleado</h3>
          <DataTable
            data={summary.rows
              .filter((r) => r.total_minutes > 0 || r.break_starts > 0)
              .map((r) => ({
                ...r,
                duration_label: formatDuration(r.total_minutes),
                open_label: r.open_breaks > 0 ? String(r.open_breaks) : "—",
              }))}
            columns={[
              { title: "Empleado", field: "employee_name", headerFilter: "input" },
              {
                title: "Código",
                field: "employee_code",
                headerFilter: "input",
                formatter: (c) => `<code>${c.getValue()}</code>`,
              },
              { title: "Tiempo parada", field: "duration_label", headerFilter: "input" },
              { title: "Inicios", field: "break_starts", headerFilter: "number" },
              { title: "Fines", field: "break_ends", headerFilter: "number" },
              { title: "Abiertas", field: "open_label", headerFilter: "input" },
            ]}
            exportFilename="resumen_paradas_empleados"
            height="280px"
          />
        </section>
      )}

      <h3 className="employee-profile-subtitle">Registro de paradas</h3>
      <DataTable
        data={breakTableData}
        columns={breakColumns}
        loading={loading}
        exportFilename="paradas"
        height="480px"
      />

      <Modal title="Parada manual" open={open && !!canCreate} onClose={() => setOpen(false)}>
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
