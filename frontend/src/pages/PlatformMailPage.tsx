import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { ConnectionTest, MailLog, MailSettings } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import PageHeader from "../components/PageHeader";

type LogFilter = "all" | "ok" | "fail";

export default function PlatformMailPage() {
  const [form, setForm] = useState<MailSettings | null>(null);
  const [password, setPassword] = useState("");
  const [logs, setLogs] = useState<MailLog[]>([]);
  const [logFilter, setLogFilter] = useState<LogFilter>("all");
  const [testEmail, setTestEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [test, setTest] = useState<ConnectionTest | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const loadSettings = useCallback(async () => {
    setForm(await api.get<MailSettings>("/platform/mail/settings"));
  }, []);

  const loadLogs = useCallback(async (filter: LogFilter) => {
    setLoadingLogs(true);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (filter === "ok") params.set("success_only", "true");
      if (filter === "fail") params.set("success_only", "false");
      setLogs(await api.get<MailLog[]>(`/platform/mail/logs?${params}`));
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  const load = useCallback(async () => {
    setError("");
    try {
      await loadSettings();
      await loadLogs(logFilter);
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    }
  }, [loadSettings, loadLogs, logFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadLogs(logFilter).catch((err) =>
      setError(String(err).replace(/^Error:\s*/i, ""))
    );
  }, [logFilter, loadLogs]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setMsg("");
    setError("");
    try {
      const payload: Record<string, unknown> = {
        smtp_host: form.smtp_host || null,
        smtp_port: form.smtp_port,
        smtp_user: form.smtp_user || null,
        smtp_use_tls: form.smtp_use_tls,
        mail_from_address: form.mail_from_address || null,
        mail_from_name: form.mail_from_name || null,
      };
      if (password.trim()) payload.smtp_password = password.trim();
      const updated = await api.put<MailSettings>("/platform/mail/settings", payload);
      setForm(updated);
      setPassword("");
      setMsg("Configuración SMTP guardada");
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    if (!testEmail.trim()) {
      setError("Indica un correo de destino para la prueba");
      return;
    }
    setError("");
    setTest(null);
    try {
      const result = await api.post<ConnectionTest>("/platform/mail/test", {
        to_email: testEmail.trim(),
      });
      setTest(result);
      await loadLogs(logFilter);
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  type LogRow = MailLog & { date_label: string; status_label: string };

  const logTableData = useMemo<LogRow[]>(
    () =>
      logs.map((row) => ({
        ...row,
        date_label: new Date(row.created_at).toLocaleString("es-ES"),
        status_label: row.success ? "OK" : "Error",
      })),
    [logs]
  );

  const logColumns = useMemo<DataTableColumn<LogRow>[]>(
    () => [
      { title: "Fecha", field: "date_label", headerFilter: "input", minWidth: 150 },
      {
        title: "Destino",
        field: "to_address",
        headerFilter: "input",
        formatter: (c) => `<span class="mono small">${String(c.getValue())}</span>`,
        minWidth: 160,
      },
      { title: "Asunto", field: "subject", headerFilter: "input", minWidth: 180 },
      {
        title: "Tipo",
        field: "event_type",
        headerFilter: "input",
        formatter: (c) => `<span class="badge">${String(c.getValue())}</span>`,
        width: 120,
      },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", OK: "OK", Error: "Error" } },
        formatter: (cell) => {
          const r = cell.getRow().getData() as LogRow;
          const cls = r.success ? "test-ok" : "test-fail";
          return `<span class="${cls}">${r.status_label}</span>`;
        },
        width: 90,
      },
      {
        title: "Detalle",
        field: "detail",
        headerFilter: "input",
        formatter: (c) => `<span class="small muted">${String(c.getValue() ?? "—")}</span>`,
        minWidth: 160,
      },
    ],
    []
  );

  if (!form) {
    return <p className="muted">Cargando correo…</p>;
  }

  const configured = Boolean(form.smtp_host && form.mail_from_address);

  return (
    <>
      <PageHeader
        title="Correo"
        subtitle="Configuración SMTP global y registro de envíos"
      />

      {error && <div className="alert alert-error">{error}</div>}
      {msg && <div className="alert alert-success">{msg}</div>}

      <section className="card" style={{ marginBottom: "1.5rem" }}>
        <div
          className={`wa-status ${configured ? "wa-status--ok" : "wa-status--pending"}`}
        >
          <span className="wa-status__dot" aria-hidden />
          <div>
            <strong>{configured ? "SMTP configurado" : "SMTP pendiente"}</strong>
            <p className="muted small">
              {configured
                ? `Remitente: ${form.mail_from_name || "alcurro"} <${form.mail_from_address}>`
                : "Indica servidor SMTP y dirección remitente para habilitar el envío."}
            </p>
          </div>
        </div>
      </section>

      <form className="card form-grid" onSubmit={save} style={{ marginBottom: "1.5rem" }}>
        <h3>Servidor SMTP</h3>
        <p className="muted small form-grid-full">
          Credenciales compartidas para toda la plataforma (firmas, notificaciones, pruebas).
          Puerto 587 con STARTTLS es lo habitual; usa 465 con TLS si tu proveedor lo requiere.
        </p>
        <label>
          Host SMTP
          <input
            value={form.smtp_host || ""}
            onChange={(e) => setForm({ ...form, smtp_host: e.target.value || null })}
            placeholder="smtp.ejemplo.com"
          />
        </label>
        <label>
          Puerto
          <input
            type="number"
            min={1}
            max={65535}
            value={form.smtp_port}
            onChange={(e) =>
              setForm({ ...form, smtp_port: Number(e.target.value) || 587 })
            }
          />
        </label>
        <label>
          Usuario
          <input
            value={form.smtp_user || ""}
            onChange={(e) => setForm({ ...form, smtp_user: e.target.value || null })}
            autoComplete="off"
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={
              form.smtp_password_configured ? "•••••••• (dejar vacío para no cambiar)" : ""
            }
            autoComplete="new-password"
          />
        </label>
        <label className="checkbox-row form-grid-full">
          <input
            type="checkbox"
            checked={form.smtp_use_tls}
            onChange={(e) => setForm({ ...form, smtp_use_tls: e.target.checked })}
          />
          Usar TLS (STARTTLS en 587 o SSL en 465)
        </label>
        <label>
          Remitente (email)
          <input
            type="email"
            value={form.mail_from_address || ""}
            onChange={(e) =>
              setForm({ ...form, mail_from_address: e.target.value || null })
            }
            placeholder="noreply@tuempresa.com"
          />
        </label>
        <label>
          Nombre remitente
          <input
            value={form.mail_from_name || ""}
            onChange={(e) =>
              setForm({ ...form, mail_from_name: e.target.value || null })
            }
            placeholder="alcurro"
          />
        </label>
        <div className="form-actions full">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </form>

      <section className="card form-grid" style={{ marginBottom: "1.5rem" }}>
        <h3>Enviar prueba</h3>
        <label className="full">
          Correo de destino
          <input
            type="email"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
            placeholder="tu@email.com"
          />
        </label>
        <div className="form-actions full">
          <button type="button" className="btn btn-ghost" onClick={runTest}>
            Enviar correo de prueba
          </button>
          {test && (
            <span className={test.ok ? "test-ok" : "test-fail"}>
              {test.message}
              {test.detail ? ` — ${test.detail}` : ""}
            </span>
          )}
        </div>
      </section>

      <div className="card">
        <div className="toolbar" style={{ marginBottom: "1rem" }}>
          <h3 style={{ margin: 0 }}>Logs de envío</h3>
          <select
            value={logFilter}
            onChange={(e) => setLogFilter(e.target.value as LogFilter)}
            aria-label="Filtrar logs"
          >
            <option value="all">Todos</option>
            <option value="ok">Enviados</option>
            <option value="fail">Fallidos</option>
          </select>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={loadingLogs}
            onClick={() => loadLogs(logFilter)}
          >
            {loadingLogs ? "Actualizando…" : "Actualizar"}
          </button>
        </div>

        {loadingLogs && logs.length === 0 && <p className="muted">Cargando logs…</p>}
        {!loadingLogs && logs.length === 0 && (
          <p className="muted">Aún no hay envíos registrados.</p>
        )}
        {logs.length > 0 && (
          <DataTable
            data={logTableData}
            columns={logColumns}
            loading={loadingLogs}
            exportFilename="logs_correo"
            height="420px"
          />
        )}
      </div>
    </>
  );
}
