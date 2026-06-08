import { FormEvent, useCallback, useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";

interface PolicyData {
  ai_monthly_limit: number;
  ai_limit_action: string;
  whatsapp_monthly_limit: number;
  whatsapp_limit_action: string;
  support_channel: string;
  support_email: string | null;
  support_notice: string | null;
  tos_notice: string | null;
  updated_at: string;
}

const ADMIN_TOKEN_KEY = "platform_token";

async function platformFetch(path: string, method = "GET", body?: unknown) {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function PlatformPolicyPage() {
  const [data, setData] = useState<PolicyData | null>(null);
  const [form, setForm] = useState<Partial<PolicyData>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const row = await platformFetch("/platform/policies");
      setData(row);
      setForm(row);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    try {
      const updated = await platformFetch("/platform/policies", "PATCH", {
        ai_monthly_limit: form.ai_monthly_limit,
        ai_limit_action: form.ai_limit_action,
        whatsapp_monthly_limit: form.whatsapp_monthly_limit,
        whatsapp_limit_action: form.whatsapp_limit_action,
        support_channel: form.support_channel,
        support_email: form.support_email || null,
        support_notice: form.support_notice || null,
        tos_notice: form.tos_notice || null,
      });
      setData(updated);
      setForm(updated);
      setMsg("Políticas guardadas");
    } catch (err) {
      setMsg(String(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="muted">Cargando…</p>;

  return (
    <>
      <PageHeader
        title="Políticas de uso"
        subtitle="Límites de IA, WhatsApp y condiciones de soporte para todos los tenants"
      />
      {msg && <div className="alert alert-info">{msg}</div>}

      <form onSubmit={save}>

        <section className="card settings-section">
          <h3>Límite de IA (Ollama)</h3>
          <p className="muted small">
            Máximo de consultas al modelo de IA por tenant al mes.
            Al superarlo se puede avisar o bloquear el servicio.
          </p>
          <div className="form-grid">
            <label>
              Consultas IA / mes por tenant
              <div className="input-hint">0 = sin límite</div>
              <input
                type="number"
                min={0}
                value={form.ai_monthly_limit ?? 500}
                onChange={(e) => setForm({ ...form, ai_monthly_limit: +e.target.value })}
              />
            </label>
            <label>
              Acción al superar el límite
              <select
                value={form.ai_limit_action ?? "warn"}
                onChange={(e) => setForm({ ...form, ai_limit_action: e.target.value })}
              >
                <option value="warn">Avisar al admin (warn)</option>
                <option value="block">Bloquear nuevas consultas (block)</option>
              </select>
            </label>
          </div>
        </section>

        <section className="card settings-section">
          <h3>Fair use — WhatsApp</h3>
          <p className="muted small">
            Máximo de mensajes enviados por el bot por tenant al mes.
            Evita el abuso del canal de WhatsApp.
          </p>
          <div className="form-grid">
            <label>
              Mensajes WhatsApp / mes por tenant
              <div className="input-hint">0 = sin límite</div>
              <input
                type="number"
                min={0}
                value={form.whatsapp_monthly_limit ?? 2000}
                onChange={(e) => setForm({ ...form, whatsapp_monthly_limit: +e.target.value })}
              />
            </label>
            <label>
              Acción al superar el límite
              <select
                value={form.whatsapp_limit_action ?? "warn"}
                onChange={(e) => setForm({ ...form, whatsapp_limit_action: e.target.value })}
              >
                <option value="warn">Avisar al admin (warn)</option>
                <option value="block">Bloquear respuestas del bot (block)</option>
              </select>
            </label>
          </div>
        </section>

        <section className="card settings-section">
          <h3>Soporte</h3>
          <p className="muted small">
            Texto e información del canal de soporte. Es visible para los clientes
            en su página de cuenta.
          </p>
          <div className="form-grid">
            <label>
              Canal de soporte
              <select
                value={form.support_channel ?? "tickets"}
                onChange={(e) => setForm({ ...form, support_channel: e.target.value })}
              >
                <option value="tickets">Solo tickets (recomendado)</option>
                <option value="email">Email</option>
                <option value="mixed">Tickets + email</option>
              </select>
            </label>
            <label>
              Email de soporte
              <input
                type="email"
                value={form.support_email ?? ""}
                onChange={(e) => setForm({ ...form, support_email: e.target.value || null })}
              />
            </label>
            <label className="form-grid-full">
              Aviso de soporte visible para los clientes
              <textarea
                rows={4}
                value={form.support_notice ?? ""}
                onChange={(e) => setForm({ ...form, support_notice: e.target.value || null })}
                placeholder="El soporte técnico se gestiona exclusivamente mediante tickets…"
              />
            </label>
          </div>
        </section>

        <section className="card settings-section">
          <h3>Condiciones de uso adicionales (ToS)</h3>
          <p className="muted small">
            Texto libre de condiciones de uso / fair-use adicionales visible para los tenants
            en su página de cuenta. Deja en blanco para no mostrar nada.
          </p>
          <label className="form-grid-full">
            <textarea
              rows={6}
              value={form.tos_notice ?? ""}
              onChange={(e) => setForm({ ...form, tos_notice: e.target.value || null })}
              placeholder="Indica aquí las condiciones de uso adicionales, restricciones de fair-use, etc."
            />
          </label>
        </section>

        {data && (
          <p className="muted small" style={{ marginBottom: "0.5rem" }}>
            Última actualización: {new Date(data.updated_at).toLocaleString("es-ES")}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Guardando…" : "Guardar políticas"}
        </button>
      </form>
    </>
  );
}
