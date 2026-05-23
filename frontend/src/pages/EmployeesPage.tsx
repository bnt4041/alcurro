import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { Employee, Role, ShiftConfiguration } from "../api/types";
import {
  formatWorkSchedule,
  toTimeInput,
  WORK_DAY_LABELS,
} from "../lib/workSchedule";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import {
  canModule,
  ROLE_LABELS,
  USER_TYPE_OPTIONS,
} from "../lib/permissions";

interface UserGroup {
  id: string;
  name: string;
}

const PANEL_GROUP_NAME = "Empleados con panel";

interface LegalStatusItem {
  document_id: string;
  title: string;
  version: number;
  is_required: boolean;
  accepted: boolean;
  needs_reaccept: boolean;
}

interface EmployeeLegalStatus {
  all_required_accepted: boolean;
  items: LegalStatusItem[];
}

const empty = (): Partial<Employee> & { password?: string } => ({
  phone: "",
  email: "",
  full_name: "",
  id_document: "",
  role: "employee",
  vacation_days_balance: 22,
  is_active: true,
  supervisor_id: null,
  password: "",
  work_days: [0, 1, 2, 3, 4],
  work_start_time: "09:00:00",
  work_end_time: "18:00:00",
  shift_configuration_id: null,
});

export default function EmployeesPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [form, setForm] = useState(empty());
  const [error, setError] = useState("");

  const [groups, setGroups] = useState<UserGroup[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [shiftConfigs, setShiftConfigs] = useState<ShiftConfiguration[]>([]);
  const [legalStatus, setLegalStatus] = useState<EmployeeLegalStatus | null>(null);

  const canWrite = user && canModule(user.permissions, "write", "employees");
  const canAdmin = user && canModule(user.permissions, "admin", "employees");
  const canGroups = user && canModule(user.permissions, "write", "groups");
  const canLegalRead = user && canModule(user.permissions, "read", "legal");

  const panelGroupId = groups.find((g) => g.name === PANEL_GROUP_NAME)?.id;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const path = buildQuery({ q: search || undefined, role: roleFilter || undefined });
      setRows(await api.get<Employee[]>(`/employees${path}`));
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (canGroups) {
      api.get<UserGroup[]>("/groups").then(setGroups).catch(() => {});
    }
  }, [canGroups]);

  useEffect(() => {
    if (open && canWrite) {
      api
        .get<ShiftConfiguration[]>("/shifts/configurations")
        .then(setShiftConfigs)
        .catch(() => setShiftConfigs([]));
    }
  }, [open, canWrite]);

  const toggleWorkDay = (day: number) => {
    const current = form.work_days ?? [];
    const next = current.includes(day)
      ? current.filter((d) => d !== day)
      : [...current, day].sort((a, b) => a - b);
    setForm({ ...form, work_days: next });
  };

  const openCreate = () => {
    setEditing(null);
    setForm(empty());
    setLegalStatus(null);
    setSelectedGroups(panelGroupId ? [panelGroupId] : []);
    setOpen(true);
  };

  const openEdit = async (row: Employee) => {
    setEditing(row);
    setForm({
      ...row,
      password: "",
      work_start_time: row.work_start_time ?? null,
      work_end_time: row.work_end_time ?? null,
      work_days: row.work_days?.length ? row.work_days : [0, 1, 2, 3, 4],
    });
    if (canGroups) {
      const ids = await api.get<string[]>(`/groups/employees/${row.id}/groups`);
      setSelectedGroups(ids);
    } else {
      setSelectedGroups([]);
    }
    if (canLegalRead) {
      api
        .get<EmployeeLegalStatus>(`/legal/employees/${row.id}/status`)
        .then(setLegalStatus)
        .catch(() => setLegalStatus(null));
    } else {
      setLegalStatus(null);
    }
    setOpen(true);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const body: Record<string, unknown> = { ...form };
      if (!body.password) delete body.password;
      if (!editing) {
        delete body.employee_code;
      } else {
        delete body.employee_code;
        delete body.id;
        delete body.created_at;
        delete body.updated_at;
        delete body.company_id;
      }
      let empId = editing?.id;
      if (editing) {
        await api.patch(`/employees/${editing.id}`, body);
      } else {
        const created = await api.post<Employee>("/employees", body);
        empId = created.id;
      }
      if (canGroups && empId) {
        await api.put(`/groups/employees/${empId}/groups`, {
          group_ids: selectedGroups,
        });
      }
      setOpen(false);
      load();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar empleado?")) return;
    await api.delete(`/employees/${id}`);
    load();
  };

  return (
    <>
      <PageHeader
        title="Empleados"
        subtitle="Personal, DNI/NIE y permisos por grupos"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nuevo empleado
            </button>
          ) : undefined
        }
      />
      <TableToolbar
        search={search}
        onSearchChange={setSearch}
        onSubmit={load}
        placeholder="Nombre, código, DNI, teléfono, email…"
        filters={[
          {
            label: "Rol",
            value: roleFilter,
            onChange: setRoleFilter,
            options: USER_TYPE_OPTIONS.map((r) => ({ value: r.value, label: r.label })),
          },
        ]}
      />
      {loading ? (
        <p className="muted">Cargando…</p>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>DNI/NIE</th>
                <th>Nombre</th>
                <th>Teléfono</th>
                <th>Rol</th>
                <th>Horario</th>
                <th>Vacaciones</th>
                <th>Activo</th>
                {canWrite && <th></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td>
                    <code>{e.employee_code}</code>
                  </td>
                  <td>{e.id_document ?? "—"}</td>
                  <td>{e.full_name}</td>
                  <td>{e.phone}</td>
                  <td>
                    <span className="badge">{ROLE_LABELS[e.role]}</span>
                  </td>
                  <td className="muted small">{formatWorkSchedule(e)}</td>
                  <td>{e.vacation_days_balance}</td>
                  <td>{e.is_active ? "Sí" : "No"}</td>
                  {canWrite && (
                    <td className="actions">
                      <button type="button" className="btn btn-sm" onClick={() => openEdit(e)}>
                        Editar
                      </button>
                      {canAdmin && (
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => remove(e.id)}
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
      )}
      <Modal
        title={editing ? "Editar empleado" : "Nuevo empleado"}
        open={open && !!canWrite}
        onClose={() => setOpen(false)}
      >
        <form onSubmit={save} className="form-grid">
          {error && <div className="alert alert-error">{error}</div>}
          {editing && (
            <label>
              Código (automático)
              <input value={editing.employee_code} readOnly disabled />
            </label>
          )}
          {!editing && (
            <p className="muted small form-grid-full">
              El código de empleado se asignará automáticamente (EMP-001, EMP-002…).
            </p>
          )}
          <label>
            DNI/NIE
            <input
              required
              placeholder="12345678Z"
              value={form.id_document ?? ""}
              onChange={(ev) => setForm({ ...form, id_document: ev.target.value.toUpperCase() })}
            />
          </label>
          <label>
            Nombre completo
            <input
              required
              value={form.full_name ?? ""}
              onChange={(ev) => setForm({ ...form, full_name: ev.target.value })}
            />
          </label>
          <label>
            Teléfono (WhatsApp)
            <input
              required
              value={form.phone ?? ""}
              onChange={(ev) => setForm({ ...form, phone: ev.target.value })}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={form.email ?? ""}
              onChange={(ev) => setForm({ ...form, email: ev.target.value })}
            />
          </label>
          <label>
            Rol
            <select
              value={form.role ?? "employee"}
              onChange={(ev) => {
                const role = ev.target.value as Role;
                setForm({ ...form, role });
                if (!editing && role === "employee" && panelGroupId) {
                  setSelectedGroups([panelGroupId]);
                }
              }}
            >
              {USER_TYPE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="form-grid-full">
            <legend>Horario de trabajo</legend>
            <label>
              Hora inicio
              <input
                type="time"
                value={toTimeInput(form.work_start_time ?? undefined)}
                onChange={(ev) =>
                  setForm({
                    ...form,
                    work_start_time: ev.target.value ? `${ev.target.value}:00` : null,
                  })
                }
              />
            </label>
            <label>
              Hora fin
              <input
                type="time"
                value={toTimeInput(form.work_end_time ?? undefined)}
                onChange={(ev) =>
                  setForm({
                    ...form,
                    work_end_time: ev.target.value ? `${ev.target.value}:00` : null,
                  })
                }
              />
            </label>
            <label>
              Turno (opcional)
              <select
                value={form.shift_configuration_id ?? ""}
                onChange={(ev) =>
                  setForm({
                    ...form,
                    shift_configuration_id: ev.target.value || null,
                  })
                }
              >
                <option value="">Sin turno asignado</option>
                {shiftConfigs.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="form-grid-full">
              <span className="label-like">Días laborables</span>
              <div className="day-chips">
                {WORK_DAY_LABELS.map((label, day) => (
                  <label key={day} className="checkbox chip">
                    <input
                      type="checkbox"
                      checked={(form.work_days ?? []).includes(day)}
                      onChange={() => toggleWorkDay(day)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </fieldset>
          {editing && legalStatus && (
            <fieldset className="form-grid-full">
              <legend>Aceptación legal</legend>
              {legalStatus.all_required_accepted ? (
                <p className="muted small">Todos los textos obligatorios están aceptados.</p>
              ) : (
                <p className="alert alert-warning small">
                  Faltan aceptaciones obligatorias.
                </p>
              )}
              <ul className="legal-status-list">
                {legalStatus.items.map((item) => (
                  <li key={item.document_id}>
                    <strong>{item.title}</strong> (v{item.version})
                    {" — "}
                    {item.accepted && !item.needs_reaccept
                      ? "Aceptado"
                      : item.needs_reaccept
                        ? "Debe volver a aceptar"
                        : "Pendiente"}
                  </li>
                ))}
              </ul>
            </fieldset>
          )}
          {canGroups && groups.length > 0 && (
            <fieldset>
              <legend>Grupos de permisos</legend>
              {!editing && (
                <p className="muted small">
                  Por defecto: <strong>{PANEL_GROUP_NAME}</strong>
                </p>
              )}
              {groups.map((g) => (
                <label key={g.id} className="checkbox">
                  <input
                    type="checkbox"
                    checked={selectedGroups.includes(g.id)}
                    onChange={() =>
                      setSelectedGroups((prev) =>
                        prev.includes(g.id)
                          ? prev.filter((id) => id !== g.id)
                          : [...prev, g.id]
                      )
                    }
                  />
                  {g.name}
                </label>
              ))}
            </fieldset>
          )}
          <label>
            Contraseña panel
            <input
              type="password"
              placeholder={editing ? "Dejar vacío = sin cambio" : "Opcional"}
              value={form.password ?? ""}
              onChange={(ev) => setForm({ ...form, password: ev.target.value })}
            />
          </label>
          <label>
            Días vacaciones
            <input
              type="number"
              step="0.5"
              value={form.vacation_days_balance ?? 22}
              onChange={(ev) =>
                setForm({
                  ...form,
                  vacation_days_balance: parseFloat(ev.target.value),
                })
              }
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={(ev) => setForm({ ...form, is_active: ev.target.checked })}
            />
            Activo
          </label>
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => setOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              Guardar
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
