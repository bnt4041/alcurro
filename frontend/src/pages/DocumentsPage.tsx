import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, buildQuery } from "../api/client";
import type { DocumentDelivery } from "../api/types";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule } from "../lib/permissions";

export default function DocumentsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const canWrite = user && canModule(user.permissions, "write", "documents");
  const canAdmin = user && canModule(user.permissions, "admin", "documents");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [rows, setRows] = useState<DocumentDelivery[]>([]);
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState({
    employee_id: "",
    document_type: "nomina",
    file: null as File | null,
  });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const path = buildQuery({
      q: search || undefined,
      document_type: typeFilter || undefined,
    });
    setRows(await api.get<DocumentDelivery[]>(`/documents${path}`));
  }, [search, typeFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const upload = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.file || !form.employee_id) return;
    setUploading(true);
    setMsg("");
    try {
      const fd = new FormData();
      fd.append("employee_id", form.employee_id);
      fd.append("document_type", form.document_type);
      fd.append("file", form.file);
      await api.upload<DocumentDelivery>("/documents/upload", fd);
      setMsg("Documento subido correctamente");
      setForm({ employee_id: "", document_type: "nomina", file: null });
      load();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setUploading(false);
    }
  };

  const sendWhatsapp = async (id: string) => {
    try {
      await api.post(`/documents/${id}/send-whatsapp`, {});
      setMsg("Enviado por WhatsApp");
      load();
    } catch (err) {
      setMsg(String(err));
    }
  };

  const remove = async (id: string) => {
    if (!confirm("¿Eliminar documento?")) return;
    await api.delete(`/documents/${id}`);
    load();
  };

  return (
    <>
      <PageHeader
        title="Documentos"
        subtitle="Nóminas, contratos y envío por WhatsApp"
      />
      <TableToolbar
        search={search}
        onSearchChange={setSearch}
        onSubmit={load}
        placeholder="Nombre archivo o tipo…"
        filters={[
          {
            label: "Tipo",
            value: typeFilter,
            onChange: setTypeFilter,
            options: [
              { value: "nomina", label: "Nómina" },
              { value: "contrato", label: "Contrato" },
              { value: "otro", label: "Otro" },
            ],
          },
        ]}
      />
      {canWrite && (
      <section className="card">
        <h3>Subir documento</h3>
        {msg && (
          <div
            className={`alert ${msg.includes("correctamente") || msg.includes("Enviado") ? "alert-ok" : "alert-error"}`}
          >
            {msg}
          </div>
        )}
        <form onSubmit={upload} className="form-grid form-inline-upload">
          <label>
            Empleado
            <select
              required
              value={form.employee_id}
              onChange={(ev) => setForm({ ...form, employee_id: ev.target.value })}
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
            Tipo
            <select
              value={form.document_type}
              onChange={(ev) =>
                setForm({ ...form, document_type: ev.target.value })
              }
            >
              <option value="nomina">Nómina</option>
              <option value="contrato">Contrato</option>
              <option value="otro">Otro</option>
            </select>
          </label>
          <label>
            Archivo
            <input
              type="file"
              required
              onChange={(ev) =>
                setForm({ ...form, file: ev.target.files?.[0] ?? null })
              }
            />
          </label>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={uploading}
          >
            {uploading ? "Subiendo…" : "Subir"}
          </button>
        </form>
      </section>
      )}
      <div className="table-wrap card">
        <table>
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Empleado</th>
              <th>Tipo</th>
              <th>Enviado WA</th>
              <th>Acuse</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td>{d.file_name}</td>
                <td>{byId(d.employee_id)}</td>
                <td>{d.document_type}</td>
                <td>
                  {d.sent_at
                    ? new Date(d.sent_at).toLocaleString("es-ES")
                    : "No"}
                </td>
                <td>
                  {d.acknowledged_at
                    ? new Date(d.acknowledged_at).toLocaleString("es-ES")
                    : "Pendiente"}
                </td>
                <td className="actions">
                  {canWrite && (
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={() => sendWhatsapp(d.id)}
                  >
                    Enviar WA
                  </button>
                  )}
                  {canAdmin && (
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    onClick={() => remove(d.id)}
                  >
                    Borrar
                  </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
