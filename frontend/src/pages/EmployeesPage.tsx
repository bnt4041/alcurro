import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { Employee, Role, ShiftConfiguration, WorkSchedulePeriod } from "../api/types";
import {
  defaultSchedulePeriods,
  formatWorkSchedule,
  periodsFromEmployee,
  validatePeriodsClient,
} from "../lib/workSchedule";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import WorkScheduleEditor from "../components/WorkScheduleEditor";
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

interface OrgDepartment {
  id: string;
  name: string;
  code: string;
}

interface OrgWorkCenter {
  id: string;
  name: string;
  code: string;
  departments: OrgDepartment[];
}

interface OrgTreeCompany {
  id: string;
  name: string;
  work_centers: OrgWorkCenter[];
}

type EmployeeForm = Partial<Employee> & {
  password?: string;
  company_id?: string | null;
  work_center_id?: string | null;
};

const empty = (defaults?: {
  company_id?: string | null;
  department_id?: string | null;
  work_center_id?: string | null;
}): EmployeeForm => ({
  phone: "",
  email: "",
  full_name: "",
  id_document: "",
  role: "employee",
  vacation_days_balance: 22,
  is_active: true,
  supervisor_id: null,
  password: "",
  company_id: defaults?.company_id ?? null,
  department_id: defaults?.department_id ?? null,
  work_center_id: defaults?.work_center_id ?? null,
  shift_configuration_id: null,
  rotating_shift: false,
  weekly_hours: null,
  work_schedule_periods: defaultSchedulePeriods(),
});

export default function EmployeesPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [form, setForm] = useState<EmployeeForm>(empty());
  const [schedulePeriods, setSchedulePeriods] = useState<WorkSchedulePeriod[]>(
    defaultSchedulePeriods()
  );
  const [orgTree, setOrgTree] = useState<OrgTreeCompany[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

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
    if (canWrite) {
      api
        .get<OrgTreeCompany[]>("/org/tree")
        .then(setOrgTree)
        .catch(() => setOrgTree([]));
    }
  }, [canWrite]);

  useEffect(() => {
    if (open && canWrite && !orgTree.length) {
      api
        .get<OrgTreeCompany[]>("/org/tree")
        .then(setOrgTree)
        .catch(() => setOrgTree([]));
    }
  }, [open, canWrite, orgTree.length]);

  useEffect(() => {
    if (!open || !canWrite || !form.company_id) {
      setShiftConfigs([]);
      return;
    }
    api
      .get<ShiftConfiguration[]>(
        `/shifts/configurations?company_id=${encodeURIComponent(form.company_id)}`
      )
      .then(setShiftConfigs)
      .catch(() => setShiftConfigs([]));
  }, [open, canWrite, form.company_id]);

  const selectedCompany = useMemo(
    () => orgTree.find((c) => c.id === form.company_id) ?? orgTree[0],
    [orgTree, form.company_id]
  );
  const workCenters = selectedCompany?.work_centers ?? [];
  const departments = useMemo(() => {
    const wc = workCenters.find((w) => w.id === form.work_center_id);
    return wc?.departments ?? [];
  }, [workCenters, form.work_center_id]);

  const resolveWorkCenterForDepartment = (departmentId: string | null | undefined) => {
    if (!departmentId || !selectedCompany) return null;
    for (const wc of selectedCompany.work_centers) {
      if (wc.departments.some((d) => d.id === departmentId)) return wc.id;
    }
    return null;
  };

  const openCreate = () => {
    setEditing(null);
    const companyId = user?.company_id ?? orgTree[0]?.id ?? null;
    const comp = orgTree.find((c) => c.id === companyId) ?? orgTree[0];
    const deptId = user?.department_id ?? comp?.work_centers[0]?.departments[0]?.id ?? null;
    const wcId =
      user?.work_center_id ??
      resolveWorkCenterForDepartment(deptId) ??
      comp?.work_centers[0]?.id ??
      null;
    setForm(empty({ company_id: companyId, department_id: deptId, work_center_id: wcId }));
    setSchedulePeriods(defaultSchedulePeriods());
    setLegalStatus(null);
    setSelectedGroups(panelGroupId ? [panelGroupId] : []);
    setOpen(true);
  };

  const openEdit = async (row: Employee) => {
    setEditing(row);
    setSchedulePeriods(
      row.rotating_shift ? [] : periodsFromEmployee(row)
    );
    let tree = orgTree;
    if (!tree.length) {
      try {
        tree = await api.get<OrgTreeCompany[]>("/org/tree");
        setOrgTree(tree);
      } catch {
        tree = [];
      }
    }
    const comp = tree.find((c) => c.id === row.company_id) ?? tree[0];
    let wcId: string | null = null;
    if (row.department_id && comp) {
      for (const wc of comp.work_centers) {
        if (wc.departments.some((d) => d.id === row.department_id)) {
          wcId = wc.id;
          break;
        }
      }
    }
    setForm({
      ...row,
      password: "",
      company_id: row.company_id,
      work_center_id: wcId,
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
    if (!form.company_id) {
      setError("Selecciona la empresa");
      return;
    }
    if (!form.department_id) {
      setError("Selecciona centro y departamento");
      return;
    }
    if (form.rotating_shift) {
      if (!form.shift_configuration_id) {
        setError("Selecciona un turno complejo (o desmarca turno rotativo)");
        return;
      }
      if (
        form.weekly_hours == null ||
        form.weekly_hours <= 0 ||
        form.weekly_hours > 168
      ) {
        setError("Indica las horas semanales (entre 0 y 168)");
        return;
      }
    } else {
      const scheduleErr = validatePeriodsClient(schedulePeriods);
      if (scheduleErr) {
        setError(scheduleErr);
        return;
      }
    }
    try {
      setSaving(true);
      const body: Record<string, unknown> = {
        phone: form.phone,
        email: form.email,
        full_name: form.full_name,
        id_document: form.id_document,
        role: form.role,
        vacation_days_balance: form.vacation_days_balance,
        is_active: form.is_active,
        supervisor_id: form.supervisor_id,
        department_id: form.department_id,
        rotating_shift: form.rotating_shift ?? false,
        shift_configuration_id: form.shift_configuration_id,
        weekly_hours: form.rotating_shift ? form.weekly_hours : null,
        work_schedule_periods: form.rotating_shift ? [] : schedulePeriods,
      };
      if (form.password) body.password = form.password;
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
          group_ids: [...new Set(selectedGroups)],
        });
      }
      setOpen(false);
      load();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
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
        xlarge
        tall
      >
        <form onSubmit={save} className="form-grid employee-modal-form modal-form-scroll">
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
          <label className="form-grid-full">
            Empresa
            <select
              required
              value={form.company_id ?? ""}
              onChange={(ev) => {
                const company_id = ev.target.value || null;
                const comp = orgTree.find((c) => c.id === company_id);
                const firstWc = comp?.work_centers[0];
                setForm({
                  ...form,
                  company_id,
                  work_center_id: firstWc?.id ?? null,
                  department_id: firstWc?.departments[0]?.id ?? null,
                  shift_configuration_id: null,
                });
              }}
            >
              <option value="">Seleccionar empresa…</option>
              {orgTree.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Centro de trabajo
            <select
              required
              value={form.work_center_id ?? ""}
              onChange={(ev) => {
                const work_center_id = ev.target.value || null;
                const wc = workCenters.find((w) => w.id === work_center_id);
                setForm({
                  ...form,
                  work_center_id,
                  department_id: wc?.departments[0]?.id ?? null,
                });
              }}
              disabled={!form.company_id}
            >
              <option value="">Seleccionar centro…</option>
              {workCenters.map((wc) => (
                <option key={wc.id} value={wc.id}>
                  {wc.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Departamento
            <select
              required
              value={form.department_id ?? ""}
              onChange={(ev) =>
                setForm({ ...form, department_id: ev.target.value || null })
              }
              disabled={!form.work_center_id}
            >
              <option value="">Seleccionar departamento…</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <div className="form-grid-full schedule-mode">
            <label className="checkbox schedule-mode__toggle">
              <input
                type="checkbox"
                checked={form.rotating_shift ?? false}
                onChange={(ev) =>
                  setForm({
                    ...form,
                    rotating_shift: ev.target.checked,
                    shift_configuration_id: ev.target.checked
                      ? form.shift_configuration_id
                      : null,
                    weekly_hours: ev.target.checked ? form.weekly_hours : null,
                  })
                }
              />
              <strong>Turno rotativo</strong>
              <span className="muted small">
                El horario se define en Turnos complejos; no uses franjas aquí.
              </span>
            </label>
            {form.rotating_shift ? (
              <div className="card-inner rotating-shift-panel">
                <label className="full">
                  Turno complejo asignado
                  <select
                    required
                    value={form.shift_configuration_id ?? ""}
                    onChange={(ev) => {
                      const id = ev.target.value || null;
                      const cfg = shiftConfigs.find((s) => s.id === id);
                      setForm({
                        ...form,
                        shift_configuration_id: id,
                        weekly_hours:
                          form.weekly_hours ??
                          cfg?.weekly_hours ??
                          null,
                      });
                    }}
                  >
                    <option value="">Seleccionar turno…</option>
                    {shiftConfigs.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                        {s.weekly_hours != null ? ` (${s.weekly_hours} h/sem)` : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Horas semanales
                  <input
                    type="number"
                    required
                    min={0.5}
                    max={168}
                    step={0.5}
                    value={form.weekly_hours ?? ""}
                    onChange={(ev) =>
                      setForm({
                        ...form,
                        weekly_hours: ev.target.value
                          ? parseFloat(ev.target.value)
                          : null,
                      })
                    }
                    placeholder="Ej. 40"
                  />
                  <span className="muted small">
                    Jornada semanal pactada para este empleado con turno complejo.
                  </span>
                </label>
                {shiftConfigs.length === 0 && (
                  <p className="muted small">
                    No hay turnos configurados. Crea uno en{" "}
                    <a href="/app/turnos">Turnos</a>.
                  </p>
                )}
              </div>
            ) : (
              <WorkScheduleEditor
                periods={schedulePeriods}
                onChange={setSchedulePeriods}
              />
            )}
          </div>
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
            <fieldset className="form-grid-full">
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
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
