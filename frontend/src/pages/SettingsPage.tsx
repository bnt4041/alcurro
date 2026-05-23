import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConnectionTest, SystemSettings } from "../api/types";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";

export default function SettingsPage() {
  const { user } = useAuth();
  const canAdmin = user && canModule(user.permissions, "admin", "settings");
  const [form, setForm] = useState<SystemSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [ollamaTest, setOllamaTest] = useState<ConnectionTest | null>(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setForm(await api.get<SystemSettings>("/settings"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setMsg("");
    try {
      const updated = await api.put<SystemSettings>("/settings", {
        company_name: form.company_name,
        ollama_base_url: form.ollama_base_url,
        ollama_model: form.ollama_model,
      });
      setForm(updated);
      setMsg("Configuración guardada");
    } catch (err) {
      setMsg(String(err));
    } finally {
      setSaving(false);
    }
  };

  const testOllama = async () => {
    setOllamaTest(await api.post<ConnectionTest>("/settings/test/ollama", {}));
  };

  if (!form) return <p className="muted">Cargando configuración…</p>;

  return (
    <>
      <PageHeader
        title="Configuración"
        subtitle="Ollama y datos de empresa"
      />
      {msg && (
        <div
          className={`alert ${msg.includes("guardada") ? "alert-ok" : "alert-error"}`}
        >
          {msg}
        </div>
      )}
      <form onSubmit={save} className="settings-grid">
        <section className="card">
          <h3>Empresa</h3>
          <label>
            Nombre
            <input
              disabled={!canAdmin}
              value={form.company_name}
              onChange={(ev) =>
                setForm({ ...form, company_name: ev.target.value })
              }
            />
          </label>
        </section>
        <section className="card">
          <h3>Ollama — IA local</h3>
          <label>
            URL base
            <input
              value={form.ollama_base_url}
              onChange={(ev) =>
                setForm({ ...form, ollama_base_url: ev.target.value })
              }
            />
          </label>
          <label>
            Modelo
            <input
              value={form.ollama_model}
              onChange={(ev) => setForm({ ...form, ollama_model: ev.target.value })}
            />
          </label>
          <div className="test-row">
            <button type="button" className="btn" onClick={testOllama}>
              Probar Ollama
            </button>
            {ollamaTest && (
              <span className={ollamaTest.ok ? "test-ok" : "test-fail"}>
                {ollamaTest.message}
              </span>
            )}
          </div>
        </section>
        <div className="settings-footer">
          <p className="muted small">
            Última actualización:{" "}
            {new Date(form.updated_at).toLocaleString("es-ES")}
          </p>
          {canAdmin ? (
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Guardando…" : "Guardar configuración"}
          </button>
          ) : (
            <span className="muted">Solo administradores pueden modificar</span>
          )}
        </div>
      </form>
    </>
  );
}
