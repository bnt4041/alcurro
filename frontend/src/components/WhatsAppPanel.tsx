import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

interface WhatsAppStatus {
  connected: boolean;
  configured: boolean;
  message: string | null;
}

export default function WhatsAppPanel({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get<WhatsAppStatus>("/tenants/current/whatsapp/status");
      setStatus(data);
    } catch {
      setError("No se pudo comprobar el estado de WhatsApp");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <p className="muted">Comprobando WhatsApp…</p>;
  }

  if (error) {
    return <div className="alert alert-error">{error}</div>;
  }

  if (!status) return null;

  const stClass = status.connected
    ? "wa-status--ok"
    : status.configured
      ? "wa-status--pending"
      : "wa-status--warn";
  const label = status.connected
    ? "Activo"
    : status.configured
      ? "Pendiente de vincular"
      : "No configurado";

  return (
    <div className={`wa-panel ${compact ? "wa-panel--compact" : ""}`}>
      <div className={`wa-status ${stClass}`}>
        <span className="wa-status__dot" aria-hidden />
        <div>
          <strong>WhatsApp de alcurro — {label}</strong>
          <p className="muted small">{status.message}</p>
        </div>
      </div>
      <p className="muted small wa-qr__linked">
        Todas las cuentas comparten la misma línea de WhatsApp. No hace falta
        configurar nada aquí: el administrador de alcurro gestiona la vinculación
        desde el panel de plataforma. Asegúrate de que cada empleado tenga su
        teléfono móvil registrado en el sistema.
      </p>
    </div>
  );
}
