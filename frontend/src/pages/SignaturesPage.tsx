import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { DocumentDelivery } from "../api/types";
import FileDropzone from "../components/FileDropzone";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

interface SignerRow {
  kind: "employee" | "external";
  employee_id: string;
  full_name: string;
  id_document: string;
  email: string;
  phone: string;
  sign_order: number;
}

interface SignatureSigner {
  id: string;
  full_name: string;
  id_document: string;
  status: string;
  sign_order: number;
  signed_at: string | null;
}

interface SignatureEnvelope {
  id: string;
  reference: string;
  title: string;
  status: string;
  document_delivery_id: string | null;
  original_hash: string;
  completed_at: string | null;
  signers: SignatureSigner[];
}

type DocSource = "upload" | "existing";

const STATUS_LABELS: Record<string, string> = {
  borrador: "Borrador",
  enviado: "Enviado",
  parcial: "Parcial",
  completado: "Completado",
  cancelado: "Cancelado",
  expirado: "Expirado",
};

const emptySigner = (order: number): SignerRow => ({
  kind: "employee",
  employee_id: "",
  full_name: "",
  id_document: "",
  email: "",
  phone: "",
  sign_order: order,
});

export default function SignaturesPage() {
  const { user } = useAuth();
  const { employees } = useEmployees();
  const canWrite = user && canModule(user.permissions, "write", "documents");
  const [rows, setRows] = useState<SignatureEnvelope[]>([]);
  const [documents, setDocuments] = useState<DocumentDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [docSource, setDocSource] = useState<DocSource>("upload");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [docId, setDocId] = useState("");
  const [title, setTitle] = useState("");
  const [signers, setSigners] = useState<SignerRow[]>([emptySigner(1)]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [envs, docs] = await Promise.all([
        api.get<SignatureEnvelope[]>("/signatures"),
        api.get<DocumentDelivery[]>("/documents"),
      ]);
      setRows(envs);
      setDocuments(docs);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setError("");
    setDocSource("upload");
    setUploadFile(null);
    setDocId("");
    setTitle("");
    setSigners([emptySigner(1)]);
  };

  const openCreate = () => {
    resetForm();
    setOpen(true);
  };

  const buildSignersPayload = () =>
    signers
      .map((s) => {
        if (s.kind === "employee" && s.employee_id) {
          return { employee_id: s.employee_id, sign_order: s.sign_order };
        }
        if (s.kind === "external" && s.full_name && s.id_document && s.phone) {
          return {
            full_name: s.full_name,
            id_document: s.id_document,
            email: s.email || undefined,
            phone: s.phone,
            sign_order: s.sign_order,
          };
        }
        return null;
      })
      .filter(Boolean);

  const firstEmployeeSignerId = signers.find(
    (s) => s.kind === "employee" && s.employee_id
  )?.employee_id;

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payloadSigners = buildSignersPayload();
    if (payloadSigners.length === 0) {
      setError("Añade al menos un firmante válido");
      return;
    }
    if (docSource === "upload" && !uploadFile) {
      setError("Sube un documento o elige uno existente");
      return;
    }
    if (docSource === "existing" && !docId) {
      setError("Selecciona un documento existente");
      return;
    }
    if (docSource === "upload" && !firstEmployeeSignerId) {
      setError(
        "Para subir un documento nuevo incluye al menos un firmante empleado (titular del archivo)"
      );
      return;
    }

    setSaving(true);
    try {
      if (docSource === "upload" && uploadFile) {
        const fd = new FormData();
        fd.append("file", uploadFile);
        fd.append("title", title || uploadFile.name);
        fd.append("signers_json", JSON.stringify(payloadSigners));
        if (firstEmployeeSignerId) {
          fd.append("owner_employee_id", firstEmployeeSignerId);
        }
        fd.append("send_notifications", "true");
        fd.append("expires_in_days", "14");
        await api.upload<SignatureEnvelope>("/signatures/from-upload", fd);
      } else {
        await api.post("/signatures", {
          document_delivery_id: docId,
          title: title || documents.find((d) => d.id === docId)?.file_name || "Documento",
          signers: payloadSigners,
          send_notifications: true,
          expires_in_days: 14,
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

  const addSigner = () => {
    setSigners((s) => [...s, emptySigner(s.length + 1)]);
  };

  const removeSigner = (index: number) => {
    setSigners((s) =>
      s.length <= 1 ? s : s.filter((_, i) => i !== index).map((row, i) => ({ ...row, sign_order: i + 1 }))
    );
  };

  const cancel = async (id: string) => {
    const reason = prompt("Motivo de cancelación:");
    if (!reason) return;
    await api.post(`/signatures/${id}/cancel`, { reason });
    load();
  };

  const resend = async (envelopeId: string, signerId: string) => {
    await api.post(`/signatures/${envelopeId}/signers/${signerId}/resend`, {});
    alert("Enlace reenviado por WhatsApp");
  };

  return (
    <>
      <PageHeader
        title="Firmas"
        subtitle="Envío de documentos con firma manuscrita, OTP y certificado"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nueva solicitud
            </button>
          ) : undefined
        }
      />
      {loading ? (
        <p className="muted">Cargando…</p>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>Referencia</th>
                <th>Documento</th>
                <th>Estado</th>
                <th>Firmantes</th>
                <th>Hash original</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <code>{r.reference}</code>
                  </td>
                  <td>{r.title}</td>
                  <td>
                    <span className="badge">{STATUS_LABELS[r.status] ?? r.status}</span>
                  </td>
                  <td>
                    <ul className="signers-inline">
                      {r.signers.map((s) => (
                        <li key={s.id}>
                          {s.full_name} — {s.status}
                          {canWrite && s.status !== "firmado" && (
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() => resend(r.id, s.id)}
                            >
                              Reenviar
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="muted small">
                    <code>{r.original_hash.slice(0, 16)}…</code>
                  </td>
                  <td className="actions">
                    {r.status === "completado" && (
                      <>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() =>
                            api.download(
                              `/signatures/${r.id}/signed`,
                              `${r.reference}_signed.pdf`
                            )
                          }
                        >
                          PDF firmado
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() =>
                            api.download(
                              `/signatures/${r.id}/certificate`,
                              `${r.reference}_cert.pdf`
                            )
                          }
                        >
                          Certificado
                        </button>
                      </>
                    )}
                    {canWrite && !["completado", "cancelado"].includes(r.status) && (
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={() => cancel(r.id)}
                      >
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        title="Nueva solicitud de firma"
        open={open && !!canWrite}
        onClose={() => setOpen(false)}
        wide
        tall
      >
        <form onSubmit={create} className="form-grid modal-form-scroll">
          {error && <div className="alert alert-error form-grid-full">{error}</div>}

          <div className="form-grid-full">
            <span className="label-like">Documento</span>
            <div className="doc-source-toggle">
              <button
                type="button"
                className={`btn btn-sm ${docSource === "upload" ? "active" : ""}`}
                onClick={() => setDocSource("upload")}
              >
                Subir archivo
              </button>
              <button
                type="button"
                className={`btn btn-sm ${docSource === "existing" ? "active" : ""}`}
                onClick={() => setDocSource("existing")}
              >
                Ya subido
              </button>
            </div>
          </div>

          {docSource === "upload" ? (
            <div className="form-grid-full">
              <FileDropzone
                file={uploadFile}
                onFile={(f) => {
                  setUploadFile(f);
                  if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, ""));
                }}
              />
            </div>
          ) : (
            <label className="form-grid-full">
              Documento en biblioteca
              <select value={docId} onChange={(ev) => setDocId(ev.target.value)}>
                <option value="">Seleccionar…</option>
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.file_name} ({d.document_type})
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="form-grid-full">
            Título de la solicitud
            <input
              value={title}
              onChange={(ev) => setTitle(ev.target.value)}
              placeholder="Opcional — por defecto el nombre del archivo"
            />
          </label>

          <fieldset className="form-grid-full signature-signers-fieldset">
            <legend>Firmantes (orden de firma)</legend>
            {signers.map((s, i) => (
              <div key={i} className="signer-block form-grid-full">
                <div className="signer-block-header">
                  <strong>Firmante {s.sign_order}</strong>
                  {signers.length > 1 && (
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={() => removeSigner(i)}
                    >
                      Quitar
                    </button>
                  )}
                </div>
                <label>
                  Tipo
                  <select
                    value={s.kind}
                    onChange={(ev) => {
                      const next = [...signers];
                      next[i] = {
                        ...next[i],
                        kind: ev.target.value as "employee" | "external",
                      };
                      setSigners(next);
                    }}
                  >
                    <option value="employee">Empleado</option>
                    <option value="external">Firmante externo</option>
                  </select>
                </label>
                {s.kind === "employee" ? (
                  <label>
                    Empleado
                    <select
                      value={s.employee_id}
                      onChange={(ev) => {
                        const next = [...signers];
                        next[i] = { ...next[i], employee_id: ev.target.value };
                        setSigners(next);
                      }}
                    >
                      <option value="">Seleccionar…</option>
                      {employees.map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.full_name} ({e.id_document ?? "sin DNI"})
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <>
                    <label>
                      Nombre
                      <input
                        value={s.full_name}
                        onChange={(ev) => {
                          const next = [...signers];
                          next[i] = { ...next[i], full_name: ev.target.value };
                          setSigners(next);
                        }}
                      />
                    </label>
                    <label>
                      DNI/NIE
                      <input
                        value={s.id_document}
                        onChange={(ev) => {
                          const next = [...signers];
                          next[i] = {
                            ...next[i],
                            id_document: ev.target.value.toUpperCase(),
                          };
                          setSigners(next);
                        }}
                      />
                    </label>
                    <label>
                      Teléfono (WhatsApp)
                      <input
                        value={s.phone}
                        onChange={(ev) => {
                          const next = [...signers];
                          next[i] = { ...next[i], phone: ev.target.value };
                          setSigners(next);
                        }}
                      />
                    </label>
                    <label>
                      Email
                      <input
                        type="email"
                        value={s.email}
                        onChange={(ev) => {
                          const next = [...signers];
                          next[i] = { ...next[i], email: ev.target.value };
                          setSigners(next);
                        }}
                      />
                    </label>
                  </>
                )}
              </div>
            ))}
            <button type="button" className="btn btn-sm" onClick={addSigner}>
              + Añadir firmante
            </button>
          </fieldset>

          <p className="muted small form-grid-full">
            Se enviará un enlace por WhatsApp a cada firmante. Deberán validar DNI/NIE y un
            código OTP. Al completar todas las firmas se genera el PDF firmado y el certificado.
          </p>

          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setOpen(false)} disabled={saving}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Creando…" : "Crear y enviar"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
