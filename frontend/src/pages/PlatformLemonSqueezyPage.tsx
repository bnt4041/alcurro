import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import { formatMoney } from "../lib/money";

interface LsStatus {
  configured: boolean;
  store_id: string | null;
  webhook_secret_set: boolean;
  webhook_url: string;
}

interface LsPayment {
  id: string;
  tenant_id: string | null;
  tenant_name: string | null;
  ls_order_id: string | null;
  ls_invoice_id: string | null;
  amount_cents: number;
  currency: string;
  status: string;
  description: string | null;
  receipt_url: string | null;
  paid_at: string | null;
  created_at: string;
}

const statusLabel: Record<string, string> = {
  paid: "Cobrado",
  pending: "Pendiente",
  failed: "Fallido",
  refunded: "Reembolsado",
};

type PaymentRow = LsPayment & {
  date_label: string;
  amount_label: string;
  status_text: string;
};

interface RefundResult {
  payment_id: string;
  payment_status: string;
  credit_note_number: string;
  credit_note_id: string;
}

export default function PlatformLemonSqueezyPage() {
  const { notify } = useToast();
  const [status, setStatus] = useState<LsStatus | null>(null);
  const [payments, setPayments] = useState<LsPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [s, p] = await Promise.all([
      api.get<LsStatus>("/platform/ls/status"),
      api.get<LsPayment[]>("/platform/ls/payments"),
    ]);
    setStatus(s);
    setPayments(p);
  }, []);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, [load]);

  const handleRefund = async (row: PaymentRow) => {
    if (!confirm(`¿Reembolsar el pago de ${row.amount_label} (${row.tenant_name ?? "—"})?\n\nSe realizará el reembolso monetario en Lemon Squeezy y se generará la factura rectificativa en Alcurro.`)) return;
    setActionLoading(row.id);
    try {
      const res = await api.post<RefundResult>(`/platform/ls/refund/${row.id}`, {});
      notify(`Abono ${res.credit_note_number} generado correctamente`, "success");
      await load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setActionLoading(null);
    }
  };

  const tableData = useMemo<PaymentRow[]>(
    () =>
      payments.map((p) => ({
        ...p,
        date_label: new Date(p.paid_at ?? p.created_at).toLocaleDateString("es-ES"),
        amount_label: formatMoney(p.amount_cents, p.currency),
        status_text: statusLabel[p.status] ?? p.status,
      })),
    [payments]
  );

  const columns = useMemo<DataTableColumn<PaymentRow>[]>(
    () => [
      { title: "Fecha", field: "date_label", width: 110 },
      {
        title: "Cuenta",
        field: "tenant_name",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 160,
      },
      {
        title: "Factura LS",
        field: "ls_invoice_id",
        width: 100,
        formatter: (cell) => {
          const r = cell.getRow().getData() as PaymentRow;
          if (!r.receipt_url) return `<span class="muted small">—</span>`;
          const ref = r.ls_invoice_id || r.ls_order_id || "";
          return `<div style="display:flex;gap:6px;align-items:center">
            <a href="${r.receipt_url}" target="_blank" rel="noopener" title="Abrir factura en Lemon Squeezy" style="color:var(--color-primary,#27ae60);display:flex;align-items:center">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
            <button data-action="copy-url" data-url="${r.receipt_url}" title="Copiar enlace" style="background:none;border:none;cursor:pointer;padding:0;color:var(--color-muted,#888);display:flex;align-items:center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
            ${ref ? `<span class="mono" style="font-size:0.75rem;color:var(--color-muted,#888)">${ref}</span>` : ""}
          </div>`;
        },
      },
      {
        title: "Concepto",
        field: "description",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 160,
      },
      { title: "Importe", field: "amount_label", width: 110 },
      {
        title: "Estado",
        field: "status_text",
        width: 120,
        formatter: (cell) => {
          const r = cell.getRow().getData() as PaymentRow;
          const cls =
            r.status === "paid"
              ? "badge--ok"
              : r.status === "failed"
                ? "badge--danger"
                : r.status === "refunded"
                  ? "badge--warning"
                  : "";
          return `<span class="badge ${cls}">${r.status_text}</span>`;
        },
      },
      {
        title: "Acciones",
        field: "id",
        width: 130,
        formatter: (cell) => {
          const r = cell.getRow().getData() as PaymentRow;
          if (r.status !== "paid") return `<span class="muted small">—</span>`;
          const loading = actionLoading === r.id;
          return `<div class="table-actions">
            <button class="btn btn-xs btn-warning" data-action="refund" ${loading ? "disabled" : ""}>
              ${loading ? "…" : "Emitir abono"}
            </button>
          </div>`;
        },
      },
    ],
    [actionLoading]
  );

  const handleAction = (action: string, row: PaymentRow) => {
    if (action === "refund") handleRefund(row);
    if (action === "copy-url") {
      const url = row.receipt_url ?? "";
      if (url) navigator.clipboard.writeText(url).then(() => notify("Enlace copiado", "success"));
    }
  };

  return (
    <>
      <PageHeader
        title="Cobros Lemon Squeezy"
        subtitle="Estado de la integración y registro de pagos recibidos"
      />

      {/* ── Estado de configuración ── */}
      <section className="card settings-section" style={{ marginBottom: "1.5rem" }}>
        <h3>Estado de la integración</h3>

        {loading ? (
          <p className="muted small">Cargando…</p>
        ) : !status ? (
          <p className="muted small">No se pudo obtener el estado.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <span className={`badge ${status.configured ? "badge--ok" : "badge--muted"}`}>
                {status.configured ? "API Key configurada" : "Sin API Key"}
              </span>
              <span className={`badge ${status.store_id ? "badge--ok" : "badge--muted"}`}>
                {status.store_id ? `Store ID: ${status.store_id}` : "Sin Store ID"}
              </span>
              <span className={`badge ${status.webhook_secret_set ? "badge--ok" : "badge--muted"}`}>
                {status.webhook_secret_set ? "Webhook secret configurado" : "Sin webhook secret"}
              </span>
            </div>

            {!status.configured && (
              <div className="alert alert-warning" style={{ marginTop: "0.5rem" }}>
                Lemon Squeezy no está configurado. Añade las variables de entorno al servidor:
                <pre style={{ marginTop: "0.5rem", fontSize: "0.82rem" }}>
{`LEMON_SQUEEZY_API_KEY=tu_api_key
LEMON_SQUEEZY_STORE_ID=tu_store_id
LEMON_SQUEEZY_WEBHOOK_SECRET=tu_webhook_secret`}
                </pre>
              </div>
            )}

            <div style={{ marginTop: "0.4rem" }}>
              <p className="muted small" style={{ margin: 0 }}>
                <strong>URL de webhook a configurar en Lemon Squeezy:</strong>
              </p>
              <code style={{ fontSize: "0.85rem", wordBreak: "break-all" }}>
                {status.webhook_url}
              </code>
              <p className="muted small" style={{ marginTop: "0.4rem" }}>
                Eventos a activar: <code>subscription_created</code>,{" "}
                <code>subscription_updated</code>, <code>subscription_cancelled</code>,{" "}
                <code>subscription_payment_success</code>,{" "}
                <code>subscription_payment_failed</code>,{" "}
                <code>subscription_payment_recovered</code>,{" "}
                <code>subscription_payment_refunded</code>
              </p>
            </div>

            <div style={{ marginTop: "0.4rem" }}>
              <p className="muted small" style={{ margin: 0 }}>
                <strong>Variant IDs:</strong> configura los IDs de variante mensual/anual
                en cada tarifa desde{" "}
                <a href="/admin/tarifas">Tarifas → Editar → sección Lemon Squeezy</a>.
              </p>
            </div>
          </div>
        )}
      </section>

      {/* ── Listado de pagos ── */}
      <section className="card settings-section">
        <h3>Pagos recibidos</h3>
        <p className="muted small" style={{ marginBottom: "0.75rem" }}>
          «Emitir abono» realiza el reembolso monetario en Lemon Squeezy y genera la factura rectificativa en Alcurro automáticamente.
        </p>
        <DataTable
          data={tableData}
          columns={columns}
          loading={loading}
          exportFilename="cobros-lemon-squeezy"
          height="500px"
          emptyMessage="Sin pagos registrados"
          onCellAction={(action, row) => handleAction(action, row as PaymentRow)}
        />
      </section>
    </>
  );
}
