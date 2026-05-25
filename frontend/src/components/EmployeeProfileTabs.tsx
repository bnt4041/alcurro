import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DocumentDelivery } from "../api/types";

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

const SIGN_STATUS: Record<string, string> = {
  borrador: "Borrador",
  enviado: "Enviado",
  parcial: "Parcial",
  completado: "Completado",
  cancelado: "Cancelado",
  expirado: "Expirado",
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
              {inbound.length === 0 ? (
                <p className="muted small">Sin requisitos de alta registrados.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Documento</th>
                        <th>Estado</th>
                        <th>Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inbound.map((r) => (
                        <tr key={r.id}>
                          <td>{r.document_name}</td>
                          <td>
                            <span
                              className={`badge ${
                                r.status === "received" ? "badge-ok" : "badge-pending"
                              }`}
                            >
                              {INBOUND_STATUS[r.status] ?? r.status}
                            </span>
                          </td>
                          <td>
                            {r.received_at
                              ? new Date(r.received_at).toLocaleString("es-ES")
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <h4 className="employee-profile-subtitle">Entregas</h4>
              {deliveries.length === 0 ? (
                <p className="muted small">No hay documentos asociados.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Título</th>
                        <th>Tipo</th>
                        <th>Caducidad</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {deliveries.map((d) => (
                        <tr key={d.id}>
                          <td>{d.title ?? d.file_name}</td>
                          <td>{d.document_type_name ?? d.document_type}</td>
                          <td>
                            {d.expires_at
                              ? new Date(d.expires_at).toLocaleDateString("es-ES")
                              : "—"}
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() =>
                                api.download(
                                  `/documents/${d.id}/download`,
                                  d.file_name
                                )
                              }
                            >
                              Descargar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
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
          {loadingSigs ? (
            <p className="muted">Cargando firmas…</p>
          ) : envelopes.length === 0 ? (
            <p className="muted small">Sin firmas asociadas.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Referencia</th>
                    <th>Título</th>
                    <th>Estado</th>
                    <th>Firmante</th>
                    <th>Firmado</th>
                  </tr>
                </thead>
                <tbody>
                  {envelopes.map((e) => {
                    const signer = e.signers.find(
                      (s) => s.full_name === employeeName
                    ) ?? e.signers[0];
                    return (
                      <tr key={e.id}>
                        <td>
                          <code>{e.reference}</code>
                        </td>
                        <td>{e.title}</td>
                        <td>
                          <span className="badge">{SIGN_STATUS[e.status] ?? e.status}</span>
                        </td>
                        <td>
                          {signer ? (
                            <span
                              className={`badge ${
                                signer.status === "firmado" ? "badge-ok" : "badge-pending"
                              }`}
                            >
                              {signer.status}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          {signer?.signed_at
                            ? new Date(signer.signed_at).toLocaleString("es-ES")
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <p className="muted small">
            <Link to="/app/firmas">Ver módulo Firmas</Link>
          </p>
        </div>
      )}
    </div>
  );
}
