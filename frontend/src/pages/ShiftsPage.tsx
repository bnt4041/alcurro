import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";
import type { ShiftAssignment, ShiftConfiguration, ShiftPatternType } from "../api/types";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useEmployees } from "../hooks/useEmployees";

const PATTERNS: { value: ShiftPatternType; label: string }[] = [
  { value: "rigid", label: "Rígido" },
  { value: "rotating", label: "Rotativo" },
  { value: "split", label: "Partido" },
  { value: "night", label: "Nocturno" },
  { value: "mixed", label: "Mixto" },
];

export default function ShiftsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const canWrite = user && canModule(user.permissions, "write", "shifts");
  const canAdmin = user && canModule(user.permissions, "admin", "shifts");
  const [search, setSearch] = useState("");
  const [patternFilter, setPatternFilter] = useState("");
  const [configs, setConfigs] = useState<ShiftConfiguration[]>([]);
  const [assignments, setAssignments] = useState<ShiftAssignment[]>([]);
  const [tab, setTab] = useState<"config" | "assign">("config");
  const [modal, setModal] = useState<"config" | "assign" | null>(null);
  const [editConfig, setEditConfig] = useState<ShiftConfiguration | null>(null);
  const [editAssign, setEditAssign] = useState<ShiftAssignment | null>(null);
  const [cfgForm, setCfgForm] = useState({
    name: "",
    pattern_type: "rigid" as ShiftPatternType,
    description: "",
    weekly_hours: 40,
    pattern_definition: "{}",
    is_active: true,
  });
  const [assignForm, setAssignForm] = useState({
    employee_id: "",
    shift_configuration_id: "",
    valid_from: "",
    valid_to: "",
    calendar_overrides: "{}",
  });

  const load = useCallback(async () => {
    const q = buildQuery({ q: search || undefined, pattern_type: patternFilter || undefined });
    const [c, a] = await Promise.all([
      api.get<ShiftConfiguration[]>(`/shifts/configurations${q}`),
      api.get<ShiftAssignment[]>("/shifts/assignments"),
    ]);
    setConfigs(c);
    setAssignments(a);
  }, [search, patternFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const saveConfig = async (e: FormEvent) => {
    e.preventDefault();
    const body = {
      ...cfgForm,
      pattern_definition: JSON.parse(cfgForm.pattern_definition || "{}"),
      weekly_hours: cfgForm.weekly_hours || null,
    };
    if (editConfig) {
      await api.patch(`/shifts/configurations/${editConfig.id}`, body);
    } else {
      await api.post("/shifts/configurations", body);
    }
    setModal(null);
    load();
  };

  const saveAssign = async (e: FormEvent) => {
    e.preventDefault();
    const body = {
      ...assignForm,
      valid_to: assignForm.valid_to || null,
      calendar_overrides: JSON.parse(assignForm.calendar_overrides || "{}"),
    };
    if (editAssign) {
      await api.patch(`/shifts/assignments/${editAssign.id}`, body);
    } else {
      await api.post("/shifts/assignments", body);
    }
    setModal(null);
    load();
  };

  const configName = (id: string) =>
    configs.find((c) => c.id === id)?.name ?? id.slice(0, 8);

  return (
    <>
      <PageHeader title="Turnos" subtitle="Configuraciones y asignaciones de calendario" />
      {tab === "config" && (
        <TableToolbar
          search={search}
          onSearchChange={setSearch}
          onSubmit={load}
          placeholder="Nombre o descripción…"
          filters={[
            {
              label: "Tipo",
              value: patternFilter,
              onChange: setPatternFilter,
              options: PATTERNS.map((p) => ({ value: p.value, label: p.label })),
            },
          ]}
        />
      )}
      <div className="tabs">
        <button
          type="button"
          className={tab === "config" ? "tab active" : "tab"}
          onClick={() => setTab("config")}
        >
          Configuraciones
        </button>
        <button
          type="button"
          className={tab === "assign" ? "tab active" : "tab"}
          onClick={() => setTab("assign")}
        >
          Asignaciones
        </button>
      </div>
      {tab === "config" && (
        <>
          <div className="toolbar">
            {canWrite && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                setEditConfig(null);
                setCfgForm({
                  name: "",
                  pattern_type: "rigid",
                  description: "",
                  weekly_hours: 40,
                  pattern_definition: JSON.stringify(
                    { slots: [{ day: 0, start: "08:00", end: "17:00" }] },
                    null,
                    2
                  ),
                  is_active: true,
                });
                setModal("config");
              }}
            >
              + Configuración
            </button>
            )}
          </div>
          <div className="table-wrap card">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Tipo</th>
                  <th>Horas/sem</th>
                  <th>Activo</th>
                  {canWrite && <th></th>}
                </tr>
              </thead>
              <tbody>
                {configs.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.pattern_type}</td>
                    <td>{c.weekly_hours ?? "—"}</td>
                    <td>{c.is_active ? "Sí" : "No"}</td>
                    {canWrite && (
                    <td className="actions">
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => {
                          setEditConfig(c);
                          setCfgForm({
                            name: c.name,
                            pattern_type: c.pattern_type,
                            description: c.description ?? "",
                            weekly_hours: c.weekly_hours ?? 40,
                            pattern_definition: JSON.stringify(
                              c.pattern_definition,
                              null,
                              2
                            ),
                            is_active: c.is_active,
                          });
                          setModal("config");
                        }}
                      >
                        Editar
                      </button>
                      {canAdmin && (
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={async () => {
                          if (confirm("¿Eliminar?")) {
                            await api.delete(`/shifts/configurations/${c.id}`);
                            load();
                          }
                        }}
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
        </>
      )}
      {tab === "assign" && (
        <>
          <div className="toolbar">
            {canWrite && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                setEditAssign(null);
                setAssignForm({
                  employee_id: "",
                  shift_configuration_id: configs[0]?.id ?? "",
                  valid_from: "",
                  valid_to: "",
                  calendar_overrides: "{}",
                });
                setModal("assign");
              }}
            >
              + Asignación
            </button>
            )}
          </div>
          <div className="table-wrap card">
            <table>
              <thead>
                <tr>
                  <th>Empleado</th>
                  <th>Turno</th>
                  <th>Desde</th>
                  <th>Hasta</th>
                  {canAdmin && <th></th>}
                </tr>
              </thead>
              <tbody>
                {assignments.map((a) => (
                  <tr key={a.id}>
                    <td>{byId(a.employee_id)}</td>
                    <td>{configName(a.shift_configuration_id)}</td>
                    <td>{a.valid_from}</td>
                    <td>{a.valid_to ?? "—"}</td>
                    {canAdmin && (
                    <td className="actions">
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={async () => {
                          if (confirm("¿Eliminar?")) {
                            await api.delete(`/shifts/assignments/${a.id}`);
                            load();
                          }
                        }}
                      >
                        Borrar
                      </button>
                    </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <Modal
        title={editConfig ? "Editar turno" : "Nueva configuración"}
        open={modal === "config"}
        onClose={() => setModal(null)}
        wide
      >
        <form onSubmit={saveConfig} className="form-grid">
          <label>
            Nombre
            <input
              required
              value={cfgForm.name}
              onChange={(ev) => setCfgForm({ ...cfgForm, name: ev.target.value })}
            />
          </label>
          <label>
            Tipo
            <select
              value={cfgForm.pattern_type}
              onChange={(ev) =>
                setCfgForm({
                  ...cfgForm,
                  pattern_type: ev.target.value as ShiftPatternType,
                })
              }
            >
              {PATTERNS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Horas semanales
            <input
              type="number"
              value={cfgForm.weekly_hours}
              onChange={(ev) =>
                setCfgForm({ ...cfgForm, weekly_hours: parseFloat(ev.target.value) })
              }
            />
          </label>
          <label className="full">
            Descripción
            <input
              value={cfgForm.description}
              onChange={(ev) =>
                setCfgForm({ ...cfgForm, description: ev.target.value })
              }
            />
          </label>
          <label className="full">
            pattern_definition (JSON)
            <textarea
              rows={8}
              value={cfgForm.pattern_definition}
              onChange={(ev) =>
                setCfgForm({ ...cfgForm, pattern_definition: ev.target.value })
              }
            />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Guardar
            </button>
          </div>
        </form>
      </Modal>
      <Modal
        title="Nueva asignación"
        open={modal === "assign"}
        onClose={() => setModal(null)}
      >
        <form onSubmit={saveAssign} className="form-grid">
          <label>
            Empleado
            <select
              required
              value={assignForm.employee_id}
              onChange={(ev) =>
                setAssignForm({ ...assignForm, employee_id: ev.target.value })
              }
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
            Configuración
            <select
              required
              value={assignForm.shift_configuration_id}
              onChange={(ev) =>
                setAssignForm({
                  ...assignForm,
                  shift_configuration_id: ev.target.value,
                })
              }
            >
              {configs.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Válido desde
            <input
              type="date"
              required
              value={assignForm.valid_from}
              onChange={(ev) =>
                setAssignForm({ ...assignForm, valid_from: ev.target.value })
              }
            />
          </label>
          <label>
            Válido hasta
            <input
              type="date"
              value={assignForm.valid_to}
              onChange={(ev) =>
                setAssignForm({ ...assignForm, valid_to: ev.target.value })
              }
            />
          </label>
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
