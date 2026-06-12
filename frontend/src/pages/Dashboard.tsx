import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DailyCount { date: string; count: number }
interface RecentClockIn { id: string; employee_name: string; entrada_at: string; salida_at: string | null }
interface RecentLeave { id: string; employee_name: string; start_date: string; end_date: string; days: number }
interface RecentIncident { id: string; title: string; employee_name: string; created_at: string; managed: boolean }

interface DashboardStats {
  employees: number;
  clockins_today: number;
  pending_leaves: number;
  open_incidents: number;
  pending_signatures: number;
  documents: number;
  clockins_by_day: DailyCount[];
  recent_clockins: RecentClockIn[];
  pending_leaves_list: RecentLeave[];
  recent_incidents: RecentIncident[];
}

type WidgetSize = 1 | 2 | 3 | 4;
type WidgetType =
  | "stat_employees"
  | "stat_clockins_today"
  | "stat_pending_leaves"
  | "stat_open_incidents"
  | "stat_pending_sigs"
  | "stat_documents"
  | "chart_clockins_week"
  | "list_recent_clockins"
  | "list_pending_leaves"
  | "list_recent_incidents"
  | "quick_links";

interface WidgetConfig { id: string; type: WidgetType; size: WidgetSize }

// ─── Widget metadata ──────────────────────────────────────────────────────────

const WIDGET_META: Record<WidgetType, { title: string; description: string; icon: string; defaultSize: WidgetSize }> = {
  stat_employees:        { title: "Empleados activos",     description: "Total de empleados activos en la empresa",               icon: "group",            defaultSize: 1 },
  stat_clockins_today:   { title: "Fichajes hoy",          description: "Número de fichajes registrados hoy",                     icon: "schedule",         defaultSize: 1 },
  stat_pending_leaves:   { title: "Permisos pendientes",   description: "Solicitudes de vacaciones o permisos sin respuesta",     icon: "beach_access",     defaultSize: 1 },
  stat_open_incidents:   { title: "Incidencias abiertas",  description: "Incidencias sin gestionar",                              icon: "warning",          defaultSize: 1 },
  stat_pending_sigs:     { title: "Firmas pendientes",     description: "Documentos a la espera de firma electrónica",            icon: "draw",             defaultSize: 1 },
  stat_documents:        { title: "Documentos",            description: "Total de documentos entregados a empleados",             icon: "folder",           defaultSize: 1 },
  chart_clockins_week:   { title: "Fichajes última semana",description: "Gráfica de fichajes por día en los últimos 7 días",     icon: "bar_chart",        defaultSize: 2 },
  list_recent_clockins:  { title: "Últimos fichajes",      description: "Los fichajes más recientes registrados",                 icon: "history",          defaultSize: 2 },
  list_pending_leaves:   { title: "Permisos por aprobar",  description: "Solicitudes de permisos pendientes de aprobación",      icon: "pending_actions",  defaultSize: 2 },
  list_recent_incidents: { title: "Incidencias recientes", description: "Últimas incidencias registradas",                       icon: "report_problem",   defaultSize: 2 },
  quick_links:           { title: "Accesos rápidos",       description: "Atajos a las secciones más usadas",                     icon: "apps",             defaultSize: 4 },
};

const STORAGE_KEY = "dashboard_config_v2";

const DEFAULT_CONFIG: WidgetConfig[] = [
  { id: "w1",  type: "stat_employees",        size: 1 },
  { id: "w2",  type: "stat_clockins_today",   size: 1 },
  { id: "w3",  type: "stat_pending_leaves",   size: 1 },
  { id: "w4",  type: "stat_open_incidents",   size: 1 },
  { id: "w5",  type: "stat_pending_sigs",     size: 1 },
  { id: "w6",  type: "stat_documents",        size: 1 },
  { id: "w7",  type: "chart_clockins_week",   size: 2 },
  { id: "w8",  type: "list_pending_leaves",   size: 2 },
  { id: "w9",  type: "list_recent_clockins",  size: 2 },
  { id: "w10", type: "list_recent_incidents", size: 2 },
  { id: "w11", type: "quick_links",           size: 4 },
];

function loadConfig(): WidgetConfig[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as WidgetConfig[];
  } catch {}
  return DEFAULT_CONFIG;
}

function saveConfig(cfg: WidgetConfig[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
}

// ─── Bar chart ────────────────────────────────────────────────────────────────

const DAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"];

function BarChart({ data }: { data: DailyCount[] }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  const todayStr = new Date().toISOString().split("T")[0];
  return (
    <div className="dash-barchart">
      {data.map((d) => {
        const dt = new Date(d.date + "T12:00:00");
        const dayIdx = (dt.getDay() + 6) % 7;
        const pct = Math.round((d.count / max) * 100);
        const isToday = d.date === todayStr;
        return (
          <div key={d.date} className="dash-barchart__col">
            <span className="dash-barchart__count">{d.count > 0 ? d.count : ""}</span>
            <div className="dash-barchart__track">
              <div
                className={`dash-barchart__bar${isToday ? " is-today" : ""}`}
                style={{ height: `${pct}%` }}
              />
            </div>
            <span className="dash-barchart__label">{DAY_LABELS[dayIdx]}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Individual widgets ───────────────────────────────────────────────────────

function StatWidget({
  icon, label, value, to, accent,
}: {
  icon: string; label: string; value: number | undefined; to: string; accent?: string;
}) {
  return (
    <Link to={to} className="dash-stat">
      <span className={`dash-stat__icon material-symbols-outlined${accent ? ` ${accent}` : ""}`}>{icon}</span>
      <span className="dash-stat__value">{value ?? "—"}</span>
      <span className="dash-stat__label">{label}</span>
    </Link>
  );
}

function fmtTime(iso: string) {
  return iso.substring(11, 16);
}
function fmtDate(iso: string) {
  return iso.substring(0, 10).split("-").reverse().join("/");
}

function ListClockIns({ data }: { data: RecentClockIn[] }) {
  if (!data.length) return <p className="dash-list__empty">Sin fichajes recientes</p>;
  return (
    <ul className="dash-list">
      {data.map((r) => (
        <li key={r.id} className="dash-list__row">
          <span className="dash-list__name">{r.employee_name}</span>
          <span className="dash-list__meta">
            {fmtDate(r.entrada_at)} · {fmtTime(r.entrada_at)}
            {r.salida_at ? ` → ${fmtTime(r.salida_at)}` : <span className="dash-list__badge dash-list__badge--open">en curso</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function ListPendingLeaves({ data }: { data: RecentLeave[] }) {
  if (!data.length) return <p className="dash-list__empty">Sin solicitudes pendientes</p>;
  return (
    <ul className="dash-list">
      {data.map((r) => (
        <li key={r.id} className="dash-list__row">
          <span className="dash-list__name">{r.employee_name}</span>
          <span className="dash-list__meta">
            {fmtDate(r.start_date)} → {fmtDate(r.end_date)} · {r.days}d
          </span>
        </li>
      ))}
    </ul>
  );
}

function ListIncidents({ data }: { data: RecentIncident[] }) {
  if (!data.length) return <p className="dash-list__empty">Sin incidencias recientes</p>;
  return (
    <ul className="dash-list">
      {data.map((r) => (
        <li key={r.id} className="dash-list__row">
          <span className="dash-list__name">{r.title}</span>
          <span className="dash-list__meta">
            {r.employee_name} · {fmtDate(r.created_at)}
            {!r.managed && <span className="dash-list__badge dash-list__badge--warn">sin gestionar</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}

const QUICK_LINKS = [
  { icon: "person_add",    label: "Alta de empleado",       to: "/app/empleados" },
  { icon: "schedule",      label: "Consultar fichajes",      to: "/app/fichajes" },
  { icon: "beach_access",  label: "Aprobar permisos",        to: "/app/vacaciones" },
  { icon: "report_problem",label: "Ver incidencias",         to: "/app/incidencias" },
  { icon: "draw",          label: "Firmas pendientes",       to: "/app/firmas" },
  { icon: "folder",        label: "Documentos",              to: "/app/documentos" },
  { icon: "groups",        label: "Organización",            to: "/app/organizacion" },
  { icon: "manage_accounts",label: "Mi cuenta",              to: "/app/cuenta" },
];

function QuickLinks() {
  return (
    <div className="dash-quicklinks">
      {QUICK_LINKS.map((l) => (
        <Link key={l.to} to={l.to} className="dash-ql-btn">
          <span className="material-symbols-outlined">{l.icon}</span>
          <span>{l.label}</span>
        </Link>
      ))}
    </div>
  );
}

// ─── Widget shell ─────────────────────────────────────────────────────────────

function Widget({
  cfg,
  stats,
  editMode,
  onRemove,
  onResize,
  onMove,
  isFirst,
  isLast,
}: {
  cfg: WidgetConfig;
  stats: DashboardStats | null;
  editMode: boolean;
  onRemove: () => void;
  onResize: (delta: -1 | 1) => void;
  onMove: (delta: -1 | 1) => void;
  isFirst: boolean;
  isLast: boolean;
}) {
  const meta = WIDGET_META[cfg.type];

  const content = (() => {
    switch (cfg.type) {
      case "stat_employees":
        return <StatWidget icon="group" label="Empleados activos" value={stats?.employees} to="/app/empleados" />;
      case "stat_clockins_today":
        return <StatWidget icon="schedule" label="Fichajes hoy" value={stats?.clockins_today} to="/app/fichajes" />;
      case "stat_pending_leaves":
        return <StatWidget icon="beach_access" label="Permisos pendientes" value={stats?.pending_leaves} to="/app/vacaciones" accent={stats?.pending_leaves ? "accent-warn" : undefined} />;
      case "stat_open_incidents":
        return <StatWidget icon="warning" label="Incidencias abiertas" value={stats?.open_incidents} to="/app/incidencias" accent={stats?.open_incidents ? "accent-warn" : undefined} />;
      case "stat_pending_sigs":
        return <StatWidget icon="draw" label="Firmas pendientes" value={stats?.pending_signatures} to="/app/firmas" accent={stats?.pending_signatures ? "accent-warn" : undefined} />;
      case "stat_documents":
        return <StatWidget icon="folder" label="Documentos" value={stats?.documents} to="/app/documentos" />;
      case "chart_clockins_week":
        return stats ? <BarChart data={stats.clockins_by_day} /> : null;
      case "list_recent_clockins":
        return <ListClockIns data={stats?.recent_clockins ?? []} />;
      case "list_pending_leaves":
        return <ListPendingLeaves data={stats?.pending_leaves_list ?? []} />;
      case "list_recent_incidents":
        return <ListIncidents data={stats?.recent_incidents ?? []} />;
      case "quick_links":
        return <QuickLinks />;
    }
  })();

  const isStat = cfg.type.startsWith("stat_");

  return (
    <div
      className={`dash-widget${editMode ? " is-editing" : ""}${isStat ? " dash-widget--stat" : ""}`}
      data-size={cfg.size}
    >
      {!isStat && (
        <div className="dash-widget__header">
          <span className="material-symbols-outlined dash-widget__icon">{meta.icon}</span>
          <span className="dash-widget__title">{meta.title}</span>
          {!cfg.type.startsWith("stat_") && cfg.type !== "quick_links" && (
            <Link to={linkForType(cfg.type)} className="dash-widget__see-all">Ver todo</Link>
          )}
        </div>
      )}
      <div className="dash-widget__body">{content}</div>

      {editMode && (
        <div className="dash-widget__edit-overlay">
          <div className="dash-widget__edit-title">{meta.title}</div>
          <div className="dash-widget__edit-controls">
            <button type="button" className="dash-edit-btn" title="Mover izquierda" disabled={isFirst} onClick={() => onMove(-1)}>
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <button type="button" className="dash-edit-btn" title="Mover derecha" disabled={isLast} onClick={() => onMove(1)}>
              <span className="material-symbols-outlined">arrow_forward</span>
            </button>
            <button type="button" className="dash-edit-btn" title="Reducir" disabled={cfg.size <= 1} onClick={() => onResize(-1)}>
              <span className="material-symbols-outlined">remove</span>
            </button>
            <div className="dash-size-label">{cfg.size}</div>
            <button type="button" className="dash-edit-btn" title="Ampliar" disabled={cfg.size >= 4} onClick={() => onResize(1)}>
              <span className="material-symbols-outlined">add</span>
            </button>
            <button type="button" className="dash-edit-btn dash-edit-btn--remove" title="Eliminar widget" onClick={onRemove}>
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function linkForType(type: WidgetType): string {
  switch (type) {
    case "list_recent_clockins":  return "/app/fichajes";
    case "list_pending_leaves":   return "/app/vacaciones";
    case "list_recent_incidents": return "/app/incidencias";
    default: return "/app";
  }
}

// ─── Add widget panel ─────────────────────────────────────────────────────────

function AddWidgetPanel({
  existing,
  onAdd,
  onClose,
}: {
  existing: WidgetType[];
  onAdd: (type: WidgetType) => void;
  onClose: () => void;
}) {
  const allTypes = Object.keys(WIDGET_META) as WidgetType[];

  return (
    <div className="dash-add-panel">
      <div className="dash-add-panel__backdrop" onClick={onClose} />
      <div className="dash-add-panel__drawer">
        <div className="dash-add-panel__header">
          <span className="dash-add-panel__title">Añadir widget</span>
          <button type="button" className="dash-edit-btn" onClick={onClose}>
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <div className="dash-add-panel__list">
          {allTypes.map((type) => {
            const meta = WIDGET_META[type];
            const used = existing.includes(type);
            return (
              <div key={type} className={`dash-add-item${used ? " is-used" : ""}`}>
                <span className="material-symbols-outlined dash-add-item__icon">{meta.icon}</span>
                <div className="dash-add-item__text">
                  <strong>{meta.title}</strong>
                  <span>{meta.description}</span>
                </div>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={used}
                  onClick={() => { onAdd(type); onClose(); }}
                >
                  {used ? "Añadido" : "Añadir"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [config, setConfig] = useState<WidgetConfig[]>(loadConfig);
  const [editMode, setEditMode] = useState(false);
  const [addPanelOpen, setAddPanelOpen] = useState(false);
  const [error, setError] = useState("");
  const idCounterRef = useRef(100);

  const loadStats = useCallback(async () => {
    try {
      const data = await api.get<DashboardStats>("/dashboard/stats");
      setStats(data);
    } catch (err) {
      setError(String(err));
    }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const updateConfig = (next: WidgetConfig[]) => {
    setConfig(next);
    saveConfig(next);
  };

  const removeWidget = (id: string) => updateConfig(config.filter((w) => w.id !== id));

  const resizeWidget = (id: string, delta: -1 | 1) => {
    updateConfig(config.map((w) => {
      if (w.id !== id) return w;
      const next = Math.max(1, Math.min(4, w.size + delta)) as WidgetSize;
      return { ...w, size: next };
    }));
  };

  const moveWidget = (id: string, delta: -1 | 1) => {
    const idx = config.findIndex((w) => w.id === id);
    if (idx < 0) return;
    const next = [...config];
    const swapIdx = idx + delta;
    if (swapIdx < 0 || swapIdx >= next.length) return;
    [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
    updateConfig(next);
  };

  const addWidget = (type: WidgetType) => {
    idCounterRef.current += 1;
    const meta = WIDGET_META[type];
    updateConfig([...config, { id: `custom_${idCounterRef.current}`, type, size: meta.defaultSize }]);
  };

  const resetConfig = () => {
    updateConfig(DEFAULT_CONFIG);
    setEditMode(false);
  };

  return (
    <>
      <div className="dash-topbar">
        <div className="dash-topbar__greeting">
          <span className="material-symbols-outlined">waving_hand</span>
          <span>Hola, <strong>{user?.full_name ?? user?.tenant_name ?? "admin"}</strong></span>
        </div>
        <div className="dash-topbar__actions">
          {editMode && (
            <>
              <button type="button" className="btn btn-sm" onClick={() => setAddPanelOpen(true)}>
                <span className="material-symbols-outlined">add</span>
                Añadir widget
              </button>
              <button type="button" className="btn btn-sm" onClick={resetConfig}>
                <span className="material-symbols-outlined">restart_alt</span>
                Restablecer
              </button>
            </>
          )}
          <button
            type="button"
            className={`btn btn-sm${editMode ? " btn-primary" : ""}`}
            onClick={() => setEditMode((v) => !v)}
          >
            <span className="material-symbols-outlined">{editMode ? "check" : "tune"}</span>
            {editMode ? "Guardar panel" : "Personalizar"}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="dash-grid">
        {config.map((cfg, idx) => (
          <Widget
            key={cfg.id}
            cfg={cfg}
            stats={stats}
            editMode={editMode}
            onRemove={() => removeWidget(cfg.id)}
            onResize={(d) => resizeWidget(cfg.id, d)}
            onMove={(d) => moveWidget(cfg.id, d)}
            isFirst={idx === 0}
            isLast={idx === config.length - 1}
          />
        ))}

        {editMode && (
          <div className="dash-widget dash-widget--add" data-size="1" onClick={() => setAddPanelOpen(true)}>
            <span className="material-symbols-outlined">add_circle</span>
            <span>Añadir widget</span>
          </div>
        )}
      </div>

      {addPanelOpen && (
        <AddWidgetPanel
          existing={config.map((c) => c.type)}
          onAdd={addWidget}
          onClose={() => setAddPanelOpen(false)}
        />
      )}
    </>
  );
}
