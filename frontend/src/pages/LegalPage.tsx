import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";
import { tableActionButtons } from "../lib/tableFormatters";

export interface LegalDocument {
  id: string;
  tenant_id: string;
  code: string;
  title: string;
  body: string;
  version: number;
  is_active: boolean;
  is_required: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

const emptyDoc = (): Partial<LegalDocument> => ({
  code: "",
  title: "",
  body: "",
  is_active: true,
  is_required: true,
  sort_order: 0,
});

export default function LegalPage() {
  const { user } = useAuth();
  const canWrite = user && canModule(user.permissions, "write", "legal");
  const [rows, setRows] = useState<LegalDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<LegalDocument | null>(null);
  const [form, setForm] = useState(emptyDoc());
  const [bumpVersion, setBumpVersion] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<LegalDocument | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<LegalDocument[]>("/legal/documents"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyDoc());
    setBumpVersion(false);
    setOpen(true);
  };

  const openEdit = (row: LegalDocument) => {
    setEditing(row);
    setForm({ ...row });
    setBumpVersion(false);
    setOpen(true);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (editing) {
        const body: Record<string, unknown> = {
          title: form.title,
          body: form.body,
          is_active: form.is_active,
          is_required: form.is_required,
          sort_order: form.sort_order,
          bump_version: bumpVersion,
        };
        await api.patch(`/legal/documents/${editing.id}`, body);
      } else {
        await api.post("/legal/documents", form);
      }
      setOpen(false);
      load();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar este texto legal?")) return;
    await api.delete(`/legal/documents/${id}`);
    load();
  };

  type LegalRow = LegalDocument & {
    version_label: string;
    required_label: string;
    active_label: string;
  };

  const tableData = useMemo<LegalRow[]>(
    () =>
      rows.map((r) => ({
        ...r,
        version_label: `v${r.version}`,
        required_label: r.is_required ? "Sí" : "No",
        active_label: r.is_active ? "Sí" : "No",
      })),
    [rows]
  );

  const columns = useMemo<DataTableColumn<LegalRow>[]>(() => {
    const cols: DataTableColumn<LegalRow>[] = [
      {
        title: "Código",
        field: "code",
        headerFilter: "input",
        formatter: (c) => `<code>${c.getValue()}</code>`,
        width: 120,
      },
      { title: "Título", field: "title", headerFilter: "input", minWidth: 180 },
      { title: "Versión", field: "version_label", headerFilter: "input", width: 90 },
      {
        title: "Obligatorio",
        field: "required_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", Sí: "Sí", No: "No" } },
        width: 100,
      },
      {
        title: "Activo",
        field: "active_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", Sí: "Sí", No: "No" } },
        width: 90,
      },
    ];
    if (canWrite) {
      cols.push({
        title: "",
        field: "id",
        headerFilter: false,
        sorter: false,
        download: false,
        width: 200,
        formatter: () =>
          tableActionButtons([
            { id: "view", label: "Ver" },
            { id: "edit", label: "Editar" },
            { id: "delete", label: "Borrar", className: "btn-danger" },
          ]),
      });
    }
    return cols;
  }, [canWrite]);

  const onCellAction = (action: string, row: LegalRow) => {
    if (action === "view") setPreview(row);
    else if (action === "edit") openEdit(row);
    else if (action === "delete") remove(row.id);
  };

  return (
    <>
      <PageHeader
        title="Legal"
        subtitle="Textos que el empleado debe leer y aceptar"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nuevo texto
            </button>
          ) : undefined
        }
      />
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="textos_legales"
        height="480px"
        onCellAction={onCellAction}
      />

      <Modal title={preview?.title ?? ""} open={!!preview} onClose={() => setPreview(null)}>
        {preview && (
          <div className="legal-body">
            <p className="muted small">
              Versión {preview.version} · Código <code>{preview.code}</code>
            </p>
            <div className="legal-text">{preview.body}</div>
          </div>
        )}
      </Modal>

      <Modal
        title={editing ? "Editar texto legal" : "Nuevo texto legal"}
        open={open && !!canWrite}
        onClose={() => setOpen(false)}
      >
        <form onSubmit={save} className="form-grid">
          {error && <div className="alert alert-error form-grid-full">{error}</div>}
          {!editing && (
            <label>
              Código interno
              <input
                required
                placeholder="privacy"
                value={form.code ?? ""}
                onChange={(ev) => setForm({ ...form, code: ev.target.value })}
              />
            </label>
          )}
          {editing && (
            <label>
              Código
              <input value={editing.code} readOnly disabled />
            </label>
          )}
          <label>
            Título
            <input
              required
              value={form.title ?? ""}
              onChange={(ev) => setForm({ ...form, title: ev.target.value })}
            />
          </label>
          <label className="form-grid-full">
            Contenido
            <textarea
              required
              rows={10}
              value={form.body ?? ""}
              onChange={(ev) => setForm({ ...form, body: ev.target.value })}
            />
          </label>
          <label>
            Orden
            <input
              type="number"
              value={form.sort_order ?? 0}
              onChange={(ev) =>
                setForm({ ...form, sort_order: parseInt(ev.target.value, 10) || 0 })
              }
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.is_required ?? true}
              onChange={(ev) => setForm({ ...form, is_required: ev.target.checked })}
            />
            Obligatorio para empleados
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={(ev) => setForm({ ...form, is_active: ev.target.checked })}
            />
            Activo
          </label>
          {editing && (
            <label className="checkbox form-grid-full">
              <input
                type="checkbox"
                checked={bumpVersion}
                onChange={(ev) => setBumpVersion(ev.target.checked)}
              />
              Nueva versión (exigirá volver a aceptar si cambias el contenido)
            </label>
          )}
          <div className="form-actions form-grid-full">
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
