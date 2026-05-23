import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConnectionTest, SystemSettings } from "../api/types";
import PageHeader from "../components/PageHeader";

interface WhatsAppSession {
  connected: boolean;
  qr_image: string | null;
  qr_expires_in: number | null;
  message: string | null;
}

export default function PlatformWhatsAppPage() {
  const [form, setForm] = useState<SystemSettings | null>(null);
  const [session, setSession] = useState<WhatsAppSession | null>(null);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [test, setTest] = useState<ConnectionTest | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const loadSettings = useCallback(async () => {
    setForm(await api.get<SystemSettings>("/platform/whatsapp/settings"));
  }, []);

  const loadSession = useCallback(async () => {
    const s = await api.get<WhatsAppSession & { gowa_status?: string }>(
      "/platform/whatsapp/session"
    );
    setSession({
      connected: s.connected,
      qr_image: s.qr_image,
      qr_expires_in: s.qr_expires_in,
      message: s.message,
    });
  }, []);

  const load = useCallback(async () => {
    setError("");
    try {
      await loadSettings();
      await loadSession();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    }
  }, [loadSettings, loadSession]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!session || session.connected || !session.qr_image) return;
    const ms = (session.qr_expires_in ?? 25) * 1000;
    const id = window.setInterval(() => {
      loadSession().catch(() => {});
    }, Math.max(ms - 2000, 15000));
    return () => window.clearInterval(id);
  }, [session?.connected, session?.qr_image, session?.qr_expires_in, loadSession]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setMsg("");
    setError("");
    try {
      const updated = await api.put<SystemSettings>("/platform/whatsapp/settings", {
        gowa_send_url: form.gowa_send_url,
        gowa_basic_auth: form.gowa_basic_auth,
        gowa_webhook_url: form.gowa_webhook_url,
        gowa_ui_url: form.gowa_ui_url,
      });
      setForm(updated);
      setMsg("Configuración guardada");
      await loadSession();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    setTest(await api.post<ConnectionTest>("/platform/whatsapp/test", {}));
  };

  const refreshQr = async () => {
    setRefreshing(true);
    setError("");
    try {
      await loadSession();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setRefreshing(false);
    }
  };

  const openQrTab = () => {
    if (!session?.qr_image) return;
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(`
      <!DOCTYPE html><html><head><meta charset="utf-8"><title>QR WhatsApp — alcurro</title>
      <style>body{font-family:system-ui,sans-serif;text-align:center;padding:2rem;background:#f8fafc}
      img{max-width:min(320px,90vw);border:8px solid #fff;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.12)}</style></head><body>
      <h1>Vincular WhatsApp de alcurro</h1>
      <p>WhatsApp → Dispositivos vinculados → Vincular dispositivo</p>
      <img src="${session.qr_image}" alt="Código QR" />
      </body></html>
    `);
    w.document.close();
  };

  if (!form) {
    return <p className="muted">Cargando WhatsApp…</p>;
  }

  const linked = session?.connected === true;
  const sendUrlLooksLocal =
    form.gowa_send_url.includes("localhost") ||
    form.gowa_send_url.includes("127.0.0.1");

  const applyDockerDefaults = () => {
    setForm({
      ...form,
      gowa_send_url: "http://gowa:3000/send/message",
      gowa_ui_url: "http://localhost:3000",
      gowa_webhook_url: "http://backend:8000/webhook/whatsapp",
    });
  };

  return (
    <>
      <PageHeader
        title="WhatsApp"
        subtitle="Una sola línea compartida por todas las cuentas cliente"
      />

      {error && <div className="alert alert-error">{error}</div>}
      {msg && <div className="alert alert-success">{msg}</div>}

      <section className="card" style={{ marginBottom: "1.5rem" }}>
        <div className={`wa-status ${linked ? "wa-status--ok" : "wa-status--pending"}`}>
          <span className="wa-status__dot" aria-hidden />
          <div>
            <strong>{linked ? "WhatsApp vinculado" : "Pendiente de vincular"}</strong>
            <p className="muted small">
              {session?.message ||
                "Configura goWA y escanea el QR con el móvil de la línea oficial."}
            </p>
          </div>
        </div>

        {!linked && session?.qr_image && (
          <div className="wa-qr" style={{ marginTop: "1rem" }}>
            <p className="wa-qr__title">Vincula el móvil de alcurro</p>
            <p className="muted small">
              Escanea con WhatsApp → Dispositivos vinculados. El código se renueva
              cada {session.qr_expires_in ?? 30} s.
            </p>
            <div className="wa-qr__frame-wrap">
              <img src={session.qr_image} alt="Código QR" className="wa-qr__img" />
            </div>
            <div className="wa-qr__actions">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={refreshing}
                onClick={refreshQr}
              >
                {refreshing ? "Actualizando…" : "Actualizar código"}
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={openQrTab}>
                Abrir en pestaña nueva
              </button>
            </div>
          </div>
        )}

        {!linked && !session?.qr_image && (
          <p className="muted small" style={{ marginTop: "1rem" }}>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={refreshing}
              onClick={refreshQr}
            >
              {refreshing ? "Generando…" : "Generar código QR"}
            </button>
          </p>
        )}
      </section>

      <form className="card form-grid" onSubmit={save}>
        <h3>Conexión goWA</h3>
        <p className="muted small form-grid-full">
          En Docker la URL de envío debe ser{" "}
          <code>http://gowa:3000/send/message</code> (nombre del servicio en la red
          interna). La interfaz web sigue siendo{" "}
          <code>http://localhost:3000</code> en el navegador.
        </p>
        {sendUrlLooksLocal && (
          <div className="alert alert-error form-grid-full">
            La URL de envío apunta a <code>localhost</code>. Desde el backend en Docker
            eso no llega a goWA. Usa <code>http://gowa:3000/send/message</code>.
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ marginLeft: "0.75rem" }}
              onClick={applyDockerDefaults}
            >
              Aplicar valores Docker
            </button>
          </div>
        )}
        <label className="full">
          URL envío (API)
          <input
            value={form.gowa_send_url}
            onChange={(e) => setForm({ ...form, gowa_send_url: e.target.value })}
          />
        </label>
        <label className="full">
          URL interfaz (navegador)
          <input
            value={form.gowa_ui_url}
            onChange={(e) => setForm({ ...form, gowa_ui_url: e.target.value })}
          />
        </label>
        <label className="full">
          Webhook (goWA → backend)
          <input
            value={form.gowa_webhook_url}
            onChange={(e) => setForm({ ...form, gowa_webhook_url: e.target.value })}
          />
        </label>
        <label className="full">
          Basic Auth (usuario:contraseña)
          <input
            value={form.gowa_basic_auth}
            onChange={(e) => setForm({ ...form, gowa_basic_auth: e.target.value })}
          />
        </label>
        <div className="form-actions full">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={runTest}>
            Probar conexión
          </button>
          {test && (
            <span className={test.ok ? "test-ok" : "test-fail"}>{test.message}</span>
          )}
        </div>
      </form>
    </>
  );
}
