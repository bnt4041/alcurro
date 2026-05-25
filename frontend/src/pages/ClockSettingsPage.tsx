import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ClockReminderRunResult, ClockSettings } from "../api/types";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";

export default function ClockSettingsPage() {
  const { user } = useAuth();
  const canWrite = user && canModule(user.permissions, "write", "clock_ins");
  const [form, setForm] = useState<ClockSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [reminderResult, setReminderResult] = useState<ClockReminderRunResult | null>(
    null
  );
  const [runningReminders, setRunningReminders] = useState(false);

  const load = useCallback(async () => {
    setForm(await api.get<ClockSettings>("/clock-settings"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleSignatureDelivery = (id: string) => {
    if (!form) return;
    const ids = form.inbound_signature_delivery_ids.includes(id)
      ? form.inbound_signature_delivery_ids.filter((x) => x !== id)
      : [...form.inbound_signature_delivery_ids, id];
    setForm({ ...form, inbound_signature_delivery_ids: ids });
  };

  const toggleInboundCode = (code: string) => {
    if (!form) return;
    const codes = form.inbound_document_codes.includes(code)
      ? form.inbound_document_codes.filter((c) => c !== code)
      : [...form.inbound_document_codes, code];
    setForm({ ...form, inbound_document_codes: codes });
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form || !canWrite) return;
    setSaving(true);
    setMsg("");
    try {
      const updated = await api.put<ClockSettings>("/clock-settings", {
        require_geolocation: form.require_geolocation,
        clock_reminder_minutes: form.clock_reminder_minutes || null,
        incident_reminder_enabled: form.incident_reminder_enabled,
        incident_reminder_minutes: form.incident_reminder_minutes,
        inbound_documents_enabled: form.inbound_documents_enabled,
        inbound_document_codes: form.inbound_document_codes,
        inbound_signature_delivery_ids: form.inbound_signature_delivery_ids,
        send_welcome_with_documents: form.send_welcome_with_documents,
        welcome_message_extra: form.welcome_message_extra || null,
      });
      setForm(updated);
      setMsg("Configuración de fichajes guardada");
    } catch (err) {
      setMsg(String(err));
    } finally {
      setSaving(false);
    }
  };

  const runReminders = async () => {
    setRunningReminders(true);
    setReminderResult(null);
    try {
      const res = await api.post<ClockReminderRunResult>(
        "/clock-settings/run-reminders",
        {}
      );
      setReminderResult(res);
      setMsg(`Recordatorios enviados: ${res.sent} (${res.skipped} omitidos)`);
    } catch (err) {
      setMsg(String(err));
    } finally {
      setRunningReminders(false);
    }
  };

  if (!form) return <p className="muted">Cargando configuración…</p>;

  const inboundDisabled = !form.inbound_documents_enabled;

  return (
    <>
      <PageHeader
        title="Configuración de fichajes"
        subtitle="WhatsApp: geolocalización, recordatorios y documentación de alta"
        action={
          <Link to="/app/fichajes" className="btn">
            ← Fichajes
          </Link>
        }
      />
      {msg && (
        <div
          className={`alert ${msg.includes("guardada") || msg.includes("enviados") ? "alert-ok" : "alert-error"}`}
        >
          {msg}
        </div>
      )}

      <form onSubmit={save} className="clock-settings-page">
        <div className="clock-settings-layout">
          <section className="card clock-settings-card">
            <h3>Geolocalización</h3>
            <p className="muted small">
              Recomienda compartir ubicación al fichar por WhatsApp. No bloquea el fichaje
              por texto.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                disabled={!canWrite}
                checked={form.require_geolocation}
                onChange={(ev) =>
                  setForm({ ...form, require_geolocation: ev.target.checked })
                }
              />
              <span>Solicitar geolocalización al fichar</span>
            </label>
          </section>

          <section className="card clock-settings-card">
            <h3>Recordatorio de fichaje</h3>
            <div className="form-grid clock-settings-fields">
              <label>
                Minutos tras inicio de jornada
                <input
                  type="number"
                  min={0}
                  max={1440}
                  disabled={!canWrite}
                  placeholder="Desactivado"
                  value={form.clock_reminder_minutes ?? ""}
                  onChange={(ev) => {
                    const v = ev.target.value;
                    setForm({
                      ...form,
                      clock_reminder_minutes: v === "" ? null : parseInt(v, 10),
                    });
                  }}
                />
                <span className="muted small">
                  Vacío = desactivado. Solo en días y franjas laborales, sin ENTRADA
                  registrada.
                </span>
              </label>
            </div>
            {canWrite && (
              <div className="test-row">
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={runningReminders || !form.clock_reminder_minutes}
                  onClick={runReminders}
                >
                  {runningReminders ? "Enviando…" : "Probar recordatorios ahora"}
                </button>
                {reminderResult && (
                  <span className="muted small">
                    Enviados: {reminderResult.sent} · Omitidos:{" "}
                    {reminderResult.skipped}
                    {reminderResult.errors.length > 0 &&
                      ` · Errores: ${reminderResult.errors.length}`}
                  </span>
                )}
              </div>
            )}
          </section>

          <section className="card clock-settings-card clock-settings-card--muted">
            <h3>Recordatorio de incidencias</h3>
            <p className="muted small">
              Opción reservada; el envío automático se activará en una versión futura.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                disabled={!canWrite}
                checked={form.incident_reminder_enabled}
                onChange={(ev) =>
                  setForm({ ...form, incident_reminder_enabled: ev.target.checked })
                }
              />
              <span>Activar cuando esté disponible</span>
            </label>
            <div className="form-grid clock-settings-fields">
              <label>
                Minutos (futuro)
                <input
                  type="number"
                  min={0}
                  max={1440}
                  disabled={!canWrite || !form.incident_reminder_enabled}
                  placeholder="—"
                  value={form.incident_reminder_minutes ?? ""}
                  onChange={(ev) => {
                    const v = ev.target.value;
                    setForm({
                      ...form,
                      incident_reminder_minutes: v === "" ? null : parseInt(v, 10),
                    });
                  }}
                />
              </label>
            </div>
          </section>

          <section className="card clock-settings-card clock-settings-card--wide">
            <h3>Documentación de alta (WhatsApp)</h3>
            <p className="muted small">
              Al dar de alta un empleado o en su primer mensaje se solicitan los
              documentos marcados (foto o PDF).
            </p>

            <div className="clock-settings-toggles">
              <label className="checkbox">
                <input
                  type="checkbox"
                  disabled={!canWrite}
                  checked={form.inbound_documents_enabled}
                  onChange={(ev) =>
                    setForm({ ...form, inbound_documents_enabled: ev.target.checked })
                  }
                />
                <span>Solicitar documentación en el alta</span>
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  disabled={!canWrite || inboundDisabled}
                  checked={form.send_welcome_with_documents}
                  onChange={(ev) =>
                    setForm({
                      ...form,
                      send_welcome_with_documents: ev.target.checked,
                    })
                  }
                />
                <span>Incluir en mensaje de bienvenida</span>
              </label>
            </div>

            <label className="clock-settings-textarea-label">
              Texto adicional en bienvenida
              <textarea
                rows={3}
                disabled={!canWrite}
                maxLength={1000}
                value={form.welcome_message_extra ?? ""}
                onChange={(ev) =>
                  setForm({ ...form, welcome_message_extra: ev.target.value || null })
                }
              />
            </label>

            <p className="clock-settings-subheading">Documentos a solicitar (subida)</p>
            <div
              className={`inbound-doc-grid${inboundDisabled ? " inbound-doc-grid--disabled" : ""}`}
            >
              {form.available_inbound_types.map((t) => {
                const checked = form.inbound_document_codes.includes(t.code);
                return (
                  <label
                    key={t.code}
                    className={`inbound-doc-option${checked ? " is-selected" : ""}`}
                  >
                    <input
                      type="checkbox"
                      disabled={!canWrite || inboundDisabled}
                      checked={checked}
                      onChange={() => toggleInboundCode(t.code)}
                    />
                    <div className="inbound-doc-option__body">
                      <span className="inbound-doc-option__title">
                        {t.name}
                        {t.optional && (
                          <span className="badge badge--muted">Opcional</span>
                        )}
                      </span>
                      <span className="muted small">{t.description}</span>
                    </div>
                  </label>
                );
              })}
            </div>

            <p className="clock-settings-subheading">
              Documentos de empresa para firmar (módulo Documentos)
            </p>
            {form.company_signature_documents.length === 0 ? (
              <p className="muted small">
                Sube documentos asociados a la empresa en{" "}
                <Link to="/app/documentos">Documentos</Link> (sin asignar a un empleado
                concreto).
              </p>
            ) : (
              <div
                className={`inbound-doc-grid${inboundDisabled ? " inbound-doc-grid--disabled" : ""}`}
              >
                {form.company_signature_documents.map((doc) => {
                  const checked = form.inbound_signature_delivery_ids.includes(doc.id);
                  return (
                    <label
                      key={doc.id}
                      className={`inbound-doc-option${checked ? " is-selected" : ""}`}
                    >
                      <input
                        type="checkbox"
                        disabled={!canWrite || inboundDisabled}
                        checked={checked}
                        onChange={() => toggleSignatureDelivery(doc.id)}
                      />
                      <div className="inbound-doc-option__body">
                        <span className="inbound-doc-option__title">{doc.title}</span>
                        <span className="muted small">
                          {doc.company_name ?? "Empresa"} · {doc.file_name}
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        <div className="settings-footer clock-settings-footer">
          <p className="muted small">
            Última actualización:{" "}
            {new Date(form.updated_at).toLocaleString("es-ES")}
          </p>
          {canWrite ? (
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Guardando…" : "Guardar configuración"}
            </button>
          ) : (
            <span className="muted small">Solo lectura</span>
          )}
        </div>
      </form>
    </>
  );
}
