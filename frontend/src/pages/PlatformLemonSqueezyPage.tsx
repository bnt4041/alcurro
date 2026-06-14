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
    if (!confirm(`¿Emitir factura de abono para el pago de ${row.amount_label} (${row.tenant_name ?? "—"})?\n\nRecuerda realizar también el reembolso monetario desde el panel de Lemon Squeezy.`)) return;
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
        title: "Referencia LS",
        field: "ls_invoice_id",
        headerFilter: "input",
        formatter: (cell) => {
          const r = cell.getRow().getData() as PaymentRow;
          const ref = r.ls_invoice_id || r.ls_order_id || "—";
          if (r.receipt_url) {
            return `<a href="${r.receipt_url}" target="_blank" rel="noopener" class="invoice-pdf-link" title="Ver factura">${ref}</a>`;
          }
          return `<span class="mono small">${ref}</span>`;
        },
        minWidth: 140,
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
          <strong>Nota sobre abonos:</strong> «Emitir abono» genera una factura rectificativa en Alcurro,
          pero <strong>no</strong> realiza el reembolso monetario en Lemon Squeezy. Debes tramitar
          el reembolso económico manualmente desde el{" "}
          <a href="https://app.lemonsqueezy.com" target="_blank" rel="noopener noreferrer">panel de Lemon Squeezy</a>.
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
