import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  ClockReminderRunResult,
  ClockSettings,
  IncidentAutoRule,
} from "../api/types";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { canModule } from "../lib/permissions";

export default function ClockSettingsPage() {
  const { user } = useAuth();
  const { success, error } = useToast();
  const canWrite = user && canModule(user.permissions, "write", "clock_ins");
  const [form, setForm] = useState<ClockSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [reminderResult, setReminderResult] = useState<ClockReminderRunResult | null>(
    null
  );
  const [runningReminders, setRunningReminders] = useState(false);
  const [incidentRules, setIncidentRules] = useState<IncidentAutoRule | null>(null);

  const load = useCallback(async () => {
    setForm(await api.get<ClockSettings>("/clock-settings"));
    if (canWrite) {
      try {
        setIncidentRules(await api.get<IncidentAutoRule>("/incidents/rules"));
      } catch {
        setIncidentRules(null);
      }
    }
  }, [canWrite]);

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

  const clockSettingsBody = () => ({
    require_geolocation: form!.require_geolocation,
    clock_reminder_minutes: form!.clock_reminder_minutes || null,
    clock_exit_reminder_minutes: form!.clock_exit_reminder_minutes || null,
    incident_reminder_enabled: form!.incident_reminder_enabled,
    incident_reminder_minutes: form!.incident_reminder_minutes || null,
    inbound_documents_enabled: form!.inbound_documents_enabled,
    inbound_document_codes: form!.inbound_document_codes,
    inbound_signature_delivery_ids: form!.inbound_signature_delivery_ids,
    send_welcome_with_documents: form!.send_welcome_with_documents,
    welcome_message_extra: form!.welcome_message_extra || null,
    daily_summary_enabled: form!.daily_summary_enabled,
    require_project_on_clock_in: form!.require_project_on_clock_in,
  });

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form || !canWrite) return;
    setSaving(true);
    try {
      const updated = await api.put<ClockSettings>("/clock-settings", clockSettingsBody());
      setForm(updated);
      success("Configuración de fichajes guardada");
    } catch (err) {
      error(String(err));
    } finally {
      setSaving(false);
    }
  };

  const runReminders = async () => {
    if (!form || !canWrite) return;
    setRunningReminders(true);
    setReminderResult(null);
    try {
      const updated = await api.put<ClockSettings>("/clock-settings", clockSettingsBody());
      setForm(updated);
      const res = await api.post<ClockReminderRunResult>(
        "/clock-settings/run-reminders",
        {}
      );
      setReminderResult(res);
      success(
        `Recordatorios enviados: ${res.sent + (res.sent_exit ?? 0)} (${res.skipped} omitidos)`
      );
    } catch (err) {
      error(String(err));
    } finally {
      setRunningReminders(false);
    }
  };

  const saveIncidentRules = async () => {
    if (!incidentRules || !canWrite) return;
    try {
      const updated = await api.put<IncidentAutoRule>("/incidents/rules", {
        late_entrada_enabled: incidentRules.late_entrada_enabled,
        late_entrada_grace_minutes: incidentRules.late_entrada_grace_minutes,
        late_entrada_notify_whatsapp: incidentRules.late_entrada_notify_whatsapp,
        late_entrada_require_justification: incidentRules.late_entrada_require_justification,
        missing_clock_in_enabled: incidentRules.missing_clock_in_enabled,
        missing_clock_in_hours: incidentRules.missing_clock_in_hours,
        missing_clock_in_notify_whatsapp: incidentRules.missing_clock_in_notify_whatsapp,
        missing_clock_in_require_justification: incidentRules.missing_clock_in_require_justification,
        missing_clock_out_enabled: incidentRules.missing_clock_out_enabled,
        missing_clock_out_hours: incidentRules.missing_clock_out_hours,
        missing_clock_out_notify_whatsapp: incidentRules.missing_clock_out_notify_whatsapp,
        missing_clock_out_require_justification: incidentRules.missing_clock_out_require_justification,
      });
      setIncidentRules(updated);
      success("Reglas de incidencias guardadas");
    } catch (err) {
      error(String(err));
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
            <h3>Resumen del día (WhatsApp)</h3>
            <p className="muted small">
              Permite al empleado pedir por WhatsApp un resumen de fichajes y paradas del
              día (p. ej. «resumen del día»).
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                disabled={!canWrite}
                checked={form.daily_summary_enabled}
                onChange={(ev) =>
                  setForm({ ...form, daily_summary_enabled: ev.target.checked })
                }
              />
              <span>Permitir solicitar resumen del día</span>
            </label>
          </section>

          <section className="card clock-settings-card">
            <h3>Proyecto al fichar</h3>
            <p className="muted small">
              Si está activo, el empleado debe elegir un proyecto al fichar por WhatsApp o
              desde el panel. Gestiona los proyectos en{" "}
              <Link to="/app/proyectos">Proyectos</Link>.
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                disabled={!canWrite}
                checked={form.require_project_on_clock_in}
                onChange={(ev) =>
                  setForm({
                    ...form,
                    require_project_on_clock_in: ev.target.checked,
                  })
                }
              />
              <span>Solicitar proyecto al fichar</span>
            </label>
          </section>

          <section className="card clock-settings-card">
            <h3>Recordatorios de fichaje</h3>
            <p className="muted small">
              Se envían automáticamente cada 5 minutos. Solo en días y franjas laborales del empleado.
            </p>
            <div className="form-grid clock-settings-fields">
              <label>
                Recordatorio de <strong>entrada</strong> — minutos tras inicio de jornada
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
                  Vacío = desactivado. Avisa si no hay ENTRADA registrada pasados X minutos.
                </span>
              </label>
              <label>
                Recordatorio de <strong>salida</strong> — minutos tras fin de jornada
                <input
                  type="number"
                  min={0}
                  max={1440}
                  disabled={!canWrite}
                  placeholder="Desactivado"
                  value={form.clock_exit_reminder_minutes ?? ""}
                  onChange={(ev) => {
                    const v = ev.target.value;
                    setForm({
                      ...form,
                      clock_exit_reminder_minutes: v === "" ? null : parseInt(v, 10),
                    });
                  }}
                />
                <span className="muted small">
                  Vacío = desactivado. Avisa si hay ENTRADA abierta sin SALIDA pasados X minutos del fin de jornada.
                </span>
              </label>
            </div>
            {canWrite && (
              <div className="test-row">
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={runningReminders || (!form.clock_reminder_minutes && !form.clock_exit_reminder_minutes)}
                  onClick={runReminders}
                >
                  {runningReminders ? "Enviando…" : "Probar recordatorios ahora"}
                </button>
                {reminderResult && (
                  <span className="muted small">
                    Entrada: {reminderResult.sent} enviados
                    {" · "}Salida: {reminderResult.sent_exit ?? 0} enviados
                    {" · "}Omitidos: {reminderResult.skipped}
                    {reminderResult.errors.length > 0 &&
                      ` · Errores: ${reminderResult.errors.length}`}
                  </span>
                )}
              </div>
            )}
          </section>

          {incidentRules && (
            <>
              <section className="card clock-settings-card">
                <h3>Incidencia: entrada tardía</h3>
                <p className="muted small">
                  Si el empleado ficha entrada superado el margen, se crea una incidencia automática.
                  Se evalúa en el momento de fichar.
                </p>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite}
                    checked={incidentRules.late_entrada_enabled}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, late_entrada_enabled: ev.target.checked })
                    }
                  />
                  <span>Activar incidencia por entrada tardía</span>
                </label>
                <div className="form-grid clock-settings-fields">
                  <label>
                    Margen de gracia (minutos)
                    <input
                      type="number"
                      min={0}
                      max={240}
                      disabled={!canWrite || !incidentRules.late_entrada_enabled}
                      value={incidentRules.late_entrada_grace_minutes}
                      onChange={(ev) =>
                        setIncidentRules({
                          ...incidentRules,
                          late_entrada_grace_minutes: parseInt(ev.target.value, 10) || 0,
                        })
                      }
                    />
                    <span className="muted small">Minutos de tolerancia antes de crear incidencia</span>
                  </label>
                </div>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite || !incidentRules.late_entrada_enabled}
                    checked={incidentRules.late_entrada_notify_whatsapp}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, late_entrada_notify_whatsapp: ev.target.checked })
                    }
                  />
                  <span>Notificar por WhatsApp con enlace de justificación</span>
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite || !incidentRules.late_entrada_enabled}
                    checked={incidentRules.late_entrada_require_justification}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, late_entrada_require_justification: ev.target.checked })
                    }
                  />
                  <span>Requerir justificación del empleado (enlace público)</span>
                </label>
              </section>

              <section className="card clock-settings-card">
                <h3>Incidencia: omisión de entrada</h3>
                <p className="muted small">
                  Si el empleado no ha fichado entrada pasadas X horas desde el inicio de su jornada,
                  se crea una incidencia automáticamente. Se comprueba cada 15 minutos.
                  No aplica en días de permiso aprobado.
                </p>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite}
                    checked={incidentRules.missing_clock_in_enabled}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, missing_clock_in_enabled: ev.target.checked })
                    }
                  />
                  <span>Activar incidencia por omisión de entrada</span>
                </label>
                <div className="form-grid clock-settings-fields">
                  <label>
                    Horas tras inicio de jornada
                    <input
                      type="number"
                      min={0.5}
                      max={24}
                      step={0.5}
                      disabled={!canWrite || !incidentRules.missing_clock_in_enabled}
                      value={incidentRules.missing_clock_in_hours}
                      onChange={(ev) =>
                        setIncidentRules({
                          ...incidentRules,
                          missing_clock_in_hours: parseFloat(ev.target.value) || 2,
                        })
                      }
                    />
                    <span className="muted small">
                      Crear incidencia si no hay entrada pasadas X horas del inicio de jornada
                    </span>
                  </label>
                </div>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite || !incidentRules.missing_clock_in_enabled}
                    checked={incidentRules.missing_clock_in_notify_whatsapp}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, missing_clock_in_notify_whatsapp: ev.target.checked })
                    }
                  />
                  <span>Notificar por WhatsApp al empleado</span>
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite || !incidentRules.missing_clock_in_enabled}
                    checked={incidentRules.missing_clock_in_require_justification}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, missing_clock_in_require_justification: ev.target.checked })
                    }
                  />
                  <span>Requerir justificación del empleado (enlace público)</span>
                </label>
              </section>

              <section className="card clock-settings-card">
                <h3>Incidencia: omisión de salida</h3>
                <p className="muted small">
                  Si un fichaje lleva más de X horas abierto sin registrar salida,
                  se crea una incidencia automáticamente. Se comprueba cada 15 minutos.
                </p>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite}
                    checked={incidentRules.missing_clock_out_enabled}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, missing_clock_out_enabled: ev.target.checked })
                    }
                  />
                  <span>Activar incidencia por fichaje sin cerrar</span>
                </label>
                <div className="form-grid clock-settings-fields">
                  <label>
                    Horas máximas de fichaje abierto
                    <input
                      type="number"
                      min={1}
                      max={48}
                      step={0.5}
                      disabled={!canWrite || !incidentRules.missing_clock_out_enabled}
                      value={incidentRules.missing_clock_out_hours}
                      onChange={(ev) =>
                        setIncidentRules({
                          ...incidentRules,
                          missing_clock_out_hours: parseFloat(ev.target.value) || 12,
                        })
                      }
                    />
                    <span className="muted small">
                      Crear incidencia si el fichaje lleva abierto más de X horas sin salida
                    </span>
                  </label>
                </div>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite || !incidentRules.missing_clock_out_enabled}
                    checked={incidentRules.missing_clock_out_notify_whatsapp}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, missing_clock_out_notify_whatsapp: ev.target.checked })
                    }
                  />
                  <span>Notificar por WhatsApp al empleado</span>
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    disabled={!canWrite || !incidentRules.missing_clock_out_enabled}
                    checked={incidentRules.missing_clock_out_require_justification}
                    onChange={(ev) =>
                      setIncidentRules({ ...incidentRules, missing_clock_out_require_justification: ev.target.checked })
                    }
                  />
                  <span>Requerir justificación del empleado (enlace público)</span>
                </label>
              </section>

              {canWrite && (
                <div style={{ marginBottom: "1rem" }}>
                  <button type="button" className="btn btn-primary" onClick={saveIncidentRules}>
                    Guardar reglas de incidencias
                  </button>
                </div>
              )}
            </>
          )}

          <section className="card clock-settings-card">
            <h3>Recordatorio de incidencias pendientes</h3>
            <p className="muted small">
              Envía un aviso por WhatsApp a los empleados que tengan incidencias pendientes de justificar.
              Solo dentro de la jornada laboral del empleado. Una vez por día por empleado.
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
              <span>Activar recordatorio de incidencias pendientes</span>
            </label>
            <div className="form-grid clock-settings-fields">
              <label>
                Minutos tras creación de incidencia para recordar
                <input
                  type="number"
                  min={0}
                  max={1440}
                  disabled={!canWrite || !form.incident_reminder_enabled}
                  placeholder="Desactivado"
                  value={form.incident_reminder_minutes ?? ""}
                  onChange={(ev) => {
                    const v = ev.target.value;
                    setForm({
                      ...form,
                      incident_reminder_minutes: v === "" ? null : parseInt(v, 10),
                    });
                  }}
                />
                <span className="muted small">
                  Vacío = desactivado. Avisa si hay incidencias sin justificar pasados X minutos.
                </span>
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
