import { formatMoney } from "../lib/money";
import type { InvoiceRow } from "../lib/subscription";
import { PAYMENT_STATUS_LABELS } from "../lib/subscription";

interface Props {
  invoices: InvoiceRow[];
  loading?: boolean;
}

export default function InvoiceHistoryTable({ invoices, loading }: Props) {
  if (loading) {
    return <p className="muted">Cargando facturas…</p>;
  }
  if (invoices.length === 0) {
    return (
      <p className="muted small">
        Aún no hay facturas registradas para esta cuenta.
      </p>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Concepto</th>
            <th>Importe</th>
            <th>Estado</th>
            <th>Referencia</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr key={inv.id}>
              <td>
                {new Date(inv.paid_at ?? inv.created_at).toLocaleDateString("es-ES")}
              </td>
              <td>{inv.description ?? "Suscripción alcurro"}</td>
              <td>{formatMoney(inv.amount_cents, inv.currency)}</td>
              <td>
                <span
                  className={`badge ${
                    inv.status === "succeeded"
                      ? "badge--ok"
                      : inv.status === "failed"
                        ? "badge--danger"
                        : ""
                  }`}
                >
                  {PAYMENT_STATUS_LABELS[inv.status] ?? inv.status}
                </span>
              </td>
              <td className="mono small">
                {inv.stripe_invoice_id ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
