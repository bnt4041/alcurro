import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { Employee, Role } from "../api/types";
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

const empty = (): Partial<Employee> & { password?: string } => ({
  phone: "",
  email: "",
  full_name: "",
  employee_code: "",
  role: "employee",
  vacation_days_balance: 22,
  is_active: true,
  supervisor_id: null,
  password: "",
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

  const canWrite = user && canModule(user.permissions, "write", "employees");
  const canAdmin = user && canModule(user.permissions, "admin", "employees");
  const canGroups = user && canModule(user.permissions, "write", "groups");

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

  const openCreate = () => {
    setEditing(null);
    setForm(empty());
    setSelectedGroups([]);
    setOpen(true);
  };

  const openEdit = async (row: Employee) => {
    setEditing(row);
    setForm({ ...row, password: "" });
    if (canGroups) {
      const ids = await api.get<string[]>(`/groups/employees/${row.id}/groups`);
      setSelectedGroups(ids);
    } else {
      setSelectedGroups([]);
    }
    setOpen(true);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const body = { ...form };
      if (!body.password) delete body.password;
      let empId = editing?.id;
      if (editing) {
        await api.patch(`/employees/${editing.id}`, body);
      } else {
        const created = await api.post<Employee>("/employees", body);
        empId = created.id;
      }
      if (canGroups && empId && selectedGroups.length) {
        await api.put(`/groups/employees/${empId}/groups`, {
          group_ids: selectedGroups,
        });
      }
      setOpen(false);
      load();
    } catch (err) {
      setError(String(err));
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
        subtitle="CRUD de personal y roles RBAC"
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
        placeholder="Nombre, código, teléfono, email…"
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
                <th>Nombre</th>
                <th>Teléfono</th>
                <th>Rol</th>
                <th>Vacaciones</th>
                <th>Activo</th>
                {canWrite && <th></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td>{e.employee_code}</td>
                  <td>{e.full_name}</td>
                  <td>{e.phone}</td>
                  <td>
                    <span className="badge">{ROLE_LABELS[e.role]}</span>
                  </td>
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
          <label>
            Código
            <input
              required
              value={form.employee_code ?? ""}
              onChange={(ev) => setForm({ ...form, employee_code: ev.target.value })}
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
              onChange={(ev) => setForm({ ...form, role: ev.target.value as Role })}
            >
              {USER_TYPE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          {canGroups && groups.length > 0 && (
            <fieldset>
              <legend>Grupos de permisos</legend>
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
