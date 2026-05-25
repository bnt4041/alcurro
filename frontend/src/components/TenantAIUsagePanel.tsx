import { useEffect, useState } from "react";
import { api } from "../api/client";

interface UsageDetail {
  tenant_id: string;
  period_label: string;
  request_count: number;
  total_tokens: number;
  total_duration_ms: number;
  by_action: { action_code: string; count: number; tokens: number }[];
  by_profile: { profile_key: string; count: number; tokens: number }[];
  recent: {
    created_at: string;
    action_code: string | null;
    profile_key: string | null;
    total_tokens: number;
    duration_ms: number;
    model: string;
    success: boolean;
  }[];
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} s`;
  return `${Math.floor(s / 60)} min ${s % 60} s`;
}

export default function TenantAIUsagePanel({ tenantId }: { tenantId: string }) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<UsageDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<UsageDetail>(
        `/platform/ai/usage/tenants/${tenantId}?days=${days}`
      )
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [tenantId, days]);

  if (loading) return <p className="muted">Cargando uso de IA…</p>;
  if (!data) return <p className="muted">Sin datos de uso de IA.</p>;

  return (
    <div className="tenant-ai-usage">
      <div className="toolbar">
        <label className="inline-label">
          Periodo
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>7 días</option>
            <option value={30}>30 días</option>
            <option value={90}>90 días</option>
          </select>
        </label>
      </div>
      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-label">Peticiones</span>
          <strong>{data.request_count}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Tokens totales</span>
          <strong>{data.total_tokens.toLocaleString("es-ES")}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Tiempo IA</span>
          <strong>{formatDuration(data.total_duration_ms)}</strong>
        </div>
      </div>
      {data.by_action.length > 0 && (
        <>
          <h4>Por acción</h4>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Acción</th>
                  <th>Peticiones</th>
                  <th>Tokens</th>
                </tr>
              </thead>
              <tbody>
                {data.by_action.map((a) => (
                  <tr key={a.action_code}>
                    <td>{a.action_code}</td>
                    <td>{a.count}</td>
                    <td>{a.tokens.toLocaleString("es-ES")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {data.recent.length > 0 && (
        <>
          <h4>Últimas peticiones</h4>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Acción</th>
                  <th>Perfil</th>
                  <th>Tokens</th>
                  <th>Tiempo</th>
                </tr>
              </thead>
              <tbody>
                {data.recent.map((r, i) => (
                  <tr key={i}>
                    <td>
                      {new Date(r.created_at).toLocaleString("es-ES")}
                    </td>
                    <td>{r.action_code ?? "—"}</td>
                    <td>{r.profile_key ?? "—"}</td>
                    <td>{r.total_tokens}</td>
                    <td>{formatDuration(r.duration_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
