import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { LeaveRequest, LeaveStatus } from "../api/types";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

const STATUSES: { value: LeaveStatus; label: string }[] = [
  { value: "pending", label: "Pendiente" },
  { value: "approved", label: "Aprobada" },
  { value: "rejected", label: "Rechazada" },
  { value: "cancelled", label: "Cancelada" },
];

export default function LeaveRequestsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<LeaveRequest | null>(null);
  const [form, setForm] = useState({
    employee_id: "",
    start_date: "",
    end_date: "",
    days_requested: 1,
    status: "pending" as LeaveStatus,
    reason: "",
    review_notes: "",
  });
  const canWrite = user && canModule(user.permissions, "write", "leave");
  const canCreate = user && canModule(user.permissions, "create", "leave");
  const canUpdate = user && canModule(user.permissions, "update", "leave");
  const canAdmin = user && canModule(user.permissions, "admin", "leave");

  const load = useCallback(async () => {
    const path = buildQuery({
      q: search || undefined,
      status: statusFilter || undefined,
    });
    setRows(await api.get<LeaveRequest[]>(`/leave-requests${path}`));
  }, [search, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm({
      employee_id: "",
      start_date: "",
      end_date: "",
      days_requested: 1,
      status: "pending",
      reason: "",
      review_notes: "",
    });
    setOpen(true);
  };

  const openEdit = (r: LeaveRequest) => {
    setEditing(r);
    setForm({
      employee_id: r.employee_id,
      start_date: r.start_date,
      end_date: r.end_date,
      days_requested: r.days_requested,
      status: r.status,
      reason: r.reason ?? "",
      review_notes: r.review_notes ?? "",
    });
    setOpen(true);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (editing) await api.patch(`/leave-requests/${editing.id}`, form);
    else await api.post("/leave-requests", form);
    setOpen(false);
    load();
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar solicitud?")) return;
    await api.delete(`/leave-requests/${id}`);
    load();
  };

  return (
    <>
      <PageHeader
        title="Vacaciones"
        subtitle="Solicitudes, aprobaciones y saldo"
        action={
          canCreate ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nueva solicitud
            </button>
          ) : undefined
        }
      />
      <TableToolbar
        search={search}
        onSearchChange={setSearch}
        onSubmit={load}
        placeholder="Buscar empleado…"
        filters={[
          {
            label: "Estado",
            value: statusFilter,
            onChange: setStatusFilter,
            options: STATUSES.map((s) => ({ value: s.value, label: s.label })),
          },
        ]}
      />
      <div className="table-wrap card">
        <table>
          <thead>
            <tr>
              <th>Empleado</th>
              <th>Inicio</th>
              <th>Fin</th>
              <th>Días</th>
              <th>Estado</th>
              <th>Motivo</th>
              {(canUpdate || canAdmin) && <th></th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{byId(r.employee_id)}</td>
                <td>{r.start_date}</td>
                <td>{r.end_date}</td>
                <td>{r.days_requested}</td>
                <td>
                  <span className={`badge badge-${r.status}`}>{r.status}</span>
                </td>
                <td>{r.reason ?? "—"}</td>
                {(canUpdate || canAdmin) && (
                  <td className="actions">
                    {canUpdate && (
                      <button type="button" className="btn btn-sm" onClick={() => openEdit(r)}>
                        Editar
                      </button>
                    )}
                    {canAdmin && (
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={() => remove(r.id)}
                      >
                        Borrar
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal
        title={editing ? "Editar vacaciones" : "Nueva solicitud"}
        open={open && !!(editing ? canUpdate : canCreate)}
        onClose={() => setOpen(false)}
        wide
      >
        <form onSubmit={save} className="form-grid">
          <label>
            Empleado
            <select
              required
              value={form.employee_id}
              onChange={(ev) => setForm({ ...form, employee_id: ev.target.value })}
              disabled={!!editing}
            >
              <option value="">Seleccionar…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Inicio
            <input
              type="date"
              required
              value={form.start_date}
              onChange={(ev) => setForm({ ...form, start_date: ev.target.value })}
            />
          </label>
          <label>
            Fin
            <input
              type="date"
              required
              value={form.end_date}
              onChange={(ev) => setForm({ ...form, end_date: ev.target.value })}
            />
          </label>
          <label>
            Días
            <input
              type="number"
              step="0.5"
              value={form.days_requested}
              onChange={(ev) =>
                setForm({ ...form, days_requested: parseFloat(ev.target.value) })
              }
            />
          </label>
          <label>
            Estado
            <select
              value={form.status}
              onChange={(ev) =>
                setForm({ ...form, status: ev.target.value as LeaveStatus })
              }
            >
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="full">
            Motivo
            <textarea
              value={form.reason}
              onChange={(ev) => setForm({ ...form, reason: ev.target.value })}
            />
          </label>
          {editing && (
            <label className="full">
              Notas revisión
              <textarea
                value={form.review_notes}
                onChange={(ev) =>
                  setForm({ ...form, review_notes: ev.target.value })
                }
              />
            </label>
          )}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Guardar
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
