import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, buildQuery } from "../api/client";
import type { ClockIn, Incident, LeaveRequest } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

type IncidentCategory = "fichaje" | "vacaciones" | "permiso";

const emptyCreateForm = () => ({
  employee_id: "",
  category: "fichaje" as IncidentCategory,
  title: "",
  description: "",
  clock_in_id: "",
  leave_request_id: "",
  require_justification: false,
  notify_whatsapp: false,
});

const STATUS_LABELS: Record<string, string> = {
  pending_justification: "Pendiente justificación",
  open: "Abierta",
  resolved: "Resuelta",
  dismissed: "Descartada",
};

type IncidentRow = Incident & {
  status_label: string;
  category_label: string;
};

export default function IncidentsPage() {
  const { user } = useAuth();
  const { employees } = useEmployees();
  const canRead = user && canModule(user.permissions, "read", "clock_ins");
  const canWrite = user && canModule(user.permissions, "write", "clock_ins");
  const [rows, setRows] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [linkClocks, setLinkClocks] = useState<ClockIn[]>([]);
  const [linkLeaves, setLinkLeaves] = useState<LeaveRequest[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [msg, setMsg] = useState("");
  const [clockForm, setClockForm] = useState({
    recorded_at: "",
    notes: "",
  });

  const load = useCallback(async () => {
    if (!canRead) return;
    setLoading(true);
    try {
      setRows(await api.get<Incident[]>("/incidents"));
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!createOpen || !createForm.employee_id) {
      setLinkClocks([]);
      setLinkLeaves([]);
      return;
    }
    const emp = createForm.employee_id;
    if (createForm.category === "fichaje") {
      api
        .get<ClockIn[]>(`/clock-ins${buildQuery({ employee_id: emp, limit: "100" })}`)
        .then(setLinkClocks)
        .catch(() => setLinkClocks([]));
      setLinkLeaves([]);
    } else {
      api
        .get<LeaveRequest[]>(`/leave-requests${buildQuery({ employee_id: emp })}`)
        .then(setLinkLeaves)
        .catch(() => setLinkLeaves([]));
      setLinkClocks([]);
    }
  }, [createOpen, createForm.employee_id, createForm.category]);

  const openCreate = () => {
    setCreateForm(emptyCreateForm());
    setCreateOpen(true);
    setMsg("");
  };

  const saveCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!canWrite) return;
    try {
      await api.post("/incidents", {
        employee_id: createForm.employee_id,
        category: createForm.category,
        incident_type: "manual",
        title: createForm.title.trim(),
        description: createForm.description.trim() || null,
        clock_in_id:
          createForm.category === "fichaje" && createForm.clock_in_id
            ? createForm.clock_in_id
            : null,
        leave_request_id:
          createForm.category !== "fichaje" && createForm.leave_request_id
            ? createForm.leave_request_id
            : null,
        require_justification: createForm.require_justification,
        notify_whatsapp: createForm.notify_whatsapp,
      });
      setCreateOpen(false);
      setMsg("Incidencia creada");
      load();
    } catch (err) {
      setMsg(String(err));
    }
  };

  const tableData = useMemo<IncidentRow[]>(
    () =>
      rows.map((r) => ({
        ...r,
        status_label: STATUS_LABELS[r.status] ?? r.status,
        category_label:
          r.category === "fichaje"
            ? "Fichaje"
            : r.category === "vacaciones"
              ? "Vacaciones"
              : "Permiso",
      })),
    [rows]
  );

  const columns = useMemo<DataTableColumn<IncidentRow>[]>(
    () => [
      {
        title: "Fecha",
        field: "created_at",
        sorter: "datetime",
        formatter: (c) => new Date(String(c.getValue())).toLocaleString("es-ES"),
        minWidth: 150,
      },
      {
        title: "Empleado",
        field: "employee_name",
        headerFilter: "input",
        minWidth: 160,
      },
      { title: "Título", field: "title", headerFilter: "input", minWidth: 180 },
      {
        title: "Tipo",
        field: "category_label",
        headerFilter: "input",
        width: 110,
      },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "input",
        width: 160,
      },
      {
        title: "",
        field: "id",
        headerFilter: false,
        download: false,
        width: 100,
        formatter: () =>
          `<button type="button" class="btn btn-sm" data-action="view">Ver</button>`,
      },
    ],
    []
  );

  const openDetail = (row: IncidentRow) => {
    setSelected(row);
    const orig = (row.original_data?.entrada_at ?? row.original_data?.recorded_at) as string | undefined;
    setClockForm({
      recorded_at: orig
        ? new Date(orig).toISOString().slice(0, 16)
        : new Date().toISOString().slice(0, 16),
      notes: String(row.original_data?.notes ?? ""),
    });
    setMsg("");
  };

  const applyClock = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !canWrite) return;
    try {
      await api.post(`/incidents/${selected.id}/apply-clock`, {
        recorded_at: new Date(clockForm.recorded_at).toISOString(),
        notes: clockForm.notes || null,
      });
      setMsg("Fichaje corregido y incidencia resuelta");
      setSelected(null);
      load();
    } catch (err) {
      setMsg(String(err));
    }
  };

  const renderDataDiff = (
    label: string,
    original: Record<string, unknown>,
    modified: Record<string, unknown> | null
  ) => (
    <div className="incident-diff">
      <h4>{label}</h4>
      <div className="incident-diff-grid">
        <div>
          <strong>Original</strong>
          <pre className="incident-diff-pre">
            {JSON.stringify(original, null, 2)}
          </pre>
        </div>
        {modified && (
          <div>
            <strong>Modificado</strong>
            <pre className="incident-diff-pre">
              {JSON.stringify(modified, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );

  if (!canRead) {
    return (
      <p className="muted">No tienes permiso para ver incidencias.</p>
    );
  }

  return (
    <>
      <PageHeader
        title="Incidencias"
        subtitle="Fichajes, vacaciones y permisos — correcciones con registro original y modificado"
        action={
          canWrite ? (
            <div className="header-actions">
              <Link to="/app/fichajes/configuracion" className="btn">
                Reglas automáticas
              </Link>
              <button type="button" className="btn btn-primary" onClick={openCreate}>
                + Nueva incidencia
              </button>
            </div>
          ) : undefined
        }
      />
      {msg && (
        <div
          className={`alert ${
            msg.includes("corregido") ||
              msg.includes("guardad") ||
              msg.includes("creada")
              ? "alert-ok"
              : "alert-error"
          }`}
        >
          {msg}
        </div>
      )}
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="incidencias"
        height="520px"
        onCellAction={(action, row) => {
          if (action === "view") openDetail(row);
        }}
      />

      <Modal
        title="Nueva incidencia manual"
        open={createOpen && !!canWrite}
        onClose={() => setCreateOpen(false)}
      >
        <form onSubmit={saveCreate} className="form-grid">
          <label>
            Empleado
            <select
              required
              value={createForm.employee_id}
              onChange={(ev) =>
                setCreateForm({
                  ...createForm,
                  employee_id: ev.target.value,
                  clock_in_id: "",
                  leave_request_id: "",
                })
              }
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
            Categoría
            <select
              value={createForm.category}
              onChange={(ev) =>
                setCreateForm({
                  ...createForm,
                  category: ev.target.value as IncidentCategory,
                  clock_in_id: "",
                  leave_request_id: "",
                })
              }
            >
              <option value="fichaje">Fichaje</option>
              <option value="vacaciones">Vacaciones</option>
              <option value="permiso">Permiso</option>
            </select>
          </label>
          <label className="form-grid-full">
            Título
            <input
              required
              maxLength={300}
              value={createForm.title}
              onChange={(ev) => setCreateForm({ ...createForm, title: ev.target.value })}
            />
          </label>
          <label className="form-grid-full">
            Descripción (opcional)
            <textarea
              rows={3}
              maxLength={2000}
              value={createForm.description}
              onChange={(ev) =>
                setCreateForm({ ...createForm, description: ev.target.value })
              }
            />
          </label>
          {createForm.category === "fichaje" && createForm.employee_id && (
            <label className="form-grid-full">
              Vincular a fichaje (opcional)
              <select
                value={createForm.clock_in_id}
                onChange={(ev) =>
                  setCreateForm({ ...createForm, clock_in_id: ev.target.value })
                }
              >
                <option value="">Sin vincular</option>
                {linkClocks.map((c) => (
                  <option key={c.id} value={c.id}>
                    {new Date(c.entrada_at).toLocaleString("es-ES")}{c.salida_at ? ` → ${new Date(c.salida_at).toLocaleString("es-ES")}` : " (abierta)"}
                    {c.notes ? ` (${c.notes})` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          {createForm.category !== "fichaje" && createForm.employee_id && (
            <label className="form-grid-full">
              Vincular a solicitud (opcional)
              <select
                value={createForm.leave_request_id}
                onChange={(ev) =>
                  setCreateForm({ ...createForm, leave_request_id: ev.target.value })
                }
              >
                <option value="">Sin vincular</option>
                {linkLeaves.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.start_date} → {l.end_date} ({l.status})
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="checkbox form-grid-full">
            <input
              type="checkbox"
              checked={createForm.require_justification}
              onChange={(ev) =>
                setCreateForm({
                  ...createForm,
                  require_justification: ev.target.checked,
                  notify_whatsapp: ev.target.checked ? createForm.notify_whatsapp : false,
                })
              }
            />
            <span>Requerir justificación del empleado (enlace público)</span>
          </label>
          {createForm.require_justification && (
            <label className="checkbox form-grid-full">
              <input
                type="checkbox"
                checked={createForm.notify_whatsapp}
                onChange={(ev) =>
                  setCreateForm({ ...createForm, notify_whatsapp: ev.target.checked })
                }
              />
              <span>Notificar por WhatsApp con el enlace</span>
            </label>
          )}
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setCreateOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              Crear incidencia
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        title={selected?.title ?? "Incidencia"}
        open={!!selected}
        onClose={() => setSelected(null)}
        wide
      >
        {selected && (
          <div className="incident-detail">
            <p>
              <strong>{selected.employee_name}</strong> ·{" "}
              {STATUS_LABELS[selected.status] ?? selected.status}
            </p>
            {selected.description && <p>{selected.description}</p>}
            {selected.employee_justification && (
              <div className="alert alert-info">
                <strong>Justificación empleado:</strong>{" "}
                {selected.employee_justification}
              </div>
            )}
            {selected.justify_url && (
              <p className="muted small">
                Enlace justificación:{" "}
                <a href={selected.justify_url} target="_blank" rel="noreferrer">
                  {selected.justify_url}
                </a>
              </p>
            )}
            {renderDataDiff(
              "Datos asociados",
              selected.original_data,
              selected.modified_data
            )}
            {canWrite &&
              selected.clock_in_id &&
              selected.status !== "resolved" && (
                <form onSubmit={applyClock} className="form-grid">
                  <h4 className="form-grid-full">Corregir fichaje</h4>
                  <label>
                    Nueva fecha/hora
                    <input
                      type="datetime-local"
                      required
                      value={clockForm.recorded_at}
                      onChange={(ev) =>
                        setClockForm({ ...clockForm, recorded_at: ev.target.value })
                      }
                    />
                  </label>
                  <label className="form-grid-full">
                    Notas
                    <input
                      value={clockForm.notes}
                      onChange={(ev) =>
                        setClockForm({ ...clockForm, notes: ev.target.value })
                      }
                    />
                  </label>
                  <div className="form-actions form-grid-full">
                    <button type="submit" className="btn btn-primary">
                      Aplicar corrección
                    </button>
                  </div>
                </form>
              )}
          </div>
        )}
      </Modal>
    </>
  );
}
