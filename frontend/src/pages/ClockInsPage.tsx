import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { ClockIn, ClockInType } from "../api/types";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

export default function ClockInsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const [rows, setRows] = useState<ClockIn[]>([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    employee_id: "",
    record_type: "entrada" as ClockInType,
    notes: "",
  });
  const canWrite = user && canModule(user.permissions, "write", "clock_ins");

  const load = useCallback(async () => {
    const path = buildQuery({
      q: search || undefined,
      record_type: typeFilter || undefined,
      limit: "300",
    });
    setRows(await api.get<ClockIn[]>(`/clock-ins${path}`));
  }, [search, typeFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/clock-ins", {
      ...form,
      source: "panel",
      latitude: null,
      longitude: null,
    });
    setOpen(false);
    load();
  };

  return (
    <>
      <PageHeader
        title="Fichajes"
        subtitle="Registro inalterable — sin borrado (normativa española)"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
              + Fichaje manual
            </button>
          ) : undefined
        }
      />
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
              { value: "entrada", label: "Entrada" },
              { value: "salida", label: "Salida" },
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
              <th>GPS</th>
              <th>Notas</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{new Date(r.recorded_at).toLocaleString("es-ES")}</td>
                <td>{byId(r.employee_id)}</td>
                <td>
                  <span
                    className={`badge ${r.record_type === "entrada" ? "badge-ok" : "badge-warn"}`}
                  >
                    {r.record_type}
                  </span>
                </td>
                <td>{r.source}</td>
                <td>
                  {r.latitude != null
                    ? `${r.latitude.toFixed(4)}, ${r.longitude?.toFixed(4)}`
                    : "—"}
                </td>
                <td>{r.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal title="Fichaje manual" open={open && !!canWrite} onClose={() => setOpen(false)}>
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
                setForm({ ...form, record_type: ev.target.value as ClockInType })
              }
            >
              <option value="entrada">Entrada</option>
              <option value="salida">Salida</option>
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
