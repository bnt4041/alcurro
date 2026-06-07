import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { DocumentDelivery } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import FileDropzone from "../components/FileDropzone";
import Modal from "../components/Modal";
import FilePreviewModal from "../components/FilePreviewModal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";
import { tableActionButtons, type TableAction } from "../lib/tableFormatters";

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

type SignatureRow = SignatureEnvelope & {
  status_label: string;
  hash_short: string;
};

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
  kind: "external",
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
  const canCreate = user && canModule(user.permissions, "create", "signatures");
  const canUpdate = user && canModule(user.permissions, "update", "signatures");
  const [previewPath, setPreviewPath] = useState<{ path: string; name: string } | null>(null);
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

    setSaving(true);
    try {
      if (docSource === "upload" && uploadFile) {
        const fd = new FormData();
        fd.append("file", uploadFile);
        fd.append("title", title || uploadFile.name);
        fd.append("signers_json", JSON.stringify(payloadSigners));
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

  const tableData = useMemo<SignatureRow[]>(
    () =>
      rows.map((r) => ({
        ...r,
        status_label: STATUS_LABELS[r.status] ?? r.status,
        hash_short: `${r.original_hash.slice(0, 16)}…`,
      })),
    [rows]
  );

  const columns = useMemo<DataTableColumn<SignatureRow>[]>(() => {
    const cols: DataTableColumn<SignatureRow>[] = [
      {
        title: "Referencia",
        field: "reference",
        headerFilter: "input",
        formatter: (c) => `<code>${String(c.getValue())}</code>`,
        minWidth: 120,
      },
      { title: "Documento", field: "title", headerFilter: "input", minWidth: 160 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", ...Object.fromEntries(Object.values(STATUS_LABELS).map((v) => [v, v])) },
        },
        formatter: (c) => `<span class="badge">${String(c.getValue())}</span>`,
        width: 120,
      },
      {
        title: "Firmantes",
        field: "signers",
        headerFilter: false,
        download: false,
        minWidth: 220,
        formatter: (cell) => {
          const r = cell.getRow().getData() as SignatureRow;
          return r.signers
            .map((s) => {
              const resendBtn =
                canUpdate && s.status !== "firmado"
                  ? `<button type="button" class="btn btn-sm" data-action="resend" data-signer-id="${s.id}">Reenviar</button>`
                  : "";
              return `<div class="signers-inline-item">${s.full_name} — ${s.status} ${resendBtn}</div>`;
            })
            .join("");
        },
      },
      {
        title: "Hash original",
        field: "hash_short",
        headerFilter: "input",
        formatter: (c) => `<code class="muted small">${String(c.getValue())}</code>`,
        width: 130,
      },
    ];
    if (canUpdate) {
      cols.push({
        title: "",
        field: "id",
        headerFilter: false,
        download: false,
        width: 200,
        formatter: (cell) => {
          const r = cell.getRow().getData() as SignatureRow;
          const actions: TableAction[] = [];
          if (r.status === "completado") {
            actions.push({ id: "preview", label: "Ver" });
            actions.push({ id: "signed", label: "PDF firmado" });
            actions.push({ id: "certificate", label: "Certificado" });
          }
          if (!["completado", "cancelado"].includes(r.status)) {
            actions.push({ id: "cancel", label: "Cancelar", className: "btn-danger" });
          }
          return actions.length ? tableActionButtons(actions) : "";
        },
      });
    }
    return cols;
  }, [canUpdate]);

  const resend = async (envelopeId: string, signerId: string) => {
    const data = await api.post<{ message: string; whatsapp_sent?: boolean; detail?: string }>(
      `/signatures/${envelopeId}/signers/${signerId}/resend`,
      {}
    );
    if (data.whatsapp_sent === false) {
      alert(data.detail ? `${data.message}\n\n${data.detail}` : data.message);
      return;
    }
    alert(data.message || "Enlace reenviado por WhatsApp");
  };

  const onCellAction = (action: string, row: SignatureRow, ctx?: { signerId?: string }) => {
    if (action === "resend" && ctx?.signerId) {
      void resend(row.id, ctx.signerId);
      return;
    }
    if (action === "preview") {
      setPreviewPath({ path: `/signatures/${row.id}/signed`, name: `${row.reference}_signed.pdf` });
      return;
    }
    if (action === "signed") {
      void api.download(`/signatures/${row.id}/signed`, `${row.reference}_signed.pdf`);
      return;
    }
    if (action === "certificate") {
      void api.download(`/signatures/${row.id}/certificate`, `${row.reference}_cert.pdf`);
      return;
    }
    if (action === "cancel") void cancel(row.id);
  };

  return (
    <>
      <FilePreviewModal
        apiPath={previewPath?.path ?? null}
        filename={previewPath?.name}
        onClose={() => setPreviewPath(null)}
      />
      <PageHeader
        title="Firmas"
        subtitle="Envío de documentos con firma manuscrita, OTP y certificado"
        action={
          canCreate ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nueva solicitud
            </button>
          ) : undefined
        }
      />
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="firmas"
        emptyMessage="Sin solicitudes de firma"
        onCellAction={onCellAction}
      />

      <Modal
        title="Nueva solicitud de firma"
        open={open && !!canCreate}
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
                    <option value="external">Firmante externo</option>
                    <option value="employee">Empleado</option>
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
                        placeholder="624230960 o +34 624 230 960"
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
