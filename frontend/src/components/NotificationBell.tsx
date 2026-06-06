import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { AppNotification } from "../api/types";

const EVENT_LABELS: Record<string, string> = {
  clock_in: "Fichaje entrada",
  clock_out: "Fichaje salida",
  leave_request: "Vacaciones",
  incident: "Incidencia",
  document: "Documento",
};

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "ahora";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

export default function NotificationBell() {
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchCount = useCallback(async () => {
    try {
      const data = await api.get<{ count: number }>("/notifications/unread-count");
      setCount(data.count);
    } catch {
      /* silencioso */
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const id = setInterval(fetchCount, 30_000);
    return () => clearInterval(id);
  }, [fetchCount]);

  // Cerrar al hacer clic fuera
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  async function togglePanel() {
    if (!open) {
      setLoading(true);
      try {
        const data = await api.get<AppNotification[]>("/notifications?limit=20");
        setNotifications(data);
      } catch {
        /* silencioso */
      } finally {
        setLoading(false);
      }
    }
    setOpen((v) => !v);
  }

  async function handleClick(n: AppNotification) {
    if (!n.read_at) {
      await api.post(`/notifications/${n.id}/read`, {});
      setNotifications((prev) =>
        prev.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x))
      );
      setCount((c) => Math.max(0, c - 1));
    }
    setOpen(false);
    if (n.link) navigate(n.link);
  }

  async function markAll() {
    await api.post("/notifications/read-all", {});
    setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })));
    setCount(0);
  }

  return (
    <div className="notif-bell" ref={panelRef}>
      <button
        type="button"
        className={`notif-bell__btn${count > 0 ? " notif-bell__btn--active" : ""}`}
        onClick={togglePanel}
        aria-label="Notificaciones"
        title="Notificaciones"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {count > 0 && (
          <span className="notif-bell__badge">{count > 99 ? "99+" : count}</span>
        )}
      </button>

      {open && (
        <div className="notif-panel">
          <div className="notif-panel__header">
            <span>Notificaciones</span>
            {count > 0 && (
              <button type="button" className="notif-panel__mark-all" onClick={markAll}>
                Marcar todas
              </button>
            )}
          </div>

          {loading && <p className="notif-panel__empty">Cargando…</p>}
          {!loading && notifications.length === 0 && (
            <p className="notif-panel__empty">Sin notificaciones</p>
          )}
          {!loading && notifications.map((n) => (
            <button
              key={n.id}
              type="button"
              className={`notif-item${n.read_at ? " notif-item--read" : ""}`}
              onClick={() => handleClick(n)}
            >
              <span className="notif-item__tag">{EVENT_LABELS[n.event_type] ?? n.event_type}</span>
              <span className="notif-item__title">{n.title}</span>
              <span className="notif-item__body">{n.body}</span>
              <span className="notif-item__time">{timeAgo(n.created_at)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
