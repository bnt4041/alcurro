import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DocumentDelivery } from "../api/types";
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

type TabId = "data" | "documents" | "signatures";

interface Props {
  employeeId: string;
  employeeName: string;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  showDocuments: boolean;
  showSignatures: boolean;
  children: React.ReactNode;
}

const TABS: { id: TabId; label: string; show?: (p: Props) => boolean }[] = [
  { id: "data", label: "Datos" },
  {
    id: "documents",
    label: "Documentos",
    show: (p) => p.showDocuments,
  },
  {
    id: "signatures",
    label: "Firmas",
    show: (p) => p.showSignatures,
  },
];

const INBOUND_STATUS: Record<string, string> = {
  pending: "Pendiente",
  received: "Recibido",
  waived: "No aplica",
};

export default function EmployeeProfileTabs({
  employeeId,
  employeeName,
  activeTab,
  onTabChange,
  showDocuments,
  showSignatures,
  children,
}: Props) {
  const props = { showDocuments, showSignatures } as Props;
  const visibleTabs = TABS.filter((t) => !t.show || t.show(props));

  const [inbound, setInbound] = useState<InboundDoc[]>([]);
  const [deliveries, setDeliveries] = useState<DocumentDelivery[]>([]);
  const [envelopes, setEnvelopes] = useState<SignatureEnvelope[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingSigs, setLoadingSigs] = useState(false);
  const [docsMsg, setDocsMsg] = useState("");
  const [uploadCode, setUploadCode] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const deliveryColumns = useMemo<DataTableColumn<Record<string, unknown>>[]>(
    () => [
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
        await api.get<SignatureEnvelope[]>(
          `/employees/${employeeId}/signatures`
        )
      );
    } catch {
      setEnvelopes([]);
    } finally {
      setLoadingSigs(false);
    }
  }, [employeeId]);

  useEffect(() => {
    if (activeTab === "documents" && showDocuments) loadDocuments();
  }, [activeTab, showDocuments, loadDocuments]);

  useEffect(() => {
    if (activeTab === "signatures" && showSignatures) loadSignatures();
  }, [activeTab, showSignatures, loadSignatures]);

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
    </div>
  );
}
