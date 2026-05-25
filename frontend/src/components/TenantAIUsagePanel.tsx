import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "./DataTable";

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

type ActionRow = UsageDetail["by_action"][number] & { tokens_label: string };
type RecentRow = UsageDetail["recent"][number] & {
  date_label: string;
  duration_label: string;
};

export default function TenantAIUsagePanel({ tenantId }: { tenantId: string }) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<UsageDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<UsageDetail>(`/platform/ai/usage/tenants/${tenantId}?days=${days}`)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [tenantId, days]);

  const actionData = useMemo<ActionRow[]>(
    () =>
      (data?.by_action ?? []).map((a) => ({
        ...a,
        tokens_label: a.tokens.toLocaleString("es-ES"),
      })),
    [data]
  );

  const recentData = useMemo<RecentRow[]>(
    () =>
      (data?.recent ?? []).map((r) => ({
        ...r,
        date_label: new Date(r.created_at).toLocaleString("es-ES"),
        duration_label: formatDuration(r.duration_ms),
      })),
    [data]
  );

  const actionColumns = useMemo<DataTableColumn<ActionRow>[]>(
    () => [
      { title: "Acción", field: "action_code", headerFilter: "input", minWidth: 140 },
      { title: "Peticiones", field: "count", headerFilter: "number", width: 110 },
      { title: "Tokens", field: "tokens_label", headerFilter: "input", width: 110 },
    ],
    []
  );

  const recentColumns = useMemo<DataTableColumn<RecentRow>[]>(
    () => [
      { title: "Fecha", field: "date_label", headerFilter: "input", minWidth: 150 },
      {
        title: "Acción",
        field: "action_code",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        width: 120,
      },
      {
        title: "Perfil",
        field: "profile_key",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        width: 120,
      },
      { title: "Tokens", field: "total_tokens", headerFilter: "number", width: 90 },
      { title: "Tiempo", field: "duration_label", headerFilter: "input", width: 100 },
    ],
    []
  );

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
      {actionData.length > 0 && (
        <>
          <h4>Por acción</h4>
          <DataTable
            data={actionData}
            columns={actionColumns}
            exportFilename="ia_por_accion"
            height="280px"
          />
        </>
      )}
      {recentData.length > 0 && (
        <>
          <h4>Últimas peticiones</h4>
          <DataTable
            data={recentData}
            columns={recentColumns}
            exportFilename="ia_recientes"
            height="320px"
          />
        </>
      )}
    </div>
  );
}
