import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  platformTicketsApi,
  type PlatformAdminOption,
  type Ticket,
  type TicketDetail,
  type TicketPriority,
  type TicketStatus,
} from "../api/tickets";

const STATUS_BADGE: Record<string, string> = {
  open: "badge-ok",
  pending: "badge-warn",
  resolved: "badge-pending",
  closed: "badge-muted",
};

const STATUSES: TicketStatus[] = ["open", "pending", "resolved", "closed"];

export default function PlatformTicketsPage() {
  const { notify } = useToast();
  const navigate = useNavigate();
  const { ticketId } = useParams();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [admins, setAdmins] = useState<PlatformAdminOption[]>([]);
  const [statusFilter, setStatusFilter] = useState("");

  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [reply, setReply] = useState("");
  const [internal, setInternal] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTickets(await platformTicketsApi.list(statusFilter || undefined));
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setLoading(false);
    }
  }, [notify, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    platformTicketsApi.admins().then(setAdmins).catch(() => setAdmins([]));
  }, []);

  const openDetail = useCallback(
    async (id: string) => {
      try {
        setDetail(await platformTicketsApi.get(id));
        setReply("");
        setInternal(false);
      } catch (err) {
        notify(String(err).replace(/^Error:\s*/i, ""), "error");
      }
    },
    [notify]
  );

  // Deep link desde email/WhatsApp: /admin/tickets/:ticketId
  useEffect(() => {
    if (ticketId) openDetail(ticketId);
  }, [ticketId, openDetail]);

  const closeDetail = () => {
    setDetail(null);
    if (ticketId) navigate("/admin/tickets", { replace: true });
  };

  const submitReply = async () => {
    if (!detail || reply.trim().length === 0) return;
    setBusy(true);
    try {
      const updated = await platformTicketsApi.reply(detail.id, reply, internal);
      setDetail(updated);
      setReply("");
      notify(internal ? "Nota interna añadida" : "Respuesta enviada al cliente", "success");
      await load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setBusy(false);
    }
  };

  const patch = async (body: {
    status?: TicketStatus;
    priority?: TicketPriority;
    assigned_platform_user_id?: string | null;
  }) => {
    if (!detail) return;
    setBusy(true);
    try {
      const updated = await platformTicketsApi.update(detail.id, body);
      setDetail(updated);
      notify("Ticket actualizado", "success");
      await load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setBusy(false);
    }
  };

  const columns = useMemo<DataTableColumn<Ticket>[]>(
    () => [
      { title: "Asunto", field: "subject", headerFilter: true, minWidth: 200 },
      { title: "Cuenta", field: "tenant_name", headerFilter: true, width: 160 },
      { title: "Creado por", field: "created_by_name", width: 150 },
      {
        title: "Estado",
        field: "status",
        width: 150,
        formatter: (c) => {
          const v = String(c.getValue());
          return `<span class="badge ${STATUS_BADGE[v] ?? "badge-muted"}">${
            STATUS_LABELS[v as keyof typeof STATUS_LABELS] ?? v
          }</span>`;
        },
      },
      {
        title: "Prioridad",
        field: "priority",
        width: 100,
        formatter: (c) =>
          PRIORITY_LABELS[c.getValue() as TicketPriority] ?? String(c.getValue()),
      },
      { title: "Asignado", field: "assigned_to_name", width: 140 },
      {
        title: "Actualizado",
        field: "updated_at",
        width: 160,
        formatter: (c) => new Date(String(c.getValue())).toLocaleString("es-ES"),
      },
      {
        title: "",
        field: "id",
        width: 90,
        download: false,
        formatter: () =>
          `<button type="button" class="btn btn-sm" data-action="view">Abrir</button>`,
      },
    ],
    []
  );

  return (
    <>
      <PageHeader
        title="Tickets de soporte"
        subtitle="Gestiona los tickets de todas las cuentas cliente"
        action={
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Todos los estados</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        }
      />

      <DataTable
        data={tickets}
        columns={columns}
        loading={loading}
        exportFilename="tickets-plataforma"
        emptyMessage="No hay tickets."
        onCellAction={(action, row) => {
          if (action === "view") openDetail(row.id);
        }}
        onRowClick={(row) => openDetail(row.id)}
      />

      <Modal
        title={detail ? detail.subject : "Ticket"}
        open={detail !== null}
        onClose={closeDetail}
        wide
        tall
      >
        {detail && (
          <>
            <div className="muted small" style={{ marginBottom: "0.75rem" }}>
              {detail.tenant_name} · creado por {detail.created_by_name} ·{" "}
              origen {detail.source === "whatsapp" ? "WhatsApp" : "Web"}
            </div>

            <div className="form-grid" style={{ marginBottom: "1rem" }}>
              <label>
                Estado
                <select
                  value={detail.status}
                  disabled={busy}
                  onChange={(e) => patch({ status: e.target.value as TicketStatus })}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {STATUS_LABELS[s]}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Prioridad
                <select
                  value={detail.priority}
                  disabled={busy}
                  onChange={(e) =>
                    patch({ priority: e.target.value as TicketPriority })
                  }
                >
                  <option value="low">Baja</option>
                  <option value="normal">Normal</option>
                  <option value="high">Alta</option>
                </select>
              </label>
              <label>
                Asignado a
                <select
                  value={detail.assigned_platform_user_id ?? ""}
                  disabled={busy}
                  onChange={(e) =>
                    patch({ assigned_platform_user_id: e.target.value || null })
                  }
                >
                  <option value="">Sin asignar</option>
                  {admins.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.full_name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="ticket-thread">
              {detail.messages.map((m) => (
                <div
                  key={m.id}
                  style={{
                    margin: "0 0 0.75rem",
                    padding: "0.6rem 0.8rem",
                    borderRadius: "10px",
                    background: m.is_internal
                      ? "#fff7e6"
                      : m.author_type === "platform"
                        ? "#eef6ff"
                        : "#f4f5f7",
                    border: m.is_internal ? "1px dashed #e0a800" : "none",
                  }}
                >
                  <div className="muted small" style={{ marginBottom: 4 }}>
                    {m.is_internal && "🔒 Nota interna · "}
                    {m.author_type === "platform"
                      ? m.author_name || "Soporte"
                      : m.author_name || "Cliente"}{" "}
                    · {new Date(m.created_at).toLocaleString("es-ES")}
                  </div>
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.body}</div>
                </div>
              ))}
            </div>

            <div className="form-grid" style={{ marginTop: "1rem" }}>
              <label className="full">
                {internal ? "Nota interna (no visible al cliente)" : "Responder al cliente"}
                <textarea
                  value={reply}
                  rows={3}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder={internal ? "Anotación interna…" : "Escribe tu respuesta…"}
                />
              </label>
              <label className="checkbox-row full">
                <input
                  type="checkbox"
                  checked={internal}
                  onChange={(e) => setInternal(e.target.checked)}
                />
                Nota interna (no se envía al cliente)
              </label>
              <div className="form-actions full">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy || reply.trim().length === 0}
                  onClick={submitReply}
                >
                  {busy ? "Enviando…" : internal ? "Añadir nota" : "Responder"}
                </button>
              </div>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}
