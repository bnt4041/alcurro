import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  ClockIn,
  DocumentDelivery,
  Incident,
  LeaveRequest,
  NotificationPreference,
} from "../api/types";
import DataTable, { type DataTableColumn } from "./DataTable";

interface InboundDoc {
  id: string;
  document_code: string;
  document_name: string;
  status: string;
  document_delivery_id: string | null;
  signature_envelope_id: string | null;
  received_at: string | null;
  created_at: string;
}

interface SignatureSigner {
  id: string;
  full_name: string;
  status: string;
  signed_at: string | null;
}

interface SignatureEnvelope {
  id: string;
  reference: string;
  title: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  signers: SignatureSigner[];
}

type TabId = "data" | "clock_ins" | "leaves" | "incidents" | "documents" | "signatures" | "notifications";

interface Props {
  employeeId: string;
  employeeName: string;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  showDocuments: boolean;
  showSignatures: boolean;
  showClockIns?: boolean;
  showLeaves?: boolean;
  showIncidents?: boolean;
  children: React.ReactNode;
}

const TABS: { id: TabId; label: string; show?: (p: Props) => boolean }[] = [
  { id: "data", label: "Datos" },
  { id: "clock_ins", label: "Fichajes", show: (p) => p.showClockIns !== false },
  { id: "leaves", label: "Permisos", show: (p) => p.showLeaves !== false },
  { id: "incidents", label: "Incidencias", show: (p) => p.showIncidents !== false },
  { id: "documents", label: "Documentos", show: (p) => p.showDocuments },
  { id: "signatures", label: "Firmas", show: (p) => p.showSignatures },
  { id: "notifications", label: "Notificaciones" },
];

const EVENT_LABELS: Record<string, string> = {
  clock_in: "Fichaje entrada",
  clock_out: "Fichaje salida",
  leave_request: "Vacaciones / permisos",
  incident: "Incidencias",
  document: "Documentos",
};
const CHANNEL_LABELS: Record<string, string> = {
  inapp: "En la app",
  whatsapp: "WhatsApp",
  email: "Email",
};

const INBOUND_STATUS: Record<string, string> = {
  pending: "Pendiente",
  received: "Recibido",
  waived: "No aplica",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobado",
  rejected: "Rechazado",
  cancelled: "Cancelado",
  open: "Abierta",
  resolved: "Resuelta",
  justified: "Justificada",
};

function fmtDT(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" });
}
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-ES");
}

export default function EmployeeProfileTabs({
  employeeId,
  employeeName,
  activeTab,
  onTabChange,
  showDocuments,
  showSignatures,
  showClockIns = true,
  showLeaves = true,
  showIncidents = true,
  children,
}: Props) {
  const props = { showDocuments, showSignatures, showClockIns, showLeaves, showIncidents } as Props;
  const visibleTabs = TABS.filter((t) => !t.show || t.show(props));

  // Documents
  const [inbound, setInbound] = useState<InboundDoc[]>([]);
  const [deliveries, setDeliveries] = useState<DocumentDelivery[]>([]);
  const [envelopes, setEnvelopes] = useState<SignatureEnvelope[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingSigs, setLoadingSigs] = useState(false);
  const [docsMsg, setDocsMsg] = useState("");
  const [prefs, setPrefs] = useState<NotificationPreference[]>([]);
  const [loadingPrefs, setLoadingPrefs] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [uploadCode, setUploadCode] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Clock-ins
  const [clockIns, setClockIns] = useState<ClockIn[]>([]);
  const [loadingClocks, setLoadingClocks] = useState(false);

  // Leaves
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loadingLeaves, setLoadingLeaves] = useState(false);

  // Incidents
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loadingIncidents, setLoadingIncidents] = useState(false);

  const deliveryColumns = useMemo<DataTableColumn<Record<string, unknown>>[]>(
    () => [
      {
        title: "",
        field: "file_name",
        headerFilter: false,
        sorter: false,
        download: false,
        width: 50,
        formatter: (cell) => {
          const d = cell.getRow().getData() as Record<string, unknown>;
          const isImg = d.is_image as boolean;
          const docId = d.id as string;
          const url = `/api/documents/${docId}/preview`;
          return isImg
            ? `<img src="${url}" alt="prev" style="width:36px;height:36px;object-fit:cover;border-radius:4px;" loading="lazy" />`
            : `<span style="font-size:18px;opacity:.4;">📄</span>`;
        },
      },
      { title: "Título", field: "title_label", headerFilter: "input" },
      { title: "Tipo", field: "type_label", headerFilter: "input" },
      { title: "Caducidad", field: "expires_label", headerFilter: "input" },
      {
        title: "",
        field: "id",
        headerFilter: false,
        sorter: false,
        download: false,
        width: 110,
        formatter: () =>
          `<button type="button" class="btn btn-sm" data-action="dl">Descargar</button>`,
      },
    ],
    []
  );

  const signatureColumns = useMemo<DataTableColumn<Record<string, unknown>>[]>(
    () => [
      { title: "Referencia", field: "reference", headerFilter: "input" },
      { title: "Título", field: "title", headerFilter: "input" },
      { title: "Estado", field: "status", headerFilter: "input" },
      { title: "Firmante", field: "signer_status", headerFilter: "input" },
      { title: "Firmado", field: "signed_label", headerFilter: "input" },
    ],
    []
  );

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    setDocsMsg("");
    try {
      const [del, inb] = await Promise.all([
        api.get<DocumentDelivery[]>(`/employees/${employeeId}/documents`),
        api.get<InboundDoc[]>(
          `/clock-settings/employees/${employeeId}/inbound-documents`
        ),
      ]);
      setDeliveries(del);
      setInbound(inb);
    } catch (err) {
      setDocsMsg(String(err));
    } finally {
      setLoadingDocs(false);
    }
  }, [employeeId]);

  const loadSignatures = useCallback(async () => {
    setLoadingSigs(true);
    try {
      setEnvelopes(
        await api.get<SignatureEnvelope[]>(`/employees/${employeeId}/signatures`)
      );
    } catch {
      setEnvelopes([]);
    } finally {
      setLoadingSigs(false);
    }
  }, [employeeId]);

  const loadClockIns = useCallback(async () => {
    setLoadingClocks(true);
    try {
      setClockIns(await api.get<ClockIn[]>(`/clock-ins?employee_id=${employeeId}&limit=200`));
    } catch {
      setClockIns([]);
    } finally {
      setLoadingClocks(false);
    }
  }, [employeeId]);

  const loadLeaves = useCallback(async () => {
    setLoadingLeaves(true);
    try {
      setLeaves(await api.get<LeaveRequest[]>(`/leave-requests?employee_id=${employeeId}`));
    } catch {
      setLeaves([]);
    } finally {
      setLoadingLeaves(false);
    }
  }, [employeeId]);

  const loadIncidents = useCallback(async () => {
    setLoadingIncidents(true);
    try {
      setIncidents(await api.get<Incident[]>(`/incidents?employee_id=${employeeId}`));
    } catch {
      setIncidents([]);
    } finally {
      setLoadingIncidents(false);
    }
  }, [employeeId]);

  useEffect(() => {
    if (activeTab === "documents" && showDocuments) loadDocuments();
  }, [activeTab, showDocuments, loadDocuments]);

  useEffect(() => {
    if (activeTab === "signatures" && showSignatures) loadSignatures();
  }, [activeTab, showSignatures, loadSignatures]);

  useEffect(() => {
    if (activeTab === "clock_ins") loadClockIns();
  }, [activeTab, loadClockIns]);

  useEffect(() => {
    if (activeTab === "leaves") loadLeaves();
  }, [activeTab, loadLeaves]);

  useEffect(() => {
    if (activeTab === "incidents") loadIncidents();
  }, [activeTab, loadIncidents]);

  useEffect(() => {
    if (activeTab !== "notifications") return;
    setLoadingPrefs(true);
    api
      .get<NotificationPreference[]>(`/employees/${employeeId}/notification-preferences`)
      .then(setPrefs)
      .catch(() => setPrefs([]))
      .finally(() => setLoadingPrefs(false));
  }, [activeTab, employeeId]);

  function togglePref(event_type: string, channel: string) {
    setPrefs((prev) =>
      prev.map((p) =>
        p.event_type === event_type && p.channel === channel
          ? { ...p, enabled: !p.enabled }
          : p
      )
    );
  }

  async function savePrefs() {
    setSavingPrefs(true);
    try {
      const updated = await api.put<NotificationPreference[]>(
        `/employees/${employeeId}/notification-preferences`,
        { preferences: prefs }
      );
      setPrefs(updated);
    } finally {
      setSavingPrefs(false);
    }
  }

  return (
    <div className="employee-profile-tabs">
      <div className="sheet-tabs employee-profile-tabs__nav">
        {visibleTabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={activeTab === t.id ? "tab active" : "tab"}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "data" && children}

      {/* ── Fichajes ── */}
      {activeTab === "clock_ins" && (
        <div className="employee-profile-panel">
          {loadingClocks ? (
            <p className="muted">Cargando fichajes…</p>
          ) : (
            <DataTable
              data={clockIns.map((c) => ({
                ...c,
                entrada_label: fmtDT(c.entrada_at),
                salida_label: c.salida_at ? fmtDT(c.salida_at) : "Abierto",
                worked_label: (() => {
                  if (!c.salida_at) return "—";
                  const mins = Math.round((new Date(c.salida_at).getTime() - new Date(c.entrada_at).getTime()) / 60000);
                  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
                })(),
                project_label: c.project_name ?? "—",
                source_label: c.source ?? "—",
              }))}
              columns={[
                { title: "Entrada", field: "entrada_label", headerFilter: "input" },
                { title: "Salida", field: "salida_label", headerFilter: "input" },
                { title: "Horas", field: "worked_label", headerFilter: false },
                { title: "Proyecto", field: "project_label", headerFilter: "input" },
                { title: "Origen", field: "source_label", headerFilter: "input" },
              ]}
              exportFilename={`fichajes_${employeeName}`}
              height="340px"
              emptyMessage="Sin fichajes registrados."
            />
          )}
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            <Link to="/app/fichajes">Ver módulo Fichajes</Link>
          </p>
        </div>
      )}

      {/* ── Permisos ── */}
      {activeTab === "leaves" && (
        <div className="employee-profile-panel">
          {loadingLeaves ? (
            <p className="muted">Cargando permisos…</p>
          ) : (
            <DataTable
              data={leaves.map((l) => ({
                ...l,
                tipo_label: l.leave_type_name ?? "—",
                desde_label: fmtDate(l.start_date),
                hasta_label: fmtDate(l.end_date),
                dias_label: l.days_requested,
                estado_label: STATUS_LABEL[l.status] ?? l.status,
                motivo_label: l.reason ?? "—",
                creado_label: fmtDate(l.created_at),
              }))}
              columns={[
                { title: "Tipo", field: "tipo_label", headerFilter: "input" },
                { title: "Desde", field: "desde_label", headerFilter: "input" },
                { title: "Hasta", field: "hasta_label", headerFilter: "input" },
                { title: "Días", field: "dias_label", headerFilter: false, width: 70 },
                { title: "Estado", field: "estado_label", headerFilter: "input" },
                { title: "Motivo", field: "motivo_label", headerFilter: "input" },
                { title: "Creado", field: "creado_label", headerFilter: "input" },
              ]}
              exportFilename={`permisos_${employeeName}`}
              height="340px"
              emptyMessage="Sin solicitudes de permiso."
            />
          )}
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            <Link to="/app/permisos">Ver módulo Permisos</Link>
          </p>
        </div>
      )}

      {/* ── Incidencias ── */}
      {activeTab === "incidents" && (
        <div className="employee-profile-panel">
          {loadingIncidents ? (
            <p className="muted">Cargando incidencias…</p>
          ) : (
            <DataTable
              data={incidents.map((i) => ({
                ...i,
                fecha_label: fmtDT(i.created_at),
                tipo_label: i.incident_type ?? "—",
                estado_label: STATUS_LABEL[i.status] ?? i.status,
                retraso_label: i.minutes_late != null ? `${i.minutes_late} min` : "—",
              }))}
              columns={[
                { title: "Fecha", field: "fecha_label", headerFilter: "input" },
                { title: "Título", field: "title", headerFilter: "input" },
                { title: "Tipo", field: "tipo_label", headerFilter: "input" },
                { title: "Estado", field: "estado_label", headerFilter: "input" },
                { title: "Retraso", field: "retraso_label", headerFilter: false, width: 90 },
              ]}
              exportFilename={`incidencias_${employeeName}`}
              height="340px"
              emptyMessage="Sin incidencias registradas."
            />
          )}
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            <Link to="/app/incidencias">Ver módulo Incidencias</Link>
          </p>
        </div>
      )}

      {/* ── Documentos ── */}
      {activeTab === "documents" && showDocuments && (
        <div className="employee-profile-panel">
          <p className="muted small">
            Documentación de {employeeName}: alta (inbound) y entregas asociadas al
            empleado.
          </p>
          {docsMsg && <div className="alert alert-error">{docsMsg}</div>}
          {loadingDocs ? (
            <p className="muted">Cargando documentos…</p>
          ) : (
            <>
              <h4 className="employee-profile-subtitle">Alta / inbound</h4>
              {inbound.some((r) => r.status === "pending") && (
                <form
                  className="form-grid inbound-upload-form"
                  style={{ marginBottom: "1rem" }}
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (!uploadFile || !uploadCode) return;
                    setUploading(true);
                    setDocsMsg("");
                    try {
                      const fd = new FormData();
                      fd.append("document_code", uploadCode);
                      fd.append("file", uploadFile);
                      const res = await api.upload<{ ok: boolean; message: string }>(
                        `/clock-settings/employees/${employeeId}/inbound-documents/upload`,
                        fd
                      );
                      setDocsMsg(res.message);
                      setUploadFile(null);
                      setUploadCode("");
                      loadDocuments();
                    } catch (err) {
                      setDocsMsg(String(err));
                    } finally {
                      setUploading(false);
                    }
                  }}
                >
                  <label className="form-grid-full">
                    Subir documentación (panel RRHH)
                    <select
                      required
                      value={uploadCode}
                      onChange={(ev) => setUploadCode(ev.target.value)}
                    >
                      <option value="">Tipo de documento…</option>
                      {inbound
                        .filter((r) => r.status === "pending")
                        .map((r) => (
                          <option key={r.document_code} value={r.document_code}>
                            {r.document_name}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label className="form-grid-full">
                    Archivo (PDF o imagen)
                    <input
                      type="file"
                      accept="image/*,.pdf"
                      required
                      onChange={(ev) =>
                        setUploadFile(ev.target.files?.[0] ?? null)
                      }
                    />
                  </label>
                  <div className="form-actions form-grid-full">
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      disabled={uploading}
                    >
                      {uploading ? "Subiendo…" : "Subir y asociar"}
                    </button>
                  </div>
                </form>
              )}
              <DataTable
                data={inbound.map((r) => ({
                  ...r,
                  status_label: INBOUND_STATUS[r.status] ?? r.status,
                  date_label: r.received_at
                    ? new Date(r.received_at).toLocaleString("es-ES")
                    : "—",
                }))}
                columns={[
                  { title: "Documento", field: "document_name", headerFilter: "input" },
                  { title: "Estado", field: "status_label", headerFilter: "input" },
                  { title: "Fecha", field: "date_label", headerFilter: "input" },
                ]}
                exportFilename="inbound_empleado"
                height="220px"
                emptyMessage="Sin requisitos de alta registrados."
              />

              <h4 className="employee-profile-subtitle">Entregas</h4>
              <DataTable
                data={deliveries.map((d) => ({
                  ...d,
                  title_label: d.title ?? d.file_name,
                  type_label: d.document_type_name ?? d.document_type,
                  expires_label: d.expires_at
                    ? new Date(d.expires_at).toLocaleDateString("es-ES")
                    : "—",
                  is_image: /\.(jpe?g|png|gif|webp|svg|bmp)$/i.test(d.file_name ?? ""),
                }))}
                columns={deliveryColumns}
                exportFilename="documentos_empleado"
                height="280px"
                emptyMessage="No hay documentos asociados."
                onCellAction={(action, row) => {
                  if (action === "dl") {
                    const d = row as DocumentDelivery;
                    api.download(`/documents/${d.id}/download`, d.file_name);
                  }
                }}
              />
              <p className="muted small">
                <Link to="/app/documentos">Ver módulo Documentos</Link>
              </p>
            </>
          )}
        </div>
      )}

      {/* ── Firmas ── */}
      {activeTab === "signatures" && showSignatures && (
        <div className="employee-profile-panel">
          <p className="muted small">
            Solicitudes de firma donde {employeeName} es firmante.
          </p>
          <DataTable
            data={envelopes.map((e) => {
              const signer =
                e.signers.find((s) => s.full_name === employeeName) ?? e.signers[0];
              return {
                ...e,
                signer_status: signer?.status ?? "—",
                signed_label: signer?.signed_at
                  ? new Date(signer.signed_at).toLocaleString("es-ES")
                  : "—",
              };
            })}
            columns={signatureColumns}
            loading={loadingSigs}
            exportFilename="firmas_empleado"
            height="280px"
            emptyMessage="Sin firmas asociadas."
          />
          <p className="muted small">
            <Link to="/app/firmas">Ver módulo Firmas</Link>
          </p>
        </div>
      )}

      {/* ── Notificaciones ── */}
      {activeTab === "notifications" && (
        <div className="employee-profile-panel">
          {loadingPrefs && <p className="muted">Cargando preferencias…</p>}
          {!loadingPrefs && prefs.length > 0 && (
            <>
              <p className="muted small">
                Canales por los que {employeeName} recibirá notificaciones de sus subordinados o de acciones propias.
              </p>
              <table className="notif-prefs-table">
                <thead>
                  <tr>
                    <th>Evento</th>
                    {["inapp", "whatsapp", "email"].map((ch) => (
                      <th key={ch}>{CHANNEL_LABELS[ch]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {["clock_in", "clock_out", "leave_request", "incident", "document"].map((ev) => (
                    <tr key={ev}>
                      <td>{EVENT_LABELS[ev] ?? ev}</td>
                      {["inapp", "whatsapp", "email"].map((ch) => {
                        const pref = prefs.find((p) => p.event_type === ev && p.channel === ch);
                        return (
                          <td key={ch} className="notif-prefs-table__cell">
                            <input
                              type="checkbox"
                              checked={pref?.enabled ?? true}
                              onChange={() => togglePref(ev, ch)}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              <button
                type="button"
                className="btn btn-primary"
                disabled={savingPrefs}
                onClick={savePrefs}
              >
                {savingPrefs ? "Guardando…" : "Guardar preferencias"}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
