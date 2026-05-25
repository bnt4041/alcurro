import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const API = "/api/public/incidencia";

interface PublicMeta {
  title: string;
  description: string | null;
  category: string;
  status: string;
  employee_name: string;
  tenant_name: string;
  original_data: Record<string, unknown>;
  modified_data: Record<string, unknown> | null;
  can_justify: boolean;
}

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers as Record<string, string>),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : res.statusText);
  }
  return res.json() as Promise<T>;
}

export default function JustifyIncidentPage() {
  const { token } = useParams<{ token: string }>();
  const [meta, setMeta] = useState<PublicMeta | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    publicFetch<PublicMeta>(`/${token}`)
      .then(setMeta)
      .catch(() => setMsg("Enlace no válido o caducado"))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setMsg("");
    try {
      await publicFetch(`/${token}/justify`, {
        method: "POST",
        body: JSON.stringify({ justification: text }),
      });
      setDone(true);
      setMsg("Justificación enviada. RRHH la revisará.");
    } catch (err) {
      setMsg(String(err));
    }
  };

  if (loading) return <p className="muted">Cargando…</p>;

  return (
    <div className="public-page">
      <div className="card" style={{ maxWidth: 520, margin: "2rem auto" }}>
        {meta ? (
          <>
            <h1>{meta.title}</h1>
            <p className="muted">
              {meta.tenant_name} · {meta.employee_name}
            </p>
            {meta.description && <p>{meta.description}</p>}
            {meta.original_data && Object.keys(meta.original_data).length > 0 && (
              <details>
                <summary>Datos del registro</summary>
                <pre className="incident-diff-pre">
                  {JSON.stringify(meta.original_data, null, 2)}
                </pre>
              </details>
            )}
            {done ? (
              <div className="alert alert-ok">{msg}</div>
            ) : meta.can_justify ? (
              <form onSubmit={submit}>
                <label>
                  Motivo / justificación
                  <textarea
                    required
                    minLength={3}
                    rows={5}
                    value={text}
                    onChange={(ev) => setText(ev.target.value)}
                    placeholder="Explica el motivo del retraso o la situación…"
                  />
                </label>
                {msg && <div className="alert alert-error">{msg}</div>}
                <button type="submit" className="btn btn-primary">
                  Enviar justificación
                </button>
              </form>
            ) : (
              <p className="muted">
                Esta incidencia ya no admite justificación por este enlace.
              </p>
            )}
          </>
        ) : (
          <div className="alert alert-error">{msg || "Enlace no válido"}</div>
        )}
      </div>
    </div>
  );
}
