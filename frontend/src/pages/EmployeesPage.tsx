import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type {
  Employee,
  EmployeeBulkScheduleResult,
  Role,
  ShiftConfiguration,
  WorkSchedulePeriod,
} from "../api/types";
import {
  defaultSchedulePeriods,
  formatWorkSchedule,
  periodsFromEmployee,
  validatePeriodsClient,
} from "../lib/workSchedule";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import { tableActionButtons } from "../lib/tableFormatters";
import EmployeeProfileTabs from "../components/EmployeeProfileTabs";
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

const EMPLOYEE_IMPORT_COLUMNS = [
  { key: "full_name", header: "Nombre completo", example: "Ana García López" },
  { key: "id_document", header: "DNI/NIE", example: "12345678Z" },
  { key: "phone", header: "Teléfono (WhatsApp)", example: "612345678" },
  { key: "email", header: "Email", example: "ana@empresa.com" },
  { key: "role", header: "Rol", example: "employee" },
  { key: "vacation_days_balance", header: "Días vacaciones", example: "22" },
  { key: "is_active", header: "Activo (si/no)", example: "si" },
];

type EmployeeTableRow = Employee & {
  role_label: string;
  schedule_label: string;
  active_label: string;
};

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

type EmployeeForm = Omit<
  Partial<Employee>,
  "company_id" | "department_id" | "work_center_id" | "shift_configuration_id" | "supervisor_id"
> & {
  password?: string;
  company_id?: string | null;
  department_id?: string | null;
  work_center_id?: string | null;
  shift_configuration_id?: string | null;
  supervisor_id?: string | null;
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
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkSaving, setBulkSaving] = useState(false);
  const [bulkMsg, setBulkMsg] = useState("");
  const [bulkRotating, setBulkRotating] = useState(false);
  const [bulkShiftId, setBulkShiftId] = useState<string | null>(null);
  const [bulkWeeklyHours, setBulkWeeklyHours] = useState<number | null>(40);
  const [bulkPeriods, setBulkPeriods] = useState<WorkSchedulePeriod[]>(
    defaultSchedulePeriods()
  );

  const canWrite = user && canModule(user.permissions, "write", "employees");
  const canUpdate =
    user &&
    (canModule(user.permissions, "write", "employees") ||
      canModule(user.permissions, "update", "employees"));
  const canAdmin = user && canModule(user.permissions, "admin", "employees");
  const canGroups = user && canModule(user.permissions, "write", "groups");
  const canLegalRead = user && canModule(user.permissions, "read", "legal");
  const canDocumentsRead =
    user && canModule(user.permissions, "read", "documents");
  const canSignaturesRead =
    user && canModule(user.permissions, "read", "signatures");
  const [empTab, setEmpTab] = useState<"data" | "documents" | "signatures">("data");

  const panelGroupId = groups.find((g) => g.name === PANEL_GROUP_NAME)?.id;

  const tableData = useMemo<EmployeeTableRow[]>(
    () =>
      rows.map((e) => ({
        ...e,
        role_label: ROLE_LABELS[e.role] ?? e.role,
        schedule_label: formatWorkSchedule(e),
        active_label: e.is_active ? "Sí" : "No",
      })),
    [rows]
  );

  const employeeColumns = useMemo<DataTableColumn<EmployeeTableRow>[]>(() => {
    const cols: DataTableColumn<EmployeeTableRow>[] = [
      {
        title: "Código",
        field: "employee_code",
        headerFilter: "input",
        width: 100,
        formatter: (c) => `<code>${c.getValue()}</code>`,
      },
      {
        title: "DNI/NIE",
        field: "id_document",
        headerFilter: "input",
        minWidth: 110,
        formatter: (c) => String(c.getValue() ?? "—"),
      },
      { title: "Nombre", field: "full_name", headerFilter: "input", minWidth: 160 },
      { title: "Teléfono", field: "phone", headerFilter: "input", width: 120 },
      {
        title: "Rol",
        field: "role_label",
        headerFilter: "select",
        headerFilterParams: {
          values: Object.fromEntries(
            USER_TYPE_OPTIONS.map((r) => [r.label, r.label])
          ),
        },
        width: 130,
      },
      {
        title: "Horario",
        field: "schedule_label",
        headerFilter: "input",
        minWidth: 140,
      },
      {
        title: "Vacaciones",
        field: "vacation_days_balance",
        headerFilter: "number",
        width: 100,
      },
      {
        title: "Activo",
        field: "active_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", Sí: "Sí", No: "No" } },
        width: 90,
      },
    ];
    if (canWrite) {
      cols.push({
        title: "",
        field: "id",
        headerFilter: false,
        sorter: false,
        download: false,
        width: 150,
        formatter: () =>
          tableActionButtons([
            { id: "edit", label: "Editar" },
            ...(canAdmin ? [{ id: "delete", label: "Borrar", className: "btn-danger" }] : []),
          ]),
      });
    }
    return cols;
  }, [canWrite, canAdmin]);

  const handleCellAction = (action: string, row: EmployeeTableRow) => {
    if (action === "edit") openEdit(row);
    else if (action === "delete") remove(row.id);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Employee[]>(`/employees?limit=3000`));
    } finally {
      setLoading(false);
    }
  }, []);

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
    if (canUpdate && user?.company_id) {
      api
        .get<ShiftConfiguration[]>(
          `/shifts/configurations?company_id=${encodeURIComponent(user.company_id)}`
        )
        .then(setShiftConfigs)
        .catch(() => setShiftConfigs([]));
    }
  }, [canUpdate, user?.company_id]);

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
    setEmpTab("data");
    setOpen(true);
  };

  const openEdit = async (row: Employee) => {
    setEditing(row);
    setEmpTab("data");
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

  const openBulkSchedule = () => {
    if (selected.size === 0) return;
    setBulkMsg("");
    setBulkRotating(false);
    setBulkShiftId(null);
    setBulkWeeklyHours(40);
    setBulkPeriods(defaultSchedulePeriods());
    setBulkOpen(true);
  };

  const applyBulkSchedule = async (e: FormEvent) => {
    e.preventDefault();
    setBulkMsg("");
    if (selected.size === 0) {
      setBulkMsg("Selecciona al menos un empleado");
      return;
    }
    if (bulkRotating) {
      if (!bulkShiftId) {
        setBulkMsg("Selecciona un turno complejo");
        return;
      }
      if (!bulkWeeklyHours || bulkWeeklyHours <= 0 || bulkWeeklyHours > 168) {
        setBulkMsg("Indica horas semanales válidas (0–168)");
        return;
      }
    } else {
      const err = validatePeriodsClient(bulkPeriods);
      if (err) {
        setBulkMsg(err);
        return;
      }
    }
    try {
      setBulkSaving(true);
      const res = await api.post<EmployeeBulkScheduleResult>(
        "/employees/bulk-schedule",
        {
          employee_ids: [...selected],
          rotating_shift: bulkRotating,
          shift_configuration_id: bulkRotating ? bulkShiftId : null,
          weekly_hours: bulkRotating ? bulkWeeklyHours : null,
          work_schedule_periods: bulkRotating ? [] : bulkPeriods,
        }
      );
      const errText =
        res.errors.length > 0
          ? ` · ${res.errors.length} error(es): ${res.errors
              .slice(0, 3)
              .map((x) => x.employee_name ?? x.employee_id)
              .join(", ")}${res.errors.length > 3 ? "…" : ""}`
          : "";
      setBulkMsg(
        `Horario actualizado en ${res.updated} empleado(s)${res.skipped ? `, ${res.skipped} omitidos` : ""}${errText}`
      );
      if (res.updated > 0) {
        setSelected(new Set());
        load();
      }
      if (res.errors.length === 0) setBulkOpen(false);
    } catch (err) {
      setBulkMsg(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setBulkSaving(false);
    }
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
      {canUpdate && selected.size > 0 && (
        <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={openBulkSchedule}
          >
            Cambio masivo de horario ({selected.size})
          </button>
        </div>
      )}
      <DataTable
        data={tableData}
        columns={employeeColumns}
        loading={loading}
        exportFilename="empleados"
        height="520px"
        selectable={!!canUpdate}
        onRowSelectionChange={(ids) => setSelected(new Set(ids))}
        onCellAction={handleCellAction}
        importConfig={
          canWrite
            ? {
                templateFilename: "plantilla_empleados",
                columns: EMPLOYEE_IMPORT_COLUMNS,
                hint: "Usa el departamento seleccionado en la barra superior",
                onImport: async (mapped) => {
                  const res = await api.post<{ created: number; errors: string[] }>(
                    "/employees/bulk-import",
                    {
                      rows: mapped.map((r) => ({
                        full_name: r.full_name,
                        id_document: r.id_document,
                        phone: r.phone,
                        email: r.email || null,
                        role: r.role || "employee",
                        vacation_days_balance: r.vacation_days_balance,
                        is_active: r.is_active,
                      })),
                    }
                  );
                  return { created: res.created, errors: res.errors };
                },
              }
            : undefined
        }
        onImportComplete={load}
      />
      <Modal
        title={`Cambio masivo de horario (${selected.size} empleado${selected.size === 1 ? "" : "s"})`}
        open={bulkOpen && !!canUpdate}
        onClose={() => setBulkOpen(false)}
        xlarge
        tall
      >
        <form onSubmit={applyBulkSchedule} className="form-grid modal-form-scroll">
          {bulkMsg && (
            <div
              className={`alert form-grid-full ${
                bulkMsg.includes("actualizado") ? "alert-ok" : "alert-error"
              }`}
            >
              {bulkMsg}
            </div>
          )}
          <p className="muted small form-grid-full">
            Se aplicará el mismo horario a los empleados seleccionados en la tabla
            (respeta filtros de búsqueda y rol).
          </p>
          <div className="form-grid-full schedule-mode">
            <label className="checkbox schedule-mode__toggle">
              <input
                type="checkbox"
                checked={bulkRotating}
                onChange={(ev) => setBulkRotating(ev.target.checked)}
              />
              <strong>Turno rotativo (complejo)</strong>
            </label>
            {bulkRotating ? (
              <div className="card-inner rotating-shift-panel">
                <label className="full">
                  Turno complejo
                  <select
                    required
                    value={bulkShiftId ?? ""}
                    onChange={(ev) => {
                      const id = ev.target.value || null;
                      const cfg = shiftConfigs.find((s) => s.id === id);
                      setBulkShiftId(id);
                      if (cfg?.weekly_hours != null) {
                        setBulkWeeklyHours(cfg.weekly_hours);
                      }
                    }}
                  >
                    <option value="">Seleccionar…</option>
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
                    value={bulkWeeklyHours ?? ""}
                    onChange={(ev) =>
                      setBulkWeeklyHours(
                        ev.target.value ? parseFloat(ev.target.value) : null
                      )
                    }
                  />
                </label>
              </div>
            ) : (
              <WorkScheduleEditor periods={bulkPeriods} onChange={setBulkPeriods} />
            )}
          </div>
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setBulkOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={bulkSaving}>
              {bulkSaving ? "Aplicando…" : "Aplicar horario"}
            </button>
          </div>
        </form>
      </Modal>
      <Modal
        title={editing ? "Editar empleado" : "Nuevo empleado"}
        open={open && !!canWrite}
        onClose={() => setOpen(false)}
        xlarge
        tall
      >
        {editing && (canDocumentsRead || canSignaturesRead) ? (
          <EmployeeProfileTabs
            employeeId={editing.id}
            employeeName={editing.full_name}
            activeTab={empTab}
            onTabChange={setEmpTab}
            showDocuments={!!canDocumentsRead}
            showSignatures={!!canSignaturesRead}
          >
            <form
              onSubmit={save}
              className="form-grid employee-modal-form modal-form-scroll"
            >
              {error && <div className="alert alert-error form-grid-full">{error}</div>}
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
          </EmployeeProfileTabs>
        ) : (
          <form
            onSubmit={save}
            className="form-grid employee-modal-form modal-form-scroll"
          >
            {error && <div className="alert alert-error form-grid-full">{error}</div>}
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
        )}
      </Modal>
    </>
  );
}
