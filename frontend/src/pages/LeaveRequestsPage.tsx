import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { EmployeeLeaveBalance, LeaveRequest, LeaveStatus, LeaveType } from "../api/types";
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

function emptyForm(leaveTypes: LeaveType[]) {
  return {
    employee_id: "",
    start_date: "",
    end_date: "",
    days_requested: 1,
    status: "pending" as LeaveStatus,
    leave_type_id: leaveTypes[0]?.id ?? "",
    reason: "",
    review_notes: "",
  };
}

export default function LeaveRequestsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<LeaveRequest | null>(null);
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [form, setForm] = useState(emptyForm([]));

  // Leave-type management state
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [editingType, setEditingType] = useState<LeaveType | null>(null);
  const [typeForm, setTypeForm] = useState({
    name: "",
    deducts_balance: true,
    has_own_balance: false,
    default_days: "" as string | number,
  });

  // Balance management state
  const [balanceEmpId, setBalanceEmpId] = useState<string>("");
  const [balances, setBalances] = useState<EmployeeLeaveBalance[]>([]);
  const [savingBalance, setSavingBalance] = useState<string | null>(null);

  const canCreate = user && canModule(user.permissions, "create", "leave");
  const canUpdate = user && canModule(user.permissions, "update", "leave");
  const canAdmin = user && canModule(user.permissions, "admin", "leave");

  const loadTypes = useCallback(async () => {
    try {
      setLeaveTypes(await api.get<LeaveType[]>("/leave-types"));
    } catch {
      setLeaveTypes([]);
    }
  }, []);

  const loadBalances = useCallback(async (empId: string) => {
    if (!empId) { setBalances([]); return; }
    try {
      setBalances(await api.get<EmployeeLeaveBalance[]>(`/employees/${empId}/leave-balances`));
    } catch {
      setBalances([]);
    }
  }, []);

  useEffect(() => { loadBalances(balanceEmpId); }, [balanceEmpId, loadBalances]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<LeaveRequest[]>("/leave-requests"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTypes();
    load();
  }, [load, loadTypes]);

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
      { title: "Tipo", field: "leave_type_name", headerFilter: "input", width: 130,
        formatter: (c) => String(c.getValue() ?? "—") },
      { title: "Inicio", field: "start_date", headerFilter: "input", width: 110 },
      { title: "Fin", field: "end_date", headerFilter: "input", width: 110 },
      { title: "Días", field: "days_requested", headerFilter: "number", width: 75 },
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
    setForm(emptyForm(leaveTypes));
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
      leave_type_id: r.leave_type_id ?? leaveTypes[0]?.id ?? "",
      reason: r.reason ?? "",
      review_notes: r.review_notes ?? "",
    });
    setOpen(true);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    const payload = { ...form, leave_type_id: form.leave_type_id || null };
    if (editing) await api.patch(`/leave-requests/${editing.id}`, payload);
    else await api.post("/leave-requests", payload);
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

  // Leave-type management
  const openTypeCreate = () => {
    setEditingType(null);
    setTypeForm({ name: "", deducts_balance: true, has_own_balance: false, default_days: "" });
    setTypeModalOpen(true);
  };

  const openTypeEdit = (lt: LeaveType) => {
    setEditingType(lt);
    setTypeForm({
      name: lt.name,
      deducts_balance: lt.deducts_balance,
      has_own_balance: lt.has_own_balance,
      default_days: lt.default_days ?? "",
    });
    setTypeModalOpen(true);
  };

  const saveType = async (e: FormEvent) => {
    e.preventDefault();
    const payload = {
      ...typeForm,
      default_days: typeForm.default_days !== "" ? Number(typeForm.default_days) : null,
    };
    if (editingType) {
      await api.patch(`/leave-types/${editingType.id}`, payload);
    } else {
      await api.post("/leave-types", payload);
    }
    setTypeModalOpen(false);
    loadTypes();
  };

  const saveBalance = async (empId: string, leaveTypeId: string, totalDays: number) => {
    setSavingBalance(leaveTypeId);
    try {
      await api.put(`/employees/${empId}/leave-balances/${leaveTypeId}`, { total_days: totalDays });
      await loadBalances(empId);
    } finally {
      setSavingBalance(null);
    }
  };

  const deleteType = async (lt: LeaveType) => {
    if (!confirm(`¿Eliminar tipo "${lt.name}"?`)) return;
    await api.delete(`/leave-types/${lt.id}`);
    loadTypes();
  };

  return (
    <>
      <PageHeader
        title="Permisos"
        subtitle="Solicitudes, aprobaciones y saldo de vacaciones"
        action={
          canCreate ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nueva solicitud
            </button>
          ) : undefined
        }
      />

      {canAdmin && (
        <section className="leave-types-section">
          <div className="leave-types-header">
            <h3 className="leave-types-title">Tipos de permiso</h3>
            <button type="button" className="btn btn-sm" onClick={openTypeCreate}>
              + Añadir tipo
            </button>
          </div>
          <div className="leave-types-list">
            {leaveTypes.map((lt) => (
              <div key={lt.id} className="leave-type-chip">
                <span className="leave-type-chip__name">{lt.name}</span>
                {lt.has_own_balance && (
                  <span className="leave-type-chip__tag own-balance">
                    saldo propio{lt.default_days != null ? ` (${lt.default_days}d)` : ""}
                  </span>
                )}
                {!lt.has_own_balance && (
                  <span className={`leave-type-chip__tag ${lt.deducts_balance ? "deducts" : "no-deducts"}`}>
                    {lt.deducts_balance ? "resta vacaciones" : "no resta"}
                  </span>
                )}
                <button type="button" className="btn btn-xs" onClick={() => openTypeEdit(lt)}>
                  Editar
                </button>
                {!lt.is_default && (
                  <button type="button" className="btn btn-xs btn-danger" onClick={() => deleteType(lt)}>
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Balance por empleado */}
          {leaveTypes.some((lt) => lt.has_own_balance) && (
            <div className="leave-balance-panel">
              <h4 className="leave-types-title" style={{ marginTop: "1rem" }}>
                Saldos por empleado
              </h4>
              <div className="leave-balance-row" style={{ marginBottom: "0.5rem" }}>
                <select
                  className="leave-balance-emp-select"
                  value={balanceEmpId}
                  onChange={(e) => setBalanceEmpId(e.target.value)}
                >
                  <option value="">Seleccionar empleado…</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>{e.full_name}</option>
                  ))}
                </select>
              </div>
              {balanceEmpId && (
                <table className="leave-balance-table">
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Total días</th>
                      <th>Usados</th>
                      <th>Restantes</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {balances
                      .filter((b) => {
                        const lt = leaveTypes.find((t) => t.id === b.leave_type_id);
                        return lt?.has_own_balance;
                      })
                      .map((b) => (
                        <BalanceRow
                          key={b.leave_type_id}
                          balance={b}
                          saving={savingBalance === b.leave_type_id}
                          onSave={(days) => saveBalance(balanceEmpId, b.leave_type_id, days)}
                        />
                      ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>
      )}

      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="permisos"
        height="520px"
        onCellAction={onCellAction}
      />

      {/* Request modal */}
      <Modal
        title={editing ? "Editar permiso" : "Nueva solicitud"}
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
            Tipo de permiso
            <select
              value={form.leave_type_id}
              onChange={(ev) => setForm({ ...form, leave_type_id: ev.target.value })}
            >
              <option value="">Sin tipo…</option>
              {leaveTypes.map((lt) => (
                <option key={lt.id} value={lt.id}>
                  {lt.name}{lt.deducts_balance ? " (resta vacaciones)" : ""}
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

      {/* Leave type modal */}
      <Modal
        title={editingType ? "Editar tipo de permiso" : "Nuevo tipo de permiso"}
        open={typeModalOpen}
        onClose={() => setTypeModalOpen(false)}
      >
        <form onSubmit={saveType} className="form-grid">
          <label className="full">
            Nombre
            <input
              type="text"
              required
              value={typeForm.name}
              onChange={(ev) => setTypeForm({ ...typeForm, name: ev.target.value })}
              placeholder="Ej: Permiso retribuido"
            />
          </label>
          <label className="full leave-type-check-label">
            <input
              type="checkbox"
              checked={typeForm.has_own_balance}
              onChange={(ev) =>
                setTypeForm({ ...typeForm, has_own_balance: ev.target.checked, deducts_balance: ev.target.checked ? false : typeForm.deducts_balance })
              }
            />
            Tiene saldo propio por empleado
          </label>
          {typeForm.has_own_balance ? (
            <label className="full">
              Días por defecto
              <input
                type="number"
                step="0.5"
                min="0"
                value={typeForm.default_days}
                onChange={(ev) => setTypeForm({ ...typeForm, default_days: ev.target.value })}
                placeholder="Ej: 3"
              />
              <span className="form-hint">Días que se asignan a cada empleado al crear su saldo</span>
            </label>
          ) : (
            <label className="full leave-type-check-label">
              <input
                type="checkbox"
                checked={typeForm.deducts_balance}
                onChange={(ev) =>
                  setTypeForm({ ...typeForm, deducts_balance: ev.target.checked })
                }
              />
              Resta días de vacaciones
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

function BalanceRow({
  balance,
  saving,
  onSave,
}: {
  balance: EmployeeLeaveBalance;
  saving: boolean;
  onSave: (days: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(balance.total_days));

  const handleSave = () => {
    const n = parseFloat(value);
    if (!isNaN(n) && n >= 0) {
      onSave(n);
      setEditing(false);
    }
  };

  return (
    <tr>
      <td>{balance.leave_type_name}</td>
      <td>
        {editing ? (
          <input
            type="number"
            step="0.5"
            min="0"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            style={{ width: 70 }}
            autoFocus
            onKeyDown={(e) => { if (e.key === "Enter") handleSave(); if (e.key === "Escape") setEditing(false); }}
          />
        ) : (
          <span
            style={{ cursor: "pointer", borderBottom: "1px dashed #94a3b8" }}
            onClick={() => { setValue(String(balance.total_days)); setEditing(true); }}
            title="Clic para editar"
          >
            {balance.total_days}
          </span>
        )}
      </td>
      <td>{balance.used_days}</td>
      <td style={{ fontWeight: balance.remaining_days < 0 ? 700 : undefined, color: balance.remaining_days < 0 ? "#dc2626" : undefined }}>
        {balance.remaining_days}
      </td>
      <td>
        {editing ? (
          <button type="button" className="btn btn-xs btn-primary" disabled={saving} onClick={handleSave}>
            {saving ? "…" : "✓"}
          </button>
        ) : null}
      </td>
    </tr>
  );
}
