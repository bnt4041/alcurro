import { useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { formatMoney } from "../lib/money";

interface StripeStatus {
  configured: boolean;
  publishable_key_set: boolean;
  webhook_secret_set: boolean;
  public_app_url: string;
}

interface StripePayment {
  id: string;
  tenant_id: string | null;
  tenant_name: string | null;
  amount_cents: number;
  currency: string;
  status: string;
  description: string | null;
  stripe_invoice_id: string | null;
  paid_at: string | null;
  created_at: string;
}

const statusLabel: Record<string, string> = {
  succeeded: "Cobrado",
  pending: "Pendiente",
  failed: "Fallido",
  refunded: "Reembolsado",
};

export default function PlatformStripePage() {
  const [status, setStatus] = useState<StripeStatus | null>(null);
  const [payments, setPayments] = useState<StripePayment[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [st, pays] = await Promise.all([
        api.get<StripeStatus>("/platform/stripe/status"),
        api.get<StripePayment[]>("/platform/stripe/payments"),
      ]);
      setStatus(st);
      setPayments(pays);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <PageHeader
        title="Cobros Stripe"
        subtitle="Pagos recibidos y estado de la integración"
      />

      {status && (
        <div className={`stripe-status card ${status.configured ? "ok" : "warn"}`}>
          <h3>Estado de Stripe</h3>
          {!status.configured ? (
            <p>
              Stripe no está configurado. Define{" "}
              <code>STRIPE_SECRET_KEY</code> en el backend para activar checkout y
              cobros automáticos. El alta de clientes funciona en modo prueba sin
              pago.
            </p>
          ) : (
            <ul className="stripe-status-list">
              <li>API secreta: configurada</li>
              <li>
                Clave publicable:{" "}
                {status.publishable_key_set ? "sí" : "no configurada"}
              </li>
              <li>
                Webhook:{" "}
                {status.webhook_secret_set
                  ? "configurado"
                  : "falta STRIPE_WEBHOOK_SECRET"}
              </li>
              <li>URL pública: {status.public_app_url}</li>
            </ul>
          )}
        </div>
      )}

      <div className="card" style={{ marginTop: "1rem" }}>
        <h3>Historial de cobros</h3>
        {loading && <p className="muted">Cargando…</p>}
        {!loading && payments.length === 0 && (
          <p className="muted">Aún no hay cobros registrados.</p>
        )}
        {!loading && payments.length > 0 && (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Cuenta</th>
                  <th>Importe</th>
                  <th>Estado</th>
                  <th>Descripción</th>
                  <th>Factura Stripe</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.id}>
                    <td>
                      {new Date(p.paid_at || p.created_at).toLocaleString("es-ES")}
                    </td>
                    <td>{p.tenant_name || "—"}</td>
                    <td>{formatMoney(p.amount_cents, p.currency)}</td>
                    <td>
                      <span className={`badge badge-${p.status}`}>
                        {statusLabel[p.status] || p.status}
                      </span>
                    </td>
                    <td>{p.description || "—"}</td>
                    <td className="mono small">{p.stripe_invoice_id || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
