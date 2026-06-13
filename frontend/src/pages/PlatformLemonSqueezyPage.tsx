import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import PageHeader from "../components/PageHeader";
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

export default function PlatformLemonSqueezyPage() {
  const [status, setStatus] = useState<LsStatus | null>(null);
  const [payments, setPayments] = useState<LsPayment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<LsStatus>("/platform/ls/status"),
      api.get<LsPayment[]>("/platform/ls/payments"),
    ])
      .then(([s, p]) => {
        setStatus(s);
        setPayments(p);
      })
      .finally(() => setLoading(false));
  }, []);

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
        width: 110,
        formatter: (cell) => {
          const r = cell.getRow().getData() as PaymentRow;
          const cls =
            r.status === "paid"
              ? "badge--ok"
              : r.status === "failed"
                ? "badge--danger"
                : "";
          return `<span class="badge ${cls}">${r.status_text}</span>`;
        },
      },
    ],
    []
  );

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
                <code>subscription_payment_recovered</code>
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
        <DataTable
          data={tableData}
          columns={columns}
          loading={loading}
          exportFilename="cobros-lemon-squeezy"
          height="500px"
          emptyMessage="Sin pagos registrados"
        />
      </section>
    </>
  );
}
