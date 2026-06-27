import { api, buildQuery } from "./client";

export type TicketStatus = "open" | "pending" | "resolved" | "closed";
export type TicketPriority = "low" | "normal" | "high";

export interface KbSearchResult {
  title: string;
  source: string;
  snippet: string;
}

export interface TicketMessage {
  id: string;
  author_type: "client" | "platform";
  author_name: string | null;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface Ticket {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  created_by_employee_id: string;
  created_by_name: string | null;
  subject: string;
  body: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: string | null;
  source: "web" | "whatsapp";
  assigned_platform_user_id: string | null;
  assigned_to_name: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[];
}

export interface TicketCreateBody {
  subject: string;
  body: string;
  priority?: TicketPriority;
  category?: string | null;
}

// ── Lado cuenta (clientes) ────────────────────────────────────────────────────
export const ticketsApi = {
  list: (status?: string) =>
    api.get<Ticket[]>(`/tickets${buildQuery({ status })}`),
  get: (id: string) => api.get<TicketDetail>(`/tickets/${id}`),
  create: (body: TicketCreateBody) =>
    api.post<TicketDetail>("/tickets", body),
  reply: (id: string, body: string) =>
    api.post<TicketDetail>(`/tickets/${id}/messages`, { body }),
  kbSearch: (q: string) =>
    api.get<KbSearchResult[]>(`/tickets/kb-search${buildQuery({ q })}`),
};

// ── Lado plataforma (admins de Alcurro) ───────────────────────────────────────
export interface PlatformAdminOption {
  id: string;
  full_name: string;
}

export const platformTicketsApi = {
  list: (status?: string) =>
    api.get<Ticket[]>(`/platform/tickets${buildQuery({ status })}`),
  get: (id: string) => api.get<TicketDetail>(`/platform/tickets/${id}`),
  admins: () =>
    api.get<PlatformAdminOption[]>("/platform/tickets/admins"),
  update: (
    id: string,
    body: {
      status?: TicketStatus;
      priority?: TicketPriority;
      assigned_platform_user_id?: string | null;
    }
  ) => api.patch<TicketDetail>(`/platform/tickets/${id}`, body),
  reply: (id: string, body: string, is_internal = false) =>
    api.post<TicketDetail>(`/platform/tickets/${id}/messages`, {
      body,
      is_internal,
    }),
};

export const STATUS_LABELS: Record<TicketStatus, string> = {
  open: "Abierto",
  pending: "Esperando cliente",
  resolved: "Resuelto",
  closed: "Cerrado",
};

export const PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: "Baja",
  normal: "Normal",
  high: "Alta",
};
