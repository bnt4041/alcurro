import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  ticketsApi,
  type KbSearchResult,
  type Ticket,
  type TicketDetail,
  type TicketPriority,
} from "../api/tickets";

const STATUS_BADGE: Record<string, string> = {
  open: "badge-ok",
  pending: "badge-warn",
  resolved: "badge-pending",
  closed: "badge-muted",
};

export default function SupportPage() {
  const { notify } = useToast();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);

  // Crear
  const [createOpen, setCreateOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("normal");
  const [docs, setDocs] = useState<KbSearchResult[]>([]);
  const [saving, setSaving] = useState(false);
  const kbTimer = useRef<number | null>(null);

  // Detalle
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [reply, setReply] = useState("");
  const [replying, setReplying] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTickets(await ticketsApi.list());
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  // Búsqueda de documentación al escribir (debounce)
  useEffect(() => {
    if (!createOpen) return;
    const query = `${subject} ${body}`.trim();
    if (kbTimer.current) window.clearTimeout(kbTimer.current);
    if (query.length < 4) {
      setDocs([]);
      return;
    }
    kbTimer.current = window.setTimeout(() => {
      ticketsApi
        .kbSearch(query)
        .then(setDocs)
        .catch(() => setDocs([]));
    }, 450);
    return () => {
      if (kbTimer.current) window.clearTimeout(kbTimer.current);
    };
  }, [subject, body, createOpen]);

  const resetCreate = () => {
    setSubject("");
    setBody("");
    setPriority("normal");
    setDocs([]);
  };

  const submitCreate = async () => {
    if (subject.trim().length < 3 || body.trim().length < 3) {
      notify("Indica un asunto y una descripción", "error");
      return;
    }
    setSaving(true);
    try {
      await ticketsApi.create({ subject, body, priority });
      notify("Ticket creado. El equipo de Alcurro te responderá pronto.", "success");
      setCreateOpen(false);
      resetCreate();
      await load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setSaving(false);
    }
  };

  const openDetail = async (row: Ticket) => {
    try {
      setDetail(await ticketsApi.get(row.id));
      setReply("");
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    }
  };

  const submitReply = async () => {
    if (!detail || reply.trim().length === 0) return;
    setReplying(true);
    try {
      const updated = await ticketsApi.reply(detail.id, reply);
      setDetail(updated);
      setReply("");
      await load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setReplying(false);
    }
  };

  const columns = useMemo<DataTableColumn<Ticket>[]>(
    () => [
      { title: "Asunto", field: "subject", headerFilter: true, minWidth: 220 },
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
        width: 110,
        formatter: (c) =>
          PRIORITY_LABELS[c.getValue() as TicketPriority] ?? String(c.getValue()),
      },
      {
        title: "Origen",
        field: "source",
        width: 100,
        formatter: (c) => (c.getValue() === "whatsapp" ? "WhatsApp" : "Web"),
      },
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
          `<button type="button" class="btn btn-sm" data-action="view">Ver</button>`,
      },
    ],
    []
  );

  return (
    <>
      <PageHeader
        title="Soporte"
        subtitle="Abre y consulta tickets de soporte con el equipo de Alcurro"
        action={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              resetCreate();
              setCreateOpen(true);
            }}
          >
            Nuevo ticket
          </button>
        }
      />

      <DataTable
        data={tickets}
        columns={columns}
        loading={loading}
        exportFilename="tickets"
        emptyMessage="No tienes tickets de soporte todavía."
        onCellAction={(action, row) => {
          if (action === "view") openDetail(row);
        }}
        onRowClick={openDetail}
      />

      {/* Crear ticket */}
      <Modal
        title="Nuevo ticket de soporte"
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        wide
      >
        <div className="form-grid">
          <label className="full">
            Asunto
            <input
              value={subject}
              maxLength={200}
              placeholder="Resumen breve de tu consulta"
              onChange={(e) => setSubject(e.target.value)}
            />
          </label>
          <label className="full">
            Descripción
            <textarea
              value={body}
              rows={5}
              maxLength={4000}
              placeholder="Cuéntanos qué necesitas o qué problema tienes…"
              onChange={(e) => setBody(e.target.value)}
            />
          </label>
          <label className="full">
            Prioridad
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as TicketPriority)}
            >
              <option value="low">Baja</option>
              <option value="normal">Normal</option>
              <option value="high">Alta</option>
            </select>
          </label>

          {docs.length > 0 && (
            <div className="full alert alert-info" style={{ textAlign: "left" }}>
              <strong>📚 Quizá esto resuelva tu duda:</strong>
              <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem" }}>
                {docs.map((d, i) => (
                  <li key={i} style={{ marginBottom: "0.5rem" }}>
                    <strong>{d.title}</strong>
                    <div className="muted small">{d.snippet}</div>
                  </li>
                ))}
              </ul>
              <p className="muted small" style={{ marginTop: "0.5rem" }}>
                Si no resuelve tu consulta, crea el ticket y te ayudaremos.
              </p>
            </div>
          )}

          <div className="form-actions full">
            <button
              type="button"
              className="btn btn-primary"
              disabled={saving}
              onClick={submitCreate}
            >
              {saving ? "Creando…" : "Crear ticket"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setCreateOpen(false)}
            >
              Cancelar
            </button>
          </div>
        </div>
      </Modal>

      {/* Detalle / hilo */}
      <Modal
        title={detail ? detail.subject : "Ticket"}
        open={detail !== null}
        onClose={() => setDetail(null)}
        wide
        tall
      >
        {detail && (
          <>
            <div className="ticket-meta" style={{ marginBottom: "1rem" }}>
              <span className={`badge ${STATUS_BADGE[detail.status] ?? "badge-muted"}`}>
                {STATUS_LABELS[detail.status]}
              </span>{" "}
              <span className="muted small">
                Prioridad {PRIORITY_LABELS[detail.priority]} ·{" "}
                {new Date(detail.created_at).toLocaleString("es-ES")}
              </span>
            </div>

            <div className="ticket-thread">
              {detail.messages.map((m) => (
                <div
                  key={m.id}
                  className={`ticket-msg ticket-msg--${m.author_type}`}
                  style={{
                    margin: "0 0 0.75rem",
                    padding: "0.6rem 0.8rem",
                    borderRadius: "10px",
                    background:
                      m.author_type === "platform" ? "#eef6ff" : "#f4f5f7",
                  }}
                >
                  <div className="muted small" style={{ marginBottom: 4 }}>
                    {m.author_type === "platform"
                      ? m.author_name || "Soporte Alcurro"
                      : m.author_name || "Tú"}{" "}
                    · {new Date(m.created_at).toLocaleString("es-ES")}
                  </div>
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.body}</div>
                </div>
              ))}
            </div>

            {detail.status !== "closed" ? (
              <div className="form-grid" style={{ marginTop: "1rem" }}>
                <label className="full">
                  Responder
                  <textarea
                    value={reply}
                    rows={3}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Escribe tu respuesta…"
                  />
                </label>
                <div className="form-actions full">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={replying || reply.trim().length === 0}
                    onClick={submitReply}
                  >
                    {replying ? "Enviando…" : "Enviar respuesta"}
                  </button>
                </div>
              </div>
            ) : (
              <p className="muted" style={{ marginTop: "1rem" }}>
                Este ticket está cerrado.
              </p>
            )}
          </>
        )}
      </Modal>
    </>
  );
}
