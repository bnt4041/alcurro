import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Link } from "react-router-dom";
import { api, buildQuery } from "../api/client";
import type { ClockIn, Incident, IncidentNote, LeaveRequest } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

type IncidentCategory = "fichaje" | "vacaciones" | "permiso";

const emptyCreateForm = () => ({
  employee_id: "",
  category: "fichaje" as IncidentCategory,
  title: "",
  description: "",
  incident_date: new Date().toISOString().slice(0, 10),
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

type IncidentRow = Incident & { status_label: string; category_label: string };
type ActionType = "clock" | "break" | "leave" | null;

interface ClockActionForm {
  action: "create" | "modify";
  clock_in_id: string;         // id del fichaje seleccionado (para modify)
  entrada_at: string;
  salida_at: string;
  notes: string;
}
interface BreakActionForm {
  action: "create" | "modify";
  break_id: string;             // parada a modificar (modify)
  clock_in_id: string;          // fichaje al que pertenece la parada (create)
  record_type: "inicio_parada" | "fin_parada";
  recorded_at: string;
  notes: string;
}
interface LeaveActionForm {
  action: "create" | "modify";
  leave_id: string;             // id del permiso seleccionado (para modify)
  start_date: string;
  end_date: string;
  days_requested: string;
  reason: string;
}

// ── Componente FileDropzone ───────────────────────────────────────────────────
function FileDropzone({ files, onChange }: { files: File[]; onChange: (f: File[]) => void }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => onChange([...files, ...accepted]),
    multiple: true,
    accept: { "image/*": [], "application/pdf": [], "application/msword": [],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [] },
  });
  const remove = (i: number) => onChange(files.filter((_, idx) => idx !== i));
  return (
    <div className="file-dropzone-wrapper">
      <div {...getRootProps()} className={`file-dropzone${isDragActive ? " is-dragging" : ""}`}>
        <input {...getInputProps()} />
        <span className="file-dropzone-icon">📁</span>
        <span>{isDragActive ? "Suelta los archivos aquí…" : "Arrastra archivos o haz clic para seleccionar"}</span>
        <span className="file-dropzone-hint">Imágenes, PDF, Word</span>
      </div>
      {files.length > 0 && (
        <ul className="file-dropzone-list">
          {files.map((f, i) => (
            <li key={i} className="file-dropzone-item">
              <span className="file-dropzone-name">{f.name}</span>
              <span className="file-dropzone-size">({(f.size / 1024).toFixed(0)} KB)</span>
              <button type="button" className="file-dropzone-remove" onClick={() => remove(i)} title="Quitar">✕</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Componente SearchableSelect inline ────────────────────────────────────────
function SearchableSelect<T extends { id: string; label: string }>({
  options, value, onChange, placeholder = "Buscar…",
}: {
  options: T[];
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const filtered = options.filter((o) =>
    o.label.toLowerCase().includes(q.toLowerCase())
  );
  return (
    <div className="searchable-select">
      <input
        type="text" placeholder={placeholder} value={q}
        onChange={(e) => setQ(e.target.value)}
        className="searchable-select__input"
      />
      <select
        size={Math.min(6, Math.max(2, filtered.length))}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="searchable-select__list"
      >
        <option value="">— ninguno —</option>
        {filtered.map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function nowLocal() {
  return new Date().toISOString().slice(0, 16);
}
function toLocalInput(iso: string | null | undefined) {
  if (!iso) return "";
  try { return new Date(iso).toISOString().slice(0, 16); } catch { return ""; }
}

export default function IncidentsPage() {
  const { user } = useAuth();
  const { notify } = useToast();
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
  const [notes, setNotes] = useState<IncidentNote[]>([]);
  const [noteText, setNoteText] = useState("");
  const [notesLoading, setNotesLoading] = useState(false);

  // send-message modal
  const [sendOpen, setSendOpen] = useState(false);
  const [sendChannel, setSendChannel] = useState<"whatsapp" | "email">("whatsapp");
  const [sendMessage, setSendMessage] = useState("");
  const [sendEmail, setSendEmail] = useState("");
  const [sendFiles, setSendFiles] = useState<File[]>([]);
  const [sendSending, setSendSending] = useState(false);

  // acciones
  const [actionType, setActionType] = useState<ActionType>(null);
  const [clockForm, setClockForm] = useState<ClockActionForm>({
    action: "create", clock_in_id: "", entrada_at: nowLocal(), salida_at: "", notes: "",
  });
  const [breakForm, setBreakForm] = useState<BreakActionForm>({
    action: "create", break_id: "", clock_in_id: "", record_type: "inicio_parada", recorded_at: nowLocal(), notes: "",
  });
  const [leaveForm, setLeaveForm] = useState<LeaveActionForm>({
    action: "create", leave_id: "", start_date: "", end_date: "", days_requested: "1", reason: "",
  });
  const [actionWorking, setActionWorking] = useState(false);
  const [askManaged, setAskManaged] = useState(false);

  // datos para autocomplete en modales de acción
  const [actionClocks, setActionClocks] = useState<ClockIn[]>([]);
  const [actionLeaves, setActionLeaves] = useState<LeaveRequest[]>([]);

  const load = useCallback(async () => {
    if (!canRead) return;
    setLoading(true);
    try { setRows(await api.get<Incident[]>("/incidents")); }
    finally { setLoading(false); }
  }, [canRead]);

  useEffect(() => { load(); }, [load]);

  // Cargar fichajes/permisos del empleado para create form
  useEffect(() => {
    if (!createOpen || !createForm.employee_id) { setLinkClocks([]); setLinkLeaves([]); return; }
    const emp = createForm.employee_id;
    if (createForm.category === "fichaje") {
      api.get<ClockIn[]>(`/clock-ins${buildQuery({ employee_id: emp, limit: "100" })}`)
        .then(setLinkClocks).catch(() => setLinkClocks([]));
      setLinkLeaves([]);
    } else {
      api.get<LeaveRequest[]>(`/leave-requests${buildQuery({ employee_id: emp })}`)
        .then(setLinkLeaves).catch(() => setLinkLeaves([]));
      setLinkClocks([]);
    }
  }, [createOpen, createForm.employee_id, createForm.category]);

  // Cargar datos para modales de acción cuando se abre
  const loadActionData = useCallback(async (incident: Incident) => {
    try {
      const [clocks, leaves] = await Promise.all([
        api.get<ClockIn[]>(`/clock-ins${buildQuery({ employee_id: incident.employee_id, limit: "200" })}`),
        api.get<LeaveRequest[]>(`/leave-requests${buildQuery({ employee_id: incident.employee_id })}`),
      ]);
      // Ordenar: los más cercanos a incident_date primero
      if (incident.incident_date) {
        const d = incident.incident_date;
        clocks.sort((a, b) => {
          const da = Math.abs(new Date(a.entrada_at).toISOString().slice(0, 10).localeCompare(d));
          const db = Math.abs(new Date(b.entrada_at).toISOString().slice(0, 10).localeCompare(d));
          return da - db;
        });
      }
      setActionClocks(clocks);
      setActionLeaves(leaves);
    } catch { setActionClocks([]); setActionLeaves([]); }
  }, []);

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
        incident_date: createForm.incident_date || null,
        clock_in_id: createForm.category === "fichaje" && createForm.clock_in_id ? createForm.clock_in_id : null,
        leave_request_id: createForm.category !== "fichaje" && createForm.leave_request_id ? createForm.leave_request_id : null,
        require_justification: createForm.require_justification,
        notify_whatsapp: createForm.notify_whatsapp,
      });
      setCreateOpen(false);
      notify("Incidencia creada", "success");
      load();
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
  };

  const tableData = useMemo<IncidentRow[]>(
    () => rows.map((r) => ({
      ...r,
      status_label: STATUS_LABELS[r.status] ?? r.status,
      category_label: r.category === "fichaje" ? "Fichaje" : r.category === "vacaciones" ? "Vacaciones" : "Permiso",
    })),
    [rows]
  );

  const columns = useMemo<DataTableColumn<IncidentRow>[]>(
    () => [
      {
        title: "Fecha incidencia", field: "incident_date", sorter: "string", width: 140,
        formatter: (c) => {
          const v = c.getValue() as string | null;
          return v ? new Date(v + "T00:00:00").toLocaleDateString("es-ES") : "—";
        },
      },
      {
        title: "Registrada", field: "created_at", sorter: "datetime",
        formatter: (c) => new Date(String(c.getValue())).toLocaleString("es-ES"), minWidth: 150,
      },
      { title: "Empleado", field: "employee_name", headerFilter: "input", minWidth: 160 },
      { title: "Título", field: "title", headerFilter: "input", minWidth: 180 },
      { title: "Tipo", field: "category_label", headerFilter: "input", width: 110 },
      { title: "Estado", field: "status_label", headerFilter: "input", width: 160 },
      {
        title: "Gestionada", field: "managed", width: 110,
        formatter: (c) => c.getValue() ? `<span class="badge badge-ok">Sí</span>` : `<span class="badge badge-muted">No</span>`,
      },
      {
        title: "", field: "id", headerFilter: false, download: false, width: 80,
        formatter: () => `<button type="button" class="btn btn-sm" data-action="view">Ver</button>`,
      },
    ],
    []
  );

  const openDetail = async (row: IncidentRow) => {
    setSelected(row);
    setNotes([]); setNoteText(""); setAskManaged(false); setActionType(null);
    setNotesLoading(true);
    api.get<IncidentNote[]>(`/incidents/${row.id}/notes`)
      .then(setNotes).catch(() => setNotes([]))
      .finally(() => setNotesLoading(false));
    await loadActionData(row);
  };

  const refreshSelected = async (id: string) => {
    const updated = await api.get<Incident>(`/incidents/${id}`);
    setSelected(updated);
    setRows((prev) => prev.map((r) => (r.id === id ? updated : r)));
    return updated;
  };

  const toggleManaged = async () => {
    if (!selected || !canWrite) return;
    try {
      const updated = await api.patch<Incident>(`/incidents/${selected.id}`, { managed: !selected.managed });
      setSelected(updated);
      setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      notify(updated.managed ? "Marcada como gestionada" : "Desmarcada", "success");
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
  };

  const addNewNote = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !noteText.trim()) return;
    try {
      const note = await api.post<IncidentNote>(`/incidents/${selected.id}/notes`, { content: noteText.trim() });
      setNotes((prev) => [...prev, note]);
      setNoteText("");
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
  };

  const openSendMessage = (channel: "whatsapp" | "email") => {
    setSendChannel(channel); setSendMessage(""); setSendEmail(""); setSendFiles([]); setSendOpen(true);
  };

  const doSendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !sendMessage.trim()) return;
    setSendSending(true);
    try {
      const fd = new FormData();
      fd.append("channel", sendChannel);
      fd.append("message", sendMessage.trim());
      if (sendChannel === "email") fd.append("recipient_email", sendEmail);
      sendFiles.forEach((f) => fd.append("files", f));
      await api.upload(`/incidents/${selected.id}/send-message`, fd);
      setSendOpen(false);
      notify(sendChannel === "whatsapp" ? "WhatsApp enviado" : `Email enviado`, "success");
      api.get<IncidentNote[]>(`/incidents/${selected.id}/notes`).then(setNotes).catch(() => {});
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
    finally { setSendSending(false); }
  };

  // ── Abrir acción: pre-poblar formulario con los datos vinculados ─────────────
  const openAction = (type: ActionType) => {
    if (!selected) return;

    if (type === "clock") {
      const linked = actionClocks.find((c) => c.id === selected.clock_in_id);
      const best = linked || (actionClocks.length > 0 ? actionClocks[0] : null);
      const initialAction = (linked || actionClocks.length > 0) ? "modify" : "create";
      setClockForm({
        action: initialAction,
        clock_in_id: best?.id ?? "",
        entrada_at: best ? toLocalInput(best.entrada_at) : (selected.incident_date ? selected.incident_date + "T08:00" : nowLocal()),
        salida_at: best?.salida_at ? toLocalInput(best.salida_at) : "",
        notes: best?.notes ?? "",
      });
    } else if (type === "break") {
      const linked = actionClocks.find((c) => c.id === selected.clock_in_id);
      const best = linked || (actionClocks.length > 0 ? actionClocks[0] : null);
      setBreakForm({
        action: selected.break_id ? "modify" : "create",
        break_id: selected.break_id ?? "",
        clock_in_id: best?.id ?? "",
        record_type: "inicio_parada",
        recorded_at: selected.incident_date ? selected.incident_date + "T10:00" : nowLocal(),
        notes: "",
      });
    } else if (type === "leave") {
      const linked = actionLeaves.find((l) => l.id === selected.leave_request_id);
      const initialAction = (linked || actionLeaves.length > 0) ? "modify" : "create";
      const best = linked || (actionLeaves.length > 0 ? actionLeaves[0] : null);
      setLeaveForm({
        action: initialAction,
        leave_id: best?.id ?? "",
        start_date: best?.start_date ?? selected.incident_date ?? "",
        end_date: best?.end_date ?? selected.incident_date ?? "",
        days_requested: String(best?.days_requested ?? "1"),
        reason: best?.reason ?? "",
      });
    }
    setActionType(type);
  };

  // Actualizar campos del formulario de fichaje cuando se selecciona un fichaje
  const onClockSelected = (clockId: string) => {
    const c = actionClocks.find((x) => x.id === clockId);
    setClockForm((prev) => ({
      ...prev,
      clock_in_id: clockId,
      entrada_at: c ? toLocalInput(c.entrada_at) : prev.entrada_at,
      salida_at: c?.salida_at ? toLocalInput(c.salida_at) : "",
      notes: c?.notes ?? prev.notes,
    }));
  };

  const onBreakClockSelected = (clockId: string) => {
    setBreakForm((prev) => ({ ...prev, clock_in_id: clockId }));
  };

  const onLeaveSelected = (leaveId: string) => {
    const l = actionLeaves.find((x) => x.id === leaveId);
    setLeaveForm((prev) => ({
      ...prev,
      leave_id: leaveId,
      start_date: l?.start_date ?? prev.start_date,
      end_date: l?.end_date ?? prev.end_date,
      days_requested: String(l?.days_requested ?? prev.days_requested),
      reason: l?.reason ?? prev.reason,
    }));
  };

  const submitClockAction = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setActionWorking(true);
    try {
      await api.post(`/incidents/${selected.id}/actions/clock`, {
        action: clockForm.action,
        clock_in_id: clockForm.action === "modify" && clockForm.clock_in_id ? clockForm.clock_in_id : null,
        entrada_at: new Date(clockForm.entrada_at).toISOString(),
        salida_at: clockForm.salida_at ? new Date(clockForm.salida_at).toISOString() : null,
        notes: clockForm.notes || null,
      });
      await refreshSelected(selected.id);
      setActionType(null); setAskManaged(true);
      notify("Fichaje actualizado", "success");
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
    finally { setActionWorking(false); }
  };

  const submitBreakAction = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setActionWorking(true);
    try {
      await api.post(`/incidents/${selected.id}/actions/break`, {
        action: breakForm.action,
        break_id: breakForm.action === "modify" && breakForm.break_id ? breakForm.break_id : null,
        clock_in_id: breakForm.clock_in_id || null,
        record_type: breakForm.record_type,
        recorded_at: new Date(breakForm.recorded_at).toISOString(),
        notes: breakForm.notes || null,
      });
      await refreshSelected(selected.id);
      setActionType(null); setAskManaged(true);
      notify("Parada actualizada", "success");
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
    finally { setActionWorking(false); }
  };

  const submitLeaveAction = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setActionWorking(true);
    try {
      await api.post(`/incidents/${selected.id}/actions/leave`, {
        action: leaveForm.action,
        leave_id: leaveForm.action === "modify" && leaveForm.leave_id ? leaveForm.leave_id : null,
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        days_requested: parseFloat(leaveForm.days_requested),
        reason: leaveForm.reason || null,
      });
      await refreshSelected(selected.id);
      setActionType(null); setAskManaged(true);
      notify("Permiso actualizado", "success");
    } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
    finally { setActionWorking(false); }
  };

  const confirmManaged = async (mark: boolean) => {
    if (!selected) return;
    if (mark) {
      try {
        await api.patch(`/incidents/${selected.id}`, {
          managed: true,
          status: ["open", "pending_justification"].includes(selected.status ?? "") ? "resolved" : selected.status,
        });
        await refreshSelected(selected.id);
        notify("Incidencia marcada como gestionada", "success");
      } catch (err) { notify(String(err).replace(/^Error:\s*/i, ""), "error"); }
    }
    setAskManaged(false);
  };

  // Labels para autocomplete
  const clockOptions = actionClocks.map((c) => ({
    id: c.id,
    label: `${new Date(c.entrada_at).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })} → ${c.salida_at ? new Date(c.salida_at).toLocaleString("es-ES", { timeStyle: "short" }) : "abierto"}${c.notes ? ` · ${c.notes}` : ""}`,
  }));
  const leaveOptions = actionLeaves.map((l) => ({
    id: l.id,
    label: `${l.start_date} → ${l.end_date} (${l.days_requested}d) ${l.status}${l.reason ? ` · ${l.reason.slice(0, 40)}` : ""}`,
  }));

  const renderDataDiff = (label: string, original: Record<string, unknown>, modified: Record<string, unknown> | null) => (
    <div className="incident-diff">
      <h4>{label}</h4>
      <div className="incident-diff-grid">
        <div><strong>Original</strong><pre className="incident-diff-pre">{JSON.stringify(original, null, 2)}</pre></div>
        {modified && <div><strong>Modificado</strong><pre className="incident-diff-pre">{JSON.stringify(modified, null, 2)}</pre></div>}
      </div>
    </div>
  );

  if (!canRead) return <p className="muted">No tienes permiso para ver incidencias.</p>;

  return (
    <>
      <PageHeader
        title="Incidencias"
        subtitle="Fichajes, vacaciones y permisos — correcciones con registro original y modificado"
        action={canWrite ? (
          <div className="header-actions">
            <Link to="/app/fichajes/configuracion" className="btn">Reglas automáticas</Link>
            <button type="button" className="btn btn-primary" onClick={() => { setCreateForm(emptyCreateForm()); setCreateOpen(true); }}>
              + Nueva incidencia
            </button>
          </div>
        ) : undefined}
      />

      <DataTable
        data={tableData} columns={columns} loading={loading}
        exportFilename="incidencias" height="520px"
        onCellAction={(action, row) => { if (action === "view") openDetail(row); }}
      />

      {/* ── Modal crear ── */}
      <Modal title="Nueva incidencia manual" open={createOpen && !!canWrite} onClose={() => setCreateOpen(false)}>
        <form onSubmit={saveCreate} className="form-grid">
          <label>
            Empleado
            <select required value={createForm.employee_id}
              onChange={(ev) => setCreateForm({ ...createForm, employee_id: ev.target.value, clock_in_id: "", leave_request_id: "" })}>
              <option value="">Seleccionar…</option>
              {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.employee_code})</option>)}
            </select>
          </label>
          <label>
            Categoría
            <select value={createForm.category}
              onChange={(ev) => setCreateForm({ ...createForm, category: ev.target.value as IncidentCategory, clock_in_id: "", leave_request_id: "" })}>
              <option value="fichaje">Fichaje</option>
              <option value="vacaciones">Vacaciones</option>
              <option value="permiso">Permiso</option>
            </select>
          </label>
          <label>
            Fecha del incidente
            <input type="date" value={createForm.incident_date}
              onChange={(ev) => setCreateForm({ ...createForm, incident_date: ev.target.value })} />
          </label>
          <label className="form-grid-full">
            Título
            <input required maxLength={300} value={createForm.title}
              onChange={(ev) => setCreateForm({ ...createForm, title: ev.target.value })} />
          </label>
          <label className="form-grid-full">
            Descripción (opcional)
            <textarea rows={3} maxLength={2000} value={createForm.description}
              onChange={(ev) => setCreateForm({ ...createForm, description: ev.target.value })} />
          </label>
          {createForm.category === "fichaje" && createForm.employee_id && (
            <label className="form-grid-full">
              Vincular a fichaje (opcional)
              <select value={createForm.clock_in_id}
                onChange={(ev) => setCreateForm({ ...createForm, clock_in_id: ev.target.value })}>
                <option value="">Sin vincular</option>
                {linkClocks.map((c) => (
                  <option key={c.id} value={c.id}>
                    {new Date(c.entrada_at).toLocaleString("es-ES")}{c.salida_at ? ` → ${new Date(c.salida_at).toLocaleString("es-ES")}` : " (abierta)"}
                    {c.notes ? ` · ${c.notes}` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          {createForm.category !== "fichaje" && createForm.employee_id && (
            <label className="form-grid-full">
              Vincular a solicitud (opcional)
              <select value={createForm.leave_request_id}
                onChange={(ev) => setCreateForm({ ...createForm, leave_request_id: ev.target.value })}>
                <option value="">Sin vincular</option>
                {linkLeaves.map((l) => (
                  <option key={l.id} value={l.id}>{l.start_date} → {l.end_date} ({l.status})</option>
                ))}
              </select>
            </label>
          )}
          <label className="checkbox form-grid-full">
            <input type="checkbox" checked={createForm.require_justification}
              onChange={(ev) => setCreateForm({ ...createForm, require_justification: ev.target.checked, notify_whatsapp: ev.target.checked ? createForm.notify_whatsapp : false })} />
            <span>Requerir justificación del empleado</span>
          </label>
          {createForm.require_justification && (
            <label className="checkbox form-grid-full">
              <input type="checkbox" checked={createForm.notify_whatsapp}
                onChange={(ev) => setCreateForm({ ...createForm, notify_whatsapp: ev.target.checked })} />
              <span>Notificar por WhatsApp con el enlace</span>
            </label>
          )}
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setCreateOpen(false)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Crear incidencia</button>
          </div>
        </form>
      </Modal>

      {/* ── Modal detalle ── */}
      <Modal title={selected?.title ?? "Incidencia"} open={!!selected} onClose={() => setSelected(null)} wide>
        {selected && (
          <div className="incident-detail">

            {/* Header */}
            <div className="incident-detail-header">
              <div className="incident-meta">
                <div className="incident-employee">{selected.employee_name}</div>
                <div className="incident-status-row">
                  <span className={`badge badge-status${selected.status === "resolved" ? " is-resolved" : selected.status === "open" ? " is-open" : selected.status === "pending_justification" ? " is-pending" : ""}`}>
                    {STATUS_LABELS[selected.status] ?? selected.status}
                  </span>
                  {selected.incident_date && (
                    <span className="badge badge-muted">
                      {new Date(selected.incident_date + "T00:00:00").toLocaleDateString("es-ES")}
                    </span>
                  )}
                  {selected.source === "whatsapp" && <span className="badge badge-whatsapp">WhatsApp</span>}
                  <span className={`badge${selected.managed ? " badge-ok" : " badge-muted"}`}>
                    {selected.managed ? "Gestionada" : "Sin gestionar"}
                  </span>
                </div>
              </div>
              {canWrite && (
                <button type="button"
                  className={`btn btn-sm${selected.managed ? " btn-primary" : ""}`}
                  onClick={toggleManaged}>
                  {selected.managed ? "✓ Gestionada" : "Marcar gestionada"}
                </button>
              )}
            </div>

            {/* Body */}
            {selected.description && <p className="incident-body-text">{selected.description}</p>}
            {selected.employee_justification && (
              <div className="alert alert-info">
                <strong>Justificación:</strong> {selected.employee_justification}
              </div>
            )}
            {selected.justify_url && (
              <p className="muted small" style={{ marginBottom: "0.5rem" }}>
                Enlace justificación: <a href={selected.justify_url} target="_blank" rel="noreferrer">{selected.justify_url}</a>
              </p>
            )}
            {selected.internal_notes && (
              <div className="alert" style={{ marginBottom: "0.5rem" }}>
                <strong>Notas internas:</strong> {selected.internal_notes}
              </div>
            )}

            {/* Comunicar */}
            {canWrite && (
              <div className="incident-comm-row">
                <button type="button" className="btn btn-sm" onClick={() => openSendMessage("whatsapp")}>📱 Enviar WhatsApp</button>
                <button type="button" className="btn btn-sm" onClick={() => openSendMessage("email")}>📧 Enviar Email</button>
              </div>
            )}

            {/* Acciones */}
            {canWrite && (
              <div className="incident-actions-section">
                <div className="incident-actions-label">Acciones sobre registros</div>
                <div className="incident-actions-grid">
                  <button type="button" className="incident-action-btn" onClick={() => openAction("clock")}>
                    🕐 Fichaje
                  </button>
                  <button type="button" className="incident-action-btn" onClick={() => openAction("break")}>
                    ⏸ Parada
                  </button>
                  <button type="button" className="incident-action-btn" onClick={() => openAction("leave")}>
                    📅 Permiso
                  </button>
                </div>
              </div>
            )}

            {/* Pregunta gestión */}
            {askManaged && (
              <div className="incident-ask-managed">
                <span>Acción completada. ¿Marcar la incidencia como gestionada?</span>
                <div className="incident-ask-managed-actions">
                  <button type="button" className="btn btn-sm btn-primary" onClick={() => confirmManaged(true)}>Sí, marcar</button>
                  <button type="button" className="btn btn-sm" onClick={() => confirmManaged(false)}>Ahora no</button>
                </div>
              </div>
            )}

            {/* Datos asociados */}
            {Object.keys(selected.original_data ?? {}).length > 0 && renderDataDiff("Datos asociados", selected.original_data, selected.modified_data)}

            {/* Notas */}
            <div className="incident-notes-section">
              <h4>Notas</h4>
              {notesLoading ? <p className="muted">Cargando…</p>
                : notes.length === 0 ? <p className="muted small">Sin notas todavía.</p>
                : (
                  <div className="incident-notes-list">
                    {notes.map((n) => (
                      <div key={n.id} className="incident-note-item">
                        <div className="incident-note-meta">
                          <strong>{n.author_name ?? "Sistema"}</strong> · {new Date(n.created_at).toLocaleString("es-ES")}
                        </div>
                        <div className="incident-note-content">{n.content}</div>
                      </div>
                    ))}
                  </div>
                )}
              {canWrite && (
                <form onSubmit={addNewNote} style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem" }}>
                  <input type="text" placeholder="Añadir nota…" value={noteText}
                    onChange={(ev) => setNoteText(ev.target.value)} style={{ flex: 1 }} maxLength={5000} />
                  <button type="submit" className="btn btn-sm btn-primary" disabled={!noteText.trim()}>Guardar</button>
                </form>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* ── Modal envío ── */}
      <Modal title={sendChannel === "whatsapp" ? "📱 Enviar WhatsApp" : "📧 Enviar Email"} open={sendOpen} onClose={() => setSendOpen(false)}>
        <form onSubmit={doSendMessage} className="form-grid">
          {sendChannel === "email" && (
            <label className="form-grid-full">
              Email destinatario
              <input type="email" required placeholder="email@ejemplo.com" value={sendEmail}
                onChange={(ev) => setSendEmail(ev.target.value)} />
            </label>
          )}
          <label className="form-grid-full">
            Mensaje
            <textarea rows={4} maxLength={2000} required value={sendMessage}
              onChange={(ev) => setSendMessage(ev.target.value)} placeholder="Escribe el mensaje…" />
          </label>
          <div className="form-grid-full">
            <label style={{ display: "block", marginBottom: "0.4rem", fontSize: "0.85rem", color: "var(--muted)" }}>
              Adjuntos (opcional)
            </label>
            <FileDropzone files={sendFiles} onChange={setSendFiles} />
          </div>
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setSendOpen(false)}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={sendSending}>{sendSending ? "Enviando…" : "Enviar"}</button>
          </div>
        </form>
      </Modal>

      {/* ── Sub-modal: acción fichaje ── */}
      <Modal title="Acción sobre fichaje" open={actionType === "clock"} onClose={() => setActionType(null)} wide>
        <form onSubmit={submitClockAction} className="form-grid">
          <div className="form-grid-full action-toggle">
            <button type="button"
              className={`action-toggle-opt${clockForm.action === "modify" ? " is-active" : ""}`}
              onClick={() => setClockForm((p) => ({ ...p, action: "modify" }))}>
              Modificar existente
            </button>
            <button type="button"
              className={`action-toggle-opt${clockForm.action === "create" ? " is-active" : ""}`}
              onClick={() => setClockForm((p) => ({ ...p, action: "create", clock_in_id: "" }))}>
              Crear nuevo
            </button>
          </div>
          {clockForm.action === "modify" && clockOptions.length > 0 && (
            <div className="form-grid-full">
              <label style={{ display: "block", marginBottom: "0.25rem" }}>Fichaje a modificar</label>
              <SearchableSelect
                options={clockOptions}
                value={clockForm.clock_in_id}
                onChange={onClockSelected}
                placeholder="Buscar por fecha, hora…"
              />
            </div>
          )}
          {clockForm.action === "modify" && clockOptions.length === 0 && (
            <p className="muted form-grid-full">No hay fichajes registrados para este empleado.</p>
          )}
          <label>
            {clockForm.action === "modify" ? "Nueva entrada" : "Entrada"}
            <input type="datetime-local" required value={clockForm.entrada_at}
              onChange={(ev) => setClockForm({ ...clockForm, entrada_at: ev.target.value })} />
          </label>
          <label>
            {clockForm.action === "modify" ? "Nueva salida (opcional)" : "Salida (opcional)"}
            <input type="datetime-local" value={clockForm.salida_at}
              onChange={(ev) => setClockForm({ ...clockForm, salida_at: ev.target.value })} />
          </label>
          <label className="form-grid-full">
            Notas
            <input maxLength={500} value={clockForm.notes}
              onChange={(ev) => setClockForm({ ...clockForm, notes: ev.target.value })} />
          </label>
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setActionType(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={actionWorking}>
              {actionWorking ? "Guardando…" : clockForm.action === "create" ? "Crear fichaje" : "Aplicar cambio"}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Sub-modal: acción parada ── */}
      <Modal title="Acción sobre parada" open={actionType === "break"} onClose={() => setActionType(null)} wide>
        <form onSubmit={submitBreakAction} className="form-grid">
          <div className="form-grid-full action-toggle">
            <button type="button"
              className={`action-toggle-opt${breakForm.action === "modify" ? " is-active" : ""}`}
              onClick={() => setBreakForm((p) => ({ ...p, action: "modify" }))}>
              Modificar existente
            </button>
            <button type="button"
              className={`action-toggle-opt${breakForm.action === "create" ? " is-active" : ""}`}
              onClick={() => setBreakForm((p) => ({ ...p, action: "create", break_id: "" }))}>
              Crear nueva
            </button>
          </div>
          {breakForm.action === "create" && (
            <div className="form-grid-full">
              <label style={{ display: "block", marginBottom: "0.25rem" }}>Fichaje al que vincular *</label>
              <SearchableSelect
                options={clockOptions}
                value={breakForm.clock_in_id}
                onChange={onBreakClockSelected}
                placeholder="Buscar fichaje por fecha u hora…"
              />
            </div>
          )}
          <label>
            Tipo
            <select value={breakForm.record_type}
              onChange={(ev) => setBreakForm({ ...breakForm, record_type: ev.target.value as "inicio_parada" | "fin_parada" })}>
              <option value="inicio_parada">Inicio parada</option>
              <option value="fin_parada">Fin parada</option>
            </select>
          </label>
          <label>
            Fecha/hora
            <input type="datetime-local" required value={breakForm.recorded_at}
              onChange={(ev) => setBreakForm({ ...breakForm, recorded_at: ev.target.value })} />
          </label>
          <label className="form-grid-full">
            Notas
            <input maxLength={500} value={breakForm.notes}
              onChange={(ev) => setBreakForm({ ...breakForm, notes: ev.target.value })} />
          </label>
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setActionType(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={actionWorking}>
              {actionWorking ? "Guardando…" : breakForm.action === "create" ? "Crear parada" : "Aplicar cambio"}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Sub-modal: acción permiso ── */}
      <Modal title="Acción sobre permiso" open={actionType === "leave"} onClose={() => setActionType(null)} wide>
        <form onSubmit={submitLeaveAction} className="form-grid">
          <div className="form-grid-full action-toggle">
            <button type="button"
              className={`action-toggle-opt${leaveForm.action === "modify" ? " is-active" : ""}`}
              onClick={() => setLeaveForm((p) => ({ ...p, action: "modify" }))}>
              Modificar existente
            </button>
            <button type="button"
              className={`action-toggle-opt${leaveForm.action === "create" ? " is-active" : ""}`}
              onClick={() => setLeaveForm((p) => ({ ...p, action: "create", leave_id: "" }))}>
              Crear nuevo
            </button>
          </div>
          {leaveForm.action === "modify" && leaveOptions.length > 0 && (
            <div className="form-grid-full">
              <label style={{ display: "block", marginBottom: "0.25rem" }}>Permiso a modificar</label>
              <SearchableSelect
                options={leaveOptions}
                value={leaveForm.leave_id}
                onChange={onLeaveSelected}
                placeholder="Buscar por fechas o motivo…"
              />
            </div>
          )}
          {leaveForm.action === "modify" && leaveOptions.length === 0 && (
            <p className="muted form-grid-full">No hay permisos registrados para este empleado.</p>
          )}
          <label>
            Fecha inicio
            <input type="date" required value={leaveForm.start_date}
              onChange={(ev) => setLeaveForm({ ...leaveForm, start_date: ev.target.value })} />
          </label>
          <label>
            Fecha fin
            <input type="date" required value={leaveForm.end_date}
              onChange={(ev) => setLeaveForm({ ...leaveForm, end_date: ev.target.value })} />
          </label>
          <label>
            Días
            <input type="number" required min="0.5" step="0.5" value={leaveForm.days_requested}
              onChange={(ev) => setLeaveForm({ ...leaveForm, days_requested: ev.target.value })} />
          </label>
          <label className="form-grid-full">
            Motivo
            <textarea rows={2} maxLength={1000} value={leaveForm.reason}
              onChange={(ev) => setLeaveForm({ ...leaveForm, reason: ev.target.value })} />
          </label>
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setActionType(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={actionWorking}>
              {actionWorking ? "Guardando…" : leaveForm.action === "create" ? "Crear permiso" : "Aplicar cambio"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
