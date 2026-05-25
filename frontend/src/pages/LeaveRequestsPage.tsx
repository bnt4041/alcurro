import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { LeaveRequest, LeaveStatus } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";
import { tableActionButtons } from "../lib/tableFormatters";

const STATUSES: { value: LeaveStatus; label: string }[] = [
  { value: "pending", label: "Pendiente" },
  { value: "approved", label: "Aprobada" },
  { value: "rejected", label: "Rechazada" },
  { value: "cancelled", label: "Cancelada" },
];

type LeaveRow = LeaveRequest & { employee_name: string; status_label: string };

export default function LeaveRequestsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
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
  const canCreate = user && canModule(user.permissions, "create", "leave");
  const canUpdate = user && canModule(user.permissions, "update", "leave");
  const canAdmin = user && canModule(user.permissions, "admin", "leave");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<LeaveRequest[]>("/leave-requests"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tableData = useMemo<LeaveRow[]>(
    () =>
      rows.map((r) => ({
        ...r,
        employee_name: byId(r.employee_id),
        status_label: STATUSES.find((s) => s.value === r.status)?.label ?? r.status,
      })),
    [rows, byId]
  );

  const columns = useMemo<DataTableColumn<LeaveRow>[]>(() => {
    const cols: DataTableColumn<LeaveRow>[] = [
      { title: "Empleado", field: "employee_name", headerFilter: "input", minWidth: 150 },
      { title: "Inicio", field: "start_date", headerFilter: "input", width: 120 },
      { title: "Fin", field: "end_date", headerFilter: "input", width: 120 },
      { title: "Días", field: "days_requested", headerFilter: "number", width: 80 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: Object.fromEntries(STATUSES.map((s) => [s.label, s.label])),
        },
        width: 120,
      },
      {
        title: "Motivo",
        field: "reason",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 140,
      },
    ];
    if (canUpdate || canAdmin) {
      const actions: { id: string; label: string; className?: string }[] = [];
      if (canUpdate) actions.push({ id: "edit", label: "Editar" });
      if (canAdmin) actions.push({ id: "delete", label: "Borrar", className: "btn-danger" });
      cols.push({
        title: "",
        field: "id",
        headerFilter: false,
        sorter: false,
        download: false,
        width: 140,
        formatter: () => tableActionButtons(actions),
      });
    }
    return cols;
  }, [canUpdate, canAdmin]);

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

  const onCellAction = (action: string, row: LeaveRow) => {
    if (action === "edit") openEdit(row);
    else if (action === "delete") remove(row.id);
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
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="vacaciones"
        height="520px"
        onCellAction={onCellAction}
      />
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
