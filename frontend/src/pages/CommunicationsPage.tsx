import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Communication } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";
import { tableActionButtons, type TableAction } from "../lib/tableFormatters";

interface OrgItem {
  id: string;
  name: string;
}

interface ExternalRow {
  full_name: string;
  phone: string;
  email: string;
  id_document: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Borrador",
  sending: "Enviando",
  sent: "Enviada",
  cancelled: "Cancelada",
};
const REC_STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  sent: "Enviado",
  read: "Leído",
  signed: "Firmado",
  cancelled: "Cancelado",
  failed: "Error",
};

const emptyExternal = (): ExternalRow => ({
  full_name: "",
  phone: "",
  email: "",
  id_document: "",
});

export default function CommunicationsPage() {
  const { user } = useAuth();
  const { notify, success, error: toastError } = useToast();
  const { employees } = useEmployees();

  const canCreate = !!user && canModule(user.permissions, "write", "communications");

  const [rows, setRows] = useState<Communication[]>([]);
  const [departments, setDepartments] = useState<OrgItem[]>([]);
  const [workCenters, setWorkCenters] = useState<OrgItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Create modal
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [mode, setMode] = useState<"open" | "signature">("open");
  const [files, setFiles] = useState<File[]>([]);
  const [companyAll, setCompanyAll] = useState(false);
  const [deptIds, setDeptIds] = useState<string[]>([]);
  const [wcIds, setWcIds] = useState<string[]>([]);
  const [supIds, setSupIds] = useState<string[]>([]);
  const [empIds, setEmpIds] = useState<string[]>([]);
  const [externals, setExternals] = useState<ExternalRow[]>([]);

  // Detail modal
  const [detail, setDetail] = useState<Communication | null>(null);
  const [addEmpIds, setAddEmpIds] = useState<string[]>([]);
  const [addExternals, setAddExternals] = useState<ExternalRow[]>([]);

  const supervisors = useMemo(() => {
    const ids = new Set(
      employees.map((e) => e.supervisor_id).filter((x): x is string => !!x)
    );
    return employees.filter((e) => ids.has(e.id));
  }, [employees]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [comms, deps, wcs] = await Promise.all([
        api.get<Communication[]>("/communications"),
        api.get<OrgItem[]>("/org/departments").catch(() => []),
        api.get<OrgItem[]>("/org/work-centers").catch(() => []),
      ]);
      setRows(comms);
      setDepartments(deps);
      setWorkCenters(wcs);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const resetForm = () => {
    setTitle("");
    setBody("");
    setMode("open");
    setFiles([]);
    setCompanyAll(false);
    setDeptIds([]);
    setWcIds([]);
    setSupIds([]);
    setEmpIds([]);
    setExternals([]);
    setError("");
  };

  const openCreate = () => {
    resetForm();
    setOpen(true);
  };

  const audiencePayload = () => ({
    company: companyAll,
    department_ids: deptIds,
    work_center_ids: wcIds,
    supervisor_ids: supIds,
    employee_ids: empIds,
  });

  const cleanExternals = (list: ExternalRow[]) =>
    list
      .filter((e) => e.full_name.trim())
      .map((e) => ({
        full_name: e.full_name.trim(),
        phone: e.phone.trim() || null,
        email: e.email.trim() || null,
        id_document: e.id_document.trim() || null,
      }));

  const create = async (ev: FormEvent, sendNow: boolean) => {
    ev.preventDefault();
    setError("");
    if (!title.trim() || !body.trim()) {
      setError("Indica un título y un texto.");
      return;
    }
    const ext = cleanExternals(externals);
    const hasAudience =
      companyAll ||
      deptIds.length ||
      wcIds.length ||
      supIds.length ||
      empIds.length ||
      ext.length;
    if (!hasAudience) {
      setError("Selecciona al menos un destinatario.");
      return;
    }
    if (mode === "signature" && ext.some((e) => !e.id_document || !e.phone)) {
      setError("Los externos con firma necesitan DNI/NIE y teléfono.");
      return;
    }
    try {
      setSaving(true);
      const created = await api.post<Communication>("/communications", {
        title: title.trim(),
        body,
        mode,
        audience: audiencePayload(),
        externals: ext,
      });
      for (const f of files) {
        const form = new FormData();
        form.append("file", f);
        await api.upload(`/communications/${created.id}/attachments`, form);
      }
      if (sendNow) {
        await api.post(`/communications/${created.id}/send`, {});
        success("Comunicación enviada");
      } else {
        success("Borrador creado");
      }
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear la comunicación");
    } finally {
      setSaving(false);
    }
  };

  const sendExisting = async (id: string) => {
    try {
      await api.post(`/communications/${id}/send`, {});
      success("Comunicación enviada");
      await load();
      if (detail?.id === id) await openDetail(id);
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Error al enviar");
    }
  };

  const cancelComm = async (id: string) => {
    if (!window.confirm("¿Cancelar esta comunicación? Las firmas pendientes se anularán.")) return;
    try {
      await api.post(`/communications/${id}/cancel`, { reason: "Cancelada desde el panel" });
      notify("Comunicación cancelada", "info");
      await load();
      if (detail?.id === id) await openDetail(id);
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Error al cancelar");
    }
  };

  const openDetail = async (id: string) => {
    const d = await api.get<Communication>(`/communications/${id}`);
    setDetail(d);
    setAddEmpIds([]);
    setAddExternals([]);
  };

  const addRecipients = async () => {
    if (!detail) return;
    const ext = cleanExternals(addExternals);
    if (!addEmpIds.length && !ext.length) {
      toastError("Selecciona empleados o añade externos.");
      return;
    }
    try {
      await api.post(`/communications/${detail.id}/recipients`, {
        audience: { employee_ids: addEmpIds },
        externals: ext,
      });
      success("Destinatarios añadidos");
      await openDetail(detail.id);
      await load();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Error al añadir destinatarios");
    }
  };

  const columns = useMemo<DataTableColumn<Communication>[]>(() => {
    const cols: DataTableColumn<Communication>[] = [
      { title: "Título", field: "title", headerFilter: "input", minWidth: 200 },
      {
        title: "Modo",
        field: "mode",
        width: 120,
        formatter: (c) =>
          c.getValue() === "signature"
            ? `<span class="badge">Con firma</span>`
            : `<span class="badge">Abierto</span>`,
      },
      {
        title: "Estado",
        field: "status",
        width: 120,
        formatter: (c) => `<span class="badge">${STATUS_LABELS[String(c.getValue())] ?? c.getValue()}</span>`,
      },
      {
        title: "Destinatarios",
        field: "recipient_count",
        width: 200,
        headerFilter: false,
        formatter: (cell) => {
          const r = cell.getRow().getData() as Communication;
          const parts = [`${r.recipient_count} dest.`, `${r.sent_count} enviados`];
          if (r.mode === "signature") parts.push(`${r.signed_count} firmados`);
          return `<span class="muted small">${parts.join(" · ")}</span>`;
        },
      },
      {
        title: "Creada",
        field: "created_at",
        width: 150,
        formatter: (c) => new Date(String(c.getValue())).toLocaleDateString("es-ES"),
      },
    ];
    cols.push({
      title: "",
      field: "id",
      headerFilter: false,
      download: false,
      width: 220,
      formatter: (cell) => {
        const r = cell.getRow().getData() as Communication;
        const actions: TableAction[] = [{ id: "view", label: "Ver" }];
        if (canCreate && r.status === "draft") actions.push({ id: "send", label: "Enviar" });
        if (canCreate && r.status !== "cancelled")
          actions.push({ id: "cancel", label: "Cancelar", className: "btn-danger" });
        return tableActionButtons(actions);
      },
    });
    return cols;
  }, [canCreate]);

  const onCellAction = (action: string, row: Communication) => {
    if (action === "view") void openDetail(row.id);
    if (action === "send") void sendExisting(row.id);
    if (action === "cancel") void cancelComm(row.id);
  };

  const multiSelect = (
    label: string,
    options: { id: string; name: string }[],
    value: string[],
    onChange: (ids: string[]) => void
  ) => (
    <label className="form-grid-full">
      {label}
      <select
        multiple
        value={value}
        onChange={(e) =>
          onChange(Array.from(e.target.selectedOptions).map((o) => o.value))
        }
        style={{ minHeight: 90 }}
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );

  const externalEditor = (
    list: ExternalRow[],
    setList: (l: ExternalRow[]) => void
  ) => (
    <div className="form-grid-full">
      <div className="row-between">
        <strong>Personas externas</strong>
        <button type="button" className="btn btn-sm" onClick={() => setList([...list, emptyExternal()])}>
          + Añadir externo
        </button>
      </div>
      {list.map((ex, i) => (
        <div key={i} className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr auto", gap: 6, marginTop: 6 }}>
          <input placeholder="Nombre" value={ex.full_name}
            onChange={(e) => setList(list.map((x, j) => (j === i ? { ...x, full_name: e.target.value } : x)))} />
          <input placeholder="Teléfono" value={ex.phone}
            onChange={(e) => setList(list.map((x, j) => (j === i ? { ...x, phone: e.target.value } : x)))} />
          <input placeholder="Email" value={ex.email}
            onChange={(e) => setList(list.map((x, j) => (j === i ? { ...x, email: e.target.value } : x)))} />
          <input placeholder="DNI/NIE" value={ex.id_document}
            onChange={(e) => setList(list.map((x, j) => (j === i ? { ...x, id_document: e.target.value } : x)))} />
          <button type="button" className="btn btn-sm btn-danger" onClick={() => setList(list.filter((_, j) => j !== i))}>×</button>
        </div>
      ))}
    </div>
  );

  return (
    <>
      <PageHeader
        title="Comunicaciones"
        subtitle="Envía un texto (y adjuntos) a tu plantilla, abierto o con firma"
        action={
          canCreate ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nueva comunicación
            </button>
          ) : undefined
        }
      />

      <DataTable
        data={rows}
        columns={columns}
        loading={loading}
        exportFilename="comunicaciones"
        emptyMessage="Sin comunicaciones"
        onCellAction={onCellAction}
      />

      {/* Crear */}
      <Modal title="Nueva comunicación" open={open && canCreate} onClose={() => setOpen(false)} wide tall>
        <form onSubmit={(e) => create(e, false)} className="form-grid modal-form-scroll">
          {error && <div className="alert alert-error form-grid-full">{error}</div>}

          <label className="form-grid-full">
            Título
            <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={255} />
          </label>
          <label className="form-grid-full">
            Texto del comunicado
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} />
          </label>

          <label className="form-grid-full">
            Adjuntos (opcional)
            <input
              type="file"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            {files.length > 0 && (
              <span className="muted small">{files.map((f) => f.name).join(", ")}</span>
            )}
          </label>

          <label className="form-grid-full">
            Modo
            <select value={mode} onChange={(e) => setMode(e.target.value as "open" | "signature")}>
              <option value="open">Abierto (solo envío por WhatsApp)</option>
              <option value="signature">Con firma (OTP + firma + trazabilidad)</option>
            </select>
          </label>

          <div className="form-grid-full">
            <strong>Audiencia</strong>
            <label className="checkbox" style={{ marginTop: 6 }}>
              <input type="checkbox" checked={companyAll} onChange={(e) => setCompanyAll(e.target.checked)} />
              Toda la empresa
            </label>
          </div>
          {!companyAll && (
            <>
              {multiSelect("Departamentos", departments, deptIds, setDeptIds)}
              {multiSelect("Centros de trabajo", workCenters, wcIds, setWcIds)}
              {multiSelect(
                "Supervisores (se envía a su equipo)",
                supervisors.map((e) => ({ id: e.id, name: e.full_name })),
                supIds,
                setSupIds
              )}
              {multiSelect(
                "Empleados concretos",
                employees.map((e) => ({ id: e.id, name: e.full_name })),
                empIds,
                setEmpIds
              )}
            </>
          )}
          {externalEditor(externals, setExternals)}

          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setOpen(false)}>Cancelar</button>
            <button type="submit" className="btn" disabled={saving}>Guardar borrador</button>
            <button type="button" className="btn btn-primary" disabled={saving} onClick={(e) => create(e, true)}>
              {saving ? "Enviando…" : "Crear y enviar"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal
        title={detail ? detail.title : "Comunicación"}
        open={!!detail}
        onClose={() => setDetail(null)}
        wide
        tall
      >
        {detail && (
          <div className="modal-form-scroll">
            <p className="muted small">
              {STATUS_LABELS[detail.status] ?? detail.status} ·{" "}
              {detail.mode === "signature" ? "Con firma" : "Abierto"} ·{" "}
              {detail.recipient_count} destinatarios
            </p>
            <p style={{ whiteSpace: "pre-wrap" }}>{detail.body}</p>
            {detail.attachments && detail.attachments.length > 0 && (
              <p className="muted small">Adjuntos: {detail.attachments.map((a) => a.file_name).join(", ")}</p>
            )}

            <h4>Destinatarios</h4>
            <table className="table table-sm">
              <thead>
                <tr><th>Nombre</th><th>Tipo</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {(detail.recipients ?? []).map((r) => (
                  <tr key={r.id}>
                    <td>{r.full_name}{r.error ? <span className="muted small"> — {r.error}</span> : null}</td>
                    <td>{r.is_external ? "Externo" : "Empleado"}</td>
                    <td><span className="badge">{REC_STATUS_LABELS[r.status] ?? r.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>

            {canCreate && detail.status !== "cancelled" && (
              <div className="form-grid-full" style={{ marginTop: 16 }}>
                <h4>Añadir destinatarios</h4>
                {multiSelect(
                  "Empleados",
                  employees.map((e) => ({ id: e.id, name: e.full_name })),
                  addEmpIds,
                  setAddEmpIds
                )}
                {externalEditor(addExternals, setAddExternals)}
                <div className="form-actions">
                  <button type="button" className="btn" onClick={addRecipients}>Añadir y enviar a los nuevos</button>
                </div>
              </div>
            )}

            <div className="form-actions" style={{ marginTop: 16 }}>
              {canCreate && detail.status === "draft" && (
                <button type="button" className="btn btn-primary" onClick={() => sendExisting(detail.id)}>Enviar ahora</button>
              )}
              {canCreate && detail.status !== "cancelled" && (
                <button type="button" className="btn btn-danger" onClick={() => cancelComm(detail.id)}>Cancelar comunicación</button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
