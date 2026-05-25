import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, buildQuery } from "../api/client";
import type {
  BulkPayrollResponse,
  DocumentDelivery,
  DocumentNotificationSettings,
  DocumentTag,
  DocumentType,
  ExpiryNotificationRunResult,
} from "../api/types";
import PageHeader from "../components/PageHeader";
import TableToolbar from "../components/TableToolbar";
import { useAuth } from "../context/AuthContext";
import { useEmployees } from "../hooks/useEmployees";
import { canModule, hasPerm } from "../lib/permissions";

type Tab = "list" | "upload" | "catalog" | "bulk" | "notify";

export default function DocumentsPage() {
  const { user } = useAuth();
  const { employees, byId } = useEmployees();
  const canWrite = user && canModule(user.permissions, "write", "documents");
  const canCreate = user && canModule(user.permissions, "create", "documents");
  const canBulk = user && hasPerm(user.permissions, "documents.bulk");

  const [tab, setTab] = useState<Tab>("list");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [expiredOnly, setExpiredOnly] = useState(false);
  const [rows, setRows] = useState<DocumentDelivery[]>([]);
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [tags, setTags] = useState<DocumentTag[]>([]);
  const [msg, setMsg] = useState("");

  const [uploading, setUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    target: "employee" as "employee" | "company",
    employee_id: "",
    document_type_id: "",
    title: "",
    expires_at: "",
    tag_ids: [] as string[],
    file: null as File | null,
  });

  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState<BulkPayrollResponse | null>(null);
  const [bulkFiles, setBulkFiles] = useState<FileList | null>(null);
  const [bulkExpires, setBulkExpires] = useState("");

  const [newType, setNewType] = useState({ code: "", name: "", description: "" });
  const [newTag, setNewTag] = useState({ name: "", color: "#2563eb" });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [downloading, setDownloading] = useState(false);

  const [notifySettings, setNotifySettings] =
    useState<DocumentNotificationSettings | null>(null);
  const [notifyForm, setNotifyForm] = useState({
    enabled: false,
    days_before: "30,7,1,0",
    channel_whatsapp: true,
    channel_email: true,
    notify_employee: true,
    notify_managers: true,
    extra_emails: "",
  });
  const [notifyRunning, setNotifyRunning] = useState(false);
  const [notifyRunResult, setNotifyRunResult] =
    useState<ExpiryNotificationRunResult | null>(null);

  const loadMeta = useCallback(async () => {
    const [t, g] = await Promise.all([
      api.get<DocumentType[]>("/documents/types"),
      api.get<DocumentTag[]>("/documents/tags"),
    ]);
    setTypes(t);
    setTags(g);
  }, []);

  const load = useCallback(async () => {
    const matchedType = types.find((x) => x.code === typeFilter);
    const path = buildQuery({
      q: search || undefined,
      document_type: matchedType ? undefined : typeFilter || undefined,
      document_type_id: matchedType?.id,
      tag_id: tagFilter || undefined,
      expired_only: expiredOnly ? "true" : undefined,
    });
    setRows(await api.get<DocumentDelivery[]>(`/documents${path}`));
  }, [search, typeFilter, tagFilter, expiredOnly, types]);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    if (tab === "list") load();
  }, [tab, load]);

  const loadNotifySettings = useCallback(async () => {
    const s = await api.get<DocumentNotificationSettings>(
      "/documents/notification-settings"
    );
    setNotifySettings(s);
    setNotifyForm({
      enabled: s.enabled,
      days_before: s.days_before.join(","),
      channel_whatsapp: s.channel_whatsapp,
      channel_email: s.channel_email,
      notify_employee: s.notify_employee,
      notify_managers: s.notify_managers,
      extra_emails: s.extra_emails.join(", "),
    });
  }, []);

  useEffect(() => {
    if (tab === "notify" && canWrite) loadNotifySettings();
  }, [tab, canWrite, loadNotifySettings]);

  const upload = async (e: FormEvent) => {
    e.preventDefault();
    if (!uploadForm.file) return;
    if (uploadForm.target === "employee" && !uploadForm.employee_id) return;
    setUploading(true);
    setMsg("");
    try {
      const fd = new FormData();
      if (uploadForm.target === "employee") {
        fd.append("employee_id", uploadForm.employee_id);
      } else if (user?.company_id) {
        fd.append("company_id", user.company_id);
      }
      if (uploadForm.document_type_id) {
        fd.append("document_type_id", uploadForm.document_type_id);
      } else {
        const code = types[0]?.code ?? "otro";
        fd.append("document_type", code);
      }
      if (uploadForm.title) fd.append("title", uploadForm.title);
      if (uploadForm.expires_at) fd.append("expires_at", uploadForm.expires_at);
      if (uploadForm.tag_ids.length) {
        fd.append("tag_ids", JSON.stringify(uploadForm.tag_ids));
      }
      fd.append("file", uploadForm.file);
      await api.upload<DocumentDelivery>("/documents/upload", fd);
      setMsg("Documento subido correctamente");
      setUploadForm({
        target: "employee",
        employee_id: "",
        document_type_id: types.find((t) => t.code === "nomina")?.id ?? "",
        title: "",
        expires_at: "",
        tag_ids: [],
        file: null,
      });
      setTab("list");
      load();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setUploading(false);
    }
  };

  const bulkUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!bulkFiles?.length || !user?.company_id) return;
    setBulkUploading(true);
    setMsg("");
    setBulkResult(null);
    try {
      const fd = new FormData();
      fd.append("company_id", user.company_id);
      const nomina = types.find((t) => t.code === "nomina");
      if (nomina) fd.append("document_type_id", nomina.id);
      else fd.append("document_type", "nomina");
      if (bulkExpires) fd.append("expires_at", bulkExpires);
      for (let i = 0; i < bulkFiles.length; i++) {
        fd.append("files", bulkFiles[i]);
      }
      const res = await api.upload<BulkPayrollResponse>(
        "/documents/bulk-payrolls",
        fd
      );
      setBulkResult(res);
      setMsg(
        `Procesadas ${res.total_pages} páginas: ${res.assigned} asignadas, ${res.skipped} omitidas, ${res.errors} errores`
      );
      load();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setBulkUploading(false);
    }
  };

  const createType = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/documents/types", newType);
      setNewType({ code: "", name: "", description: "" });
      loadMeta();
      setMsg("Tipología creada");
    } catch (err) {
      setMsg(String(err));
    }
  };

  const createTag = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/documents/tags", newTag);
      setNewTag({ name: "", color: "#2563eb" });
      loadMeta();
      setMsg("Etiqueta creada");
    } catch (err) {
      setMsg(String(err));
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
    try {
      await api.delete(`/documents/${id}`);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      setMsg("Documento eliminado");
      load();
    } catch (err) {
      setMsg(String(err));
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === rows.length) setSelected(new Set());
    else setSelected(new Set(rows.map((r) => r.id)));
  };

  const downloadOne = (id: string, fileName: string) => {
    api.download(`/documents/${id}/download`, fileName);
  };

  const downloadZip = async (useSelection: boolean) => {
    setDownloading(true);
    setMsg("");
    try {
      const matchedType = types.find((x) => x.code === typeFilter);
      if (useSelection && selected.size > 0) {
        const ids = [...selected].join(",");
        await api.download(
          `/documents/download-zip?ids=${encodeURIComponent(ids)}`,
          `documentos_${new Date().toISOString().slice(0, 10)}.zip`
        );
      } else {
        const path = buildQuery({
          document_type: matchedType ? undefined : typeFilter || undefined,
          document_type_id: matchedType?.id,
          tag_id: tagFilter || undefined,
          expired_only: expiredOnly ? "true" : undefined,
          q: search || undefined,
        });
        await api.download(
          `/documents/download-zip${path}`,
          `documentos_${new Date().toISOString().slice(0, 10)}.zip`
        );
      }
      setMsg("ZIP descargado");
    } catch (err) {
      setMsg(String(err));
    } finally {
      setDownloading(false);
    }
  };

  const saveNotifySettings = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const days = notifyForm.days_before
        .split(",")
        .map((x) => parseInt(x.trim(), 10))
        .filter((n) => !Number.isNaN(n) && n >= 0);
      const extra = notifyForm.extra_emails
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
      const s = await api.put<DocumentNotificationSettings>(
        "/documents/notification-settings",
        {
          enabled: notifyForm.enabled,
          days_before: days.length ? days : [30, 7, 1],
          channel_whatsapp: notifyForm.channel_whatsapp,
          channel_email: notifyForm.channel_email,
          notify_employee: notifyForm.notify_employee,
          notify_managers: notifyForm.notify_managers,
          extra_emails: extra,
        }
      );
      setNotifySettings(s);
      setMsg("Configuración de avisos guardada");
    } catch (err) {
      setMsg(String(err));
    }
  };

  const runNotifyNow = async (dryRun: boolean) => {
    setNotifyRunning(true);
    setNotifyRunResult(null);
    try {
      const res = await api.post<ExpiryNotificationRunResult>(
        `/documents/run-expiry-notifications?dry_run=${dryRun}`,
        {}
      );
      setNotifyRunResult(res);
      setMsg(
        dryRun
          ? `Simulación: ${res.sent} avisos pendientes, ${res.skipped} ya enviados`
          : `Enviados ${res.sent} avisos (${res.errors} errores)`
      );
    } catch (err) {
      setMsg(String(err));
    } finally {
      setNotifyRunning(false);
    }
  };

  const typeOptions = types.map((t) => ({ value: t.code, label: t.name }));
  const tagOptions = tags.map((t) => ({ value: t.id, label: t.name }));

  return (
    <>
      <PageHeader
        title="Documentos"
        subtitle="Nóminas, contratos, tipologías, etiquetas y envío por WhatsApp"
      />

      <div className="tabs">
        <button
          type="button"
          className={tab === "list" ? "tab active" : "tab"}
          onClick={() => setTab("list")}
        >
          Listado
        </button>
        {canCreate && (
          <button
            type="button"
            className={tab === "upload" ? "tab active" : "tab"}
            onClick={() => setTab("upload")}
          >
            Subir
          </button>
        )}
        {canWrite && (
          <button
            type="button"
            className={tab === "catalog" ? "tab active" : "tab"}
            onClick={() => setTab("catalog")}
          >
            Tipologías y etiquetas
          </button>
        )}
        {canBulk && (
          <button
            type="button"
            className={tab === "bulk" ? "tab active" : "tab"}
            onClick={() => setTab("bulk")}
          >
            Nóminas masivas
          </button>
        )}
        {canWrite && (
          <button
            type="button"
            className={tab === "notify" ? "tab active" : "tab"}
            onClick={() => setTab("notify")}
          >
            Avisos caducidad
          </button>
        )}
      </div>

      {msg && (
        <div
          className={`alert ${
            msg.includes("correctamente") ||
            msg.includes("Enviado") ||
            msg.includes("creada") ||
            msg.includes("asignadas") ||
            msg.includes("guardada") ||
            msg.includes("ZIP") ||
            msg.includes("Enviados") ||
            msg.includes("Simulación") ||
            msg.includes("eliminado")
              ? "alert-ok"
              : "alert-error"
          }`}
        >
          {msg}
        </div>
      )}

      {tab === "list" && (
        <>
          <TableToolbar
            search={search}
            onSearchChange={setSearch}
            onSubmit={load}
            placeholder="Nombre, título o tipo…"
            filters={[
              {
                label: "Tipo",
                value: typeFilter,
                onChange: setTypeFilter,
                options: [{ value: "", label: "Todos" }, ...typeOptions],
              },
              {
                label: "Etiqueta",
                value: tagFilter,
                onChange: setTagFilter,
                options: [{ value: "", label: "Todas" }, ...tagOptions],
              },
            ]}
          />
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={expiredOnly}
              onChange={(ev) => setExpiredOnly(ev.target.checked)}
            />
            Solo caducados
          </label>
          <div className="toolbar" style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              className="btn btn-sm"
              disabled={downloading || rows.length === 0}
              onClick={() => downloadZip(false)}
            >
              {downloading ? "Preparando…" : "Descargar listado (ZIP)"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={downloading || selected.size === 0}
              onClick={() => downloadZip(true)}
            >
              Descargar selección ({selected.size})
            </button>
          </div>
          {canWrite && (
            <p className="muted">
              Para firma electrónica con certificado, sube el documento y ve a{" "}
              <Link to="/app/firmas">Firmas</Link>.
            </p>
          )}
          <div className="table-wrap card">
            <table>
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      checked={rows.length > 0 && selected.size === rows.length}
                      onChange={toggleSelectAll}
                      aria-label="Seleccionar todos"
                    />
                  </th>
                  <th>Archivo</th>
                  <th>Destino</th>
                  <th>Tipo</th>
                  <th>Etiquetas</th>
                  <th>Caducidad</th>
                  <th>WA / Acuse</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => (
                  <tr key={d.id} className={d.is_expired ? "row-expired" : ""}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(d.id)}
                        onChange={() => toggleSelect(d.id)}
                        aria-label={`Seleccionar ${d.file_name}`}
                      />
                    </td>
                    <td>
                      <strong>{d.file_name}</strong>
                      {d.title && (
                        <div className="muted small">{d.title}</div>
                      )}
                    </td>
                    <td>
                      {d.employee_id
                        ? byId(d.employee_id)
                        : d.company_id
                          ? "Empresa"
                          : "—"}
                    </td>
                    <td>{d.document_type_name ?? d.document_type}</td>
                    <td>
                      {d.tags.length
                        ? d.tags.map((t) => (
                            <span
                              key={t.id}
                              className="badge"
                              style={
                                t.color
                                  ? { backgroundColor: t.color, color: "#fff" }
                                  : undefined
                              }
                            >
                              {t.name}
                            </span>
                          ))
                        : "—"}
                    </td>
                    <td>
                      {d.expires_at
                        ? new Date(d.expires_at).toLocaleDateString("es-ES")
                        : "—"}
                      {d.is_expired && (
                        <span className="badge badge-warn">Caducado</span>
                      )}
                    </td>
                    <td>
                      <div className="small">
                        WA:{" "}
                        {d.sent_at
                          ? new Date(d.sent_at).toLocaleString("es-ES")
                          : "No"}
                      </div>
                      <div className="small">
                        Acuse:{" "}
                        {d.acknowledged_at
                          ? new Date(d.acknowledged_at).toLocaleString("es-ES")
                          : "Pendiente"}
                      </div>
                    </td>
                    <td className="actions">
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => downloadOne(d.id, d.file_name)}
                      >
                        Descargar
                      </button>
                      {canWrite && d.employee_id && (
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={() => sendWhatsapp(d.id)}
                        >
                          Enviar WA
                        </button>
                      )}
                      {canWrite && (
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
      )}

      {tab === "upload" && canCreate && (
        <section className="card">
          <h3>Subir documento</h3>
          <form onSubmit={upload} className="form-grid">
            <label>
              Asociar a
              <select
                value={uploadForm.target}
                onChange={(ev) =>
                  setUploadForm({
                    ...uploadForm,
                    target: ev.target.value as "employee" | "company",
                  })
                }
              >
                <option value="employee">Empleado</option>
                <option value="company">Empresa (actual)</option>
              </select>
            </label>
            {uploadForm.target === "employee" && (
              <label>
                Empleado
                <select
                  required
                  value={uploadForm.employee_id}
                  onChange={(ev) =>
                    setUploadForm({ ...uploadForm, employee_id: ev.target.value })
                  }
                >
                  <option value="">Seleccionar…</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.full_name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Tipología
              <select
                value={uploadForm.document_type_id}
                onChange={(ev) =>
                  setUploadForm({
                    ...uploadForm,
                    document_type_id: ev.target.value,
                  })
                }
              >
                <option value="">Por defecto</option>
                {types.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Título (opcional)
              <input
                value={uploadForm.title}
                onChange={(ev) =>
                  setUploadForm({ ...uploadForm, title: ev.target.value })
                }
              />
            </label>
            <label>
              Fecha de caducidad
              <input
                type="date"
                value={uploadForm.expires_at}
                onChange={(ev) =>
                  setUploadForm({ ...uploadForm, expires_at: ev.target.value })
                }
              />
            </label>
            {tags.length > 0 && (
              <fieldset>
                <legend>Etiquetas</legend>
                {tags.map((t) => (
                  <label key={t.id} className="checkbox-inline">
                    <input
                      type="checkbox"
                      checked={uploadForm.tag_ids.includes(t.id)}
                      onChange={(ev) => {
                        const ids = ev.target.checked
                          ? [...uploadForm.tag_ids, t.id]
                          : uploadForm.tag_ids.filter((id) => id !== t.id);
                        setUploadForm({ ...uploadForm, tag_ids: ids });
                      }}
                    />
                    {t.name}
                  </label>
                ))}
              </fieldset>
            )}
            <label>
              Archivo
              <input
                type="file"
                required
                onChange={(ev) =>
                  setUploadForm({
                    ...uploadForm,
                    file: ev.target.files?.[0] ?? null,
                  })
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

      {tab === "catalog" && canWrite && (
        <div className="grid-2">
          <section className="card">
            <h3>Tipologías</h3>
            <ul className="simple-list">
              {types.map((t) => (
                <li key={t.id}>
                  <strong>{t.name}</strong>{" "}
                  <span className="muted">({t.code})</span>
                </li>
              ))}
            </ul>
            <form onSubmit={createType} className="form-grid">
              <label>
                Código
                <input
                  required
                  value={newType.code}
                  onChange={(ev) =>
                    setNewType({ ...newType, code: ev.target.value })
                  }
                  placeholder="ej. politica"
                />
              </label>
              <label>
                Nombre
                <input
                  required
                  value={newType.name}
                  onChange={(ev) =>
                    setNewType({ ...newType, name: ev.target.value })
                  }
                />
              </label>
              <button type="submit" className="btn btn-primary btn-sm">
                Añadir tipología
              </button>
            </form>
          </section>
          <section className="card">
            <h3>Etiquetas</h3>
            <ul className="simple-list">
              {tags.map((t) => (
                <li key={t.id}>
                  <span
                    className="badge"
                    style={
                      t.color
                        ? { backgroundColor: t.color, color: "#fff" }
                        : undefined
                    }
                  >
                    {t.name}
                  </span>
                </li>
              ))}
            </ul>
            <form onSubmit={createTag} className="form-grid">
              <label>
                Nombre
                <input
                  required
                  value={newTag.name}
                  onChange={(ev) =>
                    setNewTag({ ...newTag, name: ev.target.value })
                  }
                />
              </label>
              <label>
                Color
                <input
                  type="color"
                  value={newTag.color}
                  onChange={(ev) =>
                    setNewTag({ ...newTag, color: ev.target.value })
                  }
                />
              </label>
              <button type="submit" className="btn btn-primary btn-sm">
                Añadir etiqueta
              </button>
            </form>
          </section>
        </div>
      )}

      {tab === "notify" && canWrite && (
        <section className="card">
          <h3>Avisos de caducidad</h3>
          <p className="muted">
            Envía recordatorios por WhatsApp y/o email cuando un documento
            llegue a los días configurados antes de su fecha de caducidad. Cada
            aviso se envía una sola vez por umbral. Programa{" "}
            <code>POST /api/documents/run-expiry-notifications</code> en un cron
            diario para automatizarlo.
          </p>
          <form onSubmit={saveNotifySettings} className="form-grid">
            <label className="checkbox-inline form-grid-full">
              <input
                type="checkbox"
                checked={notifyForm.enabled}
                onChange={(ev) =>
                  setNotifyForm({ ...notifyForm, enabled: ev.target.checked })
                }
              />
              Activar avisos automáticos
            </label>
            <label>
              Días antes de caducar (separados por coma)
              <input
                value={notifyForm.days_before}
                onChange={(ev) =>
                  setNotifyForm({ ...notifyForm, days_before: ev.target.value })
                }
                placeholder="30,7,1,0"
              />
              <span className="muted small">
                Ej. 30, 7, 1 y 0 (el día de caducidad)
              </span>
            </label>
            <label>
              Emails adicionales (opcional)
              <input
                value={notifyForm.extra_emails}
                onChange={(ev) =>
                  setNotifyForm({ ...notifyForm, extra_emails: ev.target.value })
                }
                placeholder="rrhh@empresa.com, legal@empresa.com"
              />
            </label>
            <fieldset className="form-grid-full">
              <legend>Canales</legend>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={notifyForm.channel_whatsapp}
                  onChange={(ev) =>
                    setNotifyForm({
                      ...notifyForm,
                      channel_whatsapp: ev.target.checked,
                    })
                  }
                />
                WhatsApp
              </label>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={notifyForm.channel_email}
                  onChange={(ev) =>
                    setNotifyForm({
                      ...notifyForm,
                      channel_email: ev.target.checked,
                    })
                  }
                />
                Email (requiere SMTP en configuración)
              </label>
            </fieldset>
            <fieldset className="form-grid-full">
              <legend>Destinatarios</legend>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={notifyForm.notify_employee}
                  onChange={(ev) =>
                    setNotifyForm({
                      ...notifyForm,
                      notify_employee: ev.target.checked,
                    })
                  }
                />
                Empleado del documento
              </label>
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={notifyForm.notify_managers}
                  onChange={(ev) =>
                    setNotifyForm({
                      ...notifyForm,
                      notify_managers: ev.target.checked,
                    })
                  }
                />
                Responsables con permiso de documentos
              </label>
            </fieldset>
            <button type="submit" className="btn btn-primary">
              Guardar configuración
            </button>
          </form>
          {notifySettings && (
            <div className="toolbar" style={{ marginTop: "1rem" }}>
              <button
                type="button"
                className="btn btn-sm"
                disabled={notifyRunning || !notifySettings.enabled}
                onClick={() => runNotifyNow(true)}
              >
                Simular envío
              </button>
              <button
                type="button"
                className="btn btn-sm btn-primary"
                disabled={notifyRunning || !notifySettings.enabled}
                onClick={() => runNotifyNow(false)}
              >
                {notifyRunning ? "Enviando…" : "Enviar avisos ahora"}
              </button>
            </div>
          )}
          {notifyRunResult && (
            <p className="muted small" style={{ marginTop: "0.75rem" }}>
              Revisados: {notifyRunResult.checked} · Enviados/simulados:{" "}
              {notifyRunResult.sent} · Omitidos (ya avisados):{" "}
              {notifyRunResult.skipped} · Errores: {notifyRunResult.errors}
              {notifyRunResult.details.length > 0 && (
                <>
                  <br />
                  {notifyRunResult.details.join(" · ")}
                </>
              )}
            </p>
          )}
        </section>
      )}

      {tab === "bulk" && canBulk && (
        <section className="card">
          <h3>Subida masiva de nóminas</h3>
          <p className="muted">
            Sube un ZIP con PDFs o varios PDF. Cada página se analiza para
            detectar el DNI/NIE y asignar la nómina al empleado de la empresa
            activa.
          </p>
          <form onSubmit={bulkUpload} className="form-grid">
            <label>
              Periodo / caducidad (opcional)
              <input
                type="date"
                value={bulkExpires}
                onChange={(ev) => setBulkExpires(ev.target.value)}
              />
            </label>
            <label>
              Archivos (PDF o ZIP)
              <input
                type="file"
                multiple
                accept=".pdf,.zip,application/pdf,application/zip"
                required
                onChange={(ev) => setBulkFiles(ev.target.files)}
              />
            </label>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={bulkUploading}
            >
              {bulkUploading ? "Procesando…" : "Procesar nóminas"}
            </button>
          </form>
          {bulkResult && (
            <div className="table-wrap" style={{ marginTop: "1rem" }}>
              <table>
                <thead>
                  <tr>
                    <th>Origen</th>
                    <th>Pág.</th>
                    <th>DNI/NIE</th>
                    <th>Empleado</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {bulkResult.items.map((item, i) => (
                    <tr key={i}>
                      <td>{item.source_file}</td>
                      <td>{item.page ?? "—"}</td>
                      <td>{item.id_document ?? "—"}</td>
                      <td>{item.employee_name ?? "—"}</td>
                      <td>
                        <span
                          className={`badge ${
                            item.status === "ok"
                              ? "badge-ok"
                              : item.status === "error"
                                ? "badge-danger"
                                : ""
                          }`}
                        >
                          {item.status}
                        </span>
                        {item.message && (
                          <div className="muted small">{item.message}</div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}
