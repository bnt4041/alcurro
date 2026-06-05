import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";

interface AiProfile {
  key: string;
  label: string;
}

interface AiAction {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
}

interface MatrixRow {
  action: AiAction;
  profiles: { profile_key: string; enabled: boolean }[];
}

interface AiRule {
  id: string;
  title: string;
  content: string;
  priority: number;
  is_active: boolean;
}

interface TenantUsage {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  request_count: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_duration_ms: number;
  last_used_at: string | null;
}

interface Overview {
  profiles: AiProfile[];
  action_matrix: MatrixRow[];
  rules: AiRule[];
  tenant_usage: TenantUsage[];
}

type Tab = "actions" | "rules" | "usage";

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} s`;
  return `${Math.floor(s / 60)} min ${s % 60} s`;
}

export default function PlatformAIPage() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("actions");
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [matrix, setMatrix] = useState<MatrixRow[]>([]);
  const [rules, setRules] = useState<AiRule[]>([]);
  const [usage, setUsage] = useState<TenantUsage[]>([]);
  const [savingMatrix, setSavingMatrix] = useState(false);
  const [newRule, setNewRule] = useState({
    title: "",
    content: "",
    priority: 100,
  });

  const load = useCallback(async () => {
    const data = await api.get<Overview>(`/platform/ai/overview?days=${days}`);
    setOverview(data);
    setMatrix(data.action_matrix);
    setRules(data.rules);
    setUsage(data.tenant_usage);
  }, [days]);

  useEffect(() => {
    load().catch((e) => toast.error(String(e)));
  }, [load, toast]);

  const toggleCell = (actionId: string, profileKey: string) => {
    setMatrix((prev) =>
      prev.map((row) =>
        row.action.id !== actionId
          ? row
          : {
              ...row,
              profiles: row.profiles.map((p) =>
                p.profile_key === profileKey
                  ? { ...p, enabled: !p.enabled }
                  : p
              ),
            }
      )
    );
  };

  const saveMatrix = async () => {
    setSavingMatrix(true);
    try {
      const cells = matrix.flatMap((row) =>
        row.profiles.map((p) => ({
          action_id: row.action.id,
          profile_key: p.profile_key,
          enabled: p.enabled,
        }))
      );
      const updated = await api.put<MatrixRow[]>("/platform/ai/actions/matrix", {
        cells,
      });
      setMatrix(updated);
      toast.success("Matriz de acciones guardada");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setSavingMatrix(false);
    }
  };

  const addRule = async (e: FormEvent) => {
    e.preventDefault();
    if (!newRule.title.trim() || !newRule.content.trim()) return;
    try {
      await api.post("/platform/ai/rules", newRule);
      setNewRule({ title: "", content: "", priority: 100 });
      await load();
      toast.success("Regla añadida");
    } catch (err) {
      toast.error(String(err));
    }
  };

  const moveRule = async (index: number, dir: -1 | 1) => {
    const next = [...rules];
    const target = index + dir;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setRules(next);
    try {
      const reordered = await api.post<AiRule[]>("/platform/ai/rules/reorder", {
        rule_ids: next.map((r) => r.id),
      });
      setRules(reordered);
    } catch (err) {
      toast.error(String(err));
      load();
    }
  };

  const deleteRule = async (id: string) => {
    if (!confirm("¿Eliminar esta regla?")) return;
    await api.delete(`/platform/ai/rules/${id}`);
    load();
  };

  const profiles = overview?.profiles ?? [];

  type UsageTableRow = TenantUsage & {
    tokens_label: string;
    prompt_label: string;
    completion_label: string;
    duration_label: string;
    last_used_label: string;
  };

  const usageTableData = useMemo<UsageTableRow[]>(
    () =>
      usage.map((u) => ({
        ...u,
        tokens_label: u.total_tokens.toLocaleString("es-ES"),
        prompt_label: u.prompt_tokens.toLocaleString("es-ES"),
        completion_label: u.completion_tokens.toLocaleString("es-ES"),
        duration_label: formatDuration(u.total_duration_ms),
        last_used_label: u.last_used_at
          ? new Date(u.last_used_at).toLocaleString("es-ES")
          : "—",
      })),
    [usage]
  );

  const usageColumns = useMemo<DataTableColumn<UsageTableRow>[]>(
    () => [
      {
        title: "Cuenta",
        field: "tenant_name",
        headerFilter: "input",
        minWidth: 160,
        formatter: (cell) => {
          const r = cell.getRow().getData() as UsageTableRow;
          return `<strong>${r.tenant_name}</strong><div class="muted small">${r.tenant_slug}</div>`;
        },
      },
      { title: "Peticiones", field: "request_count", headerFilter: "number", width: 100 },
      { title: "Tokens", field: "tokens_label", headerFilter: "input", width: 100 },
      { title: "Prompt", field: "prompt_label", headerFilter: "input", width: 100 },
      { title: "Respuesta", field: "completion_label", headerFilter: "input", width: 100 },
      { title: "Tiempo IA", field: "duration_label", headerFilter: "input", width: 110 },
      { title: "Último uso", field: "last_used_label", headerFilter: "input", minWidth: 150 },
    ],
    []
  );

  return (
    <>
      <PageHeader
        title="Inteligencia artificial"
        subtitle="Acciones por perfil, reglas conversacionales y consumo por cuenta"
      />
      <p className="muted small" style={{ marginBottom: "1rem", maxWidth: "52rem" }}>
        La matriz define qué puede hacer cada <strong>perfil IA</strong> por WhatsApp.
        Además, cada empleado debe tener los permisos equivalentes en los{" "}
        <strong>grupos del tenant</strong> (RBAC). Ollama recibe reglas, contexto del
        empleado y hasta 12 mensajes recientes. Documentación:{" "}
        <code>docs/AI_WHATSAPP.md</code> en el repositorio.
      </p>

      <div className="toolbar" style={{ marginBottom: "0.75rem" }}>
        <label className="inline-label">
          Periodo uso
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>7 días</option>
            <option value={30}>30 días</option>
            <option value={90}>90 días</option>
          </select>
        </label>
      </div>

      <div className="tabs">
        <button
          type="button"
          className={tab === "actions" ? "tab active" : "tab"}
          onClick={() => setTab("actions")}
        >
          Acciones por perfil
        </button>
        <button
          type="button"
          className={tab === "rules" ? "tab active" : "tab"}
          onClick={() => setTab("rules")}
        >
          Reglas conversacionales
        </button>
        <button
          type="button"
          className={tab === "usage" ? "tab active" : "tab"}
          onClick={() => setTab("usage")}
        >
          Uso por cuenta
        </button>
      </div>

      {tab === "actions" && (
        <section className="card">
          <p className="muted small">
            Marca qué acciones puede ejecutar la IA (WhatsApp / Ollama) según el
            tipo de usuario. Los cambios aplican a todas las cuentas.
          </p>
          <div className="table-wrap">
            <table className="matrix-table">
              <thead>
                <tr>
                  <th>Acción</th>
                  {profiles.map((p) => (
                    <th key={p.key} className="matrix-col">
                      {p.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row) => (
                  <tr key={row.action.id}>
                    <td>
                      <strong>{row.action.name}</strong>
                      <div className="muted small">{row.action.code}</div>
                    </td>
                    {row.profiles.map((cell) => (
                      <td key={cell.profile_key} className="matrix-cell">
                        <input
                          type="checkbox"
                          checked={cell.enabled}
                          onChange={() =>
                            toggleCell(row.action.id, cell.profile_key)
                          }
                          aria-label={`${row.action.name} — ${cell.profile_key}`}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={savingMatrix}
            onClick={saveMatrix}
          >
            {savingMatrix ? "Guardando…" : "Guardar matriz"}
          </button>
        </section>
      )}

      {tab === "rules" && (
        <div className="grid-2">
          <section className="card">
            <h3>Reglas activas (orden = prioridad)</h3>
            <p className="muted small">
              Las reglas con menor número se aplican antes en el prompt del
              sistema. Usa ↑↓ para reordenar.
            </p>
            <ul className="simple-list">
              {rules.map((r, i) => (
                <li key={r.id} className="rule-row">
                  <div>
                    <strong>
                      {r.priority}. {r.title}
                    </strong>
                    <p className="muted small">{r.content}</p>
                  </div>
                  <div className="actions">
                    <button
                      type="button"
                      className="btn btn-icon"
                      disabled={i === 0}
                      onClick={() => moveRule(i, -1)}
                      title="Subir prioridad"
                    ><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6"/></svg></button>
                    <button
                      type="button"
                      className="btn btn-icon"
                      disabled={i === rules.length - 1}
                      onClick={() => moveRule(i, 1)}
                      title="Bajar prioridad"
                    ><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg></button>
                    <button
                      type="button"
                      className="btn btn-icon btn-danger"
                      onClick={() => deleteRule(r.id)}
                      title="Eliminar regla"
                    ><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M10 11v6 M14 11v6"/></svg></button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
          <section className="card">
            <h3>Nueva regla</h3>
            <form onSubmit={addRule} className="form-grid">
              <label>
                Título
                <input
                  required
                  value={newRule.title}
                  onChange={(e) =>
                    setNewRule({ ...newRule, title: e.target.value })
                  }
                />
              </label>
              <label>
                Prioridad (menor = más importante)
                <input
                  type="number"
                  min={0}
                  max={9999}
                  value={newRule.priority}
                  onChange={(e) =>
                    setNewRule({
                      ...newRule,
                      priority: parseInt(e.target.value, 10) || 0,
                    })
                  }
                />
              </label>
              <label className="form-grid-full">
                Contenido
                <textarea
                  required
                  rows={5}
                  value={newRule.content}
                  onChange={(e) =>
                    setNewRule({ ...newRule, content: e.target.value })
                  }
                  placeholder="Ej. Responde siempre en español formal y breve..."
                />
              </label>
              <button type="submit" className="btn btn-primary">
                Añadir regla
              </button>
            </form>
          </section>
        </div>
      )}

      {tab === "usage" && (
        <section className="card">
          <p className="muted small">
            Consumo agregado por cuenta: peticiones, tokens (prompt + respuesta) y
            tiempo de inferencia.
          </p>
          <DataTable
            data={usageTableData}
            columns={usageColumns}
            exportFilename="uso_ia_cuentas"
          />
        </section>
      )}
    </>
  );
}
