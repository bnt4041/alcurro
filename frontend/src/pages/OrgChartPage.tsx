import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { OrgChartNode } from "../api/types";
import PageHeader from "../components/PageHeader";

const ROLE_LABELS: Record<string, string> = {
  employee: "Empleado",
  manager: "Responsable",
  tenant_admin: "Administrador",
  labor_inspector: "Inspector",
  supervisor: "Supervisor",
  admin: "Admin",
};

function OrgNode({ node, depth = 0 }: { node: OrgChartNode; depth?: number }) {
  const [collapsed, setCollapsed] = useState(false);
  const hasChildren = node.children.length > 0;

  return (
    <div className={`org-node org-node--depth-${Math.min(depth, 4)}`}>
      <div className="org-card">
        {node.avatar_url ? (
          <img src={node.avatar_url} alt={node.full_name} className="org-card__avatar" />
        ) : (
          <div className="org-card__avatar org-card__avatar--placeholder">
            {node.full_name.charAt(0).toUpperCase()}
          </div>
        )}
        <div className="org-card__info">
          <span className="org-card__name">{node.full_name}</span>
          {node.job_title && <span className="org-card__title">{node.job_title}</span>}
          <span className="org-card__role">{ROLE_LABELS[node.role] ?? node.role}</span>
        </div>
        {hasChildren && (
          <button
            type="button"
            className="org-card__toggle"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expandir" : "Colapsar"}
          >
            {collapsed ? "+" : "−"}
          </button>
        )}
      </div>
      {hasChildren && !collapsed && (
        <div className="org-children">
          {node.children.map((child) => (
            <OrgNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function OrgChartPage() {
  const [roots, setRoots] = useState<OrgChartNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<OrgChartNode[]>("/employees/org-chart")
      .then(setRoots)
      .catch(() => setError("No se pudo cargar el organigrama"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <PageHeader title="Organigrama" />
      {loading && <p>Cargando…</p>}
      {error && <p className="alert alert-error">{error}</p>}
      {!loading && roots.length === 0 && !error && (
        <p className="text-muted">No hay empleados activos o ninguno tiene supervisor asignado.</p>
      )}
      <div className="org-chart">
        {roots.map((root) => (
          <OrgNode key={root.id} node={root} />
        ))}
      </div>
    </div>
  );
}
