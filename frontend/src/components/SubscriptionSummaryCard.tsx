import { formatMoney } from "../lib/money";
import type { SubscriptionSummary } from "../lib/subscription";
import { SUBSCRIPTION_STATUS_LABELS } from "../lib/subscription";

interface Props {
  subscription: SubscriptionSummary | null;
  loading?: boolean;
}

export default function SubscriptionSummaryCard({ subscription, loading }: Props) {
  if (loading) {
    return <p className="muted">Cargando suscripción…</p>;
  }
  if (!subscription) {
    return (
      <p className="muted small">
        No hay suscripción activa registrada para esta cuenta.
      </p>
    );
  }

  const cycleLabel = subscription.billing_cycle === "annual" ? "anual" : "mensual";
  const statusLabel =
    SUBSCRIPTION_STATUS_LABELS[subscription.status] ?? subscription.status;
  const statusClass =
    subscription.status === "active"
      ? "badge--ok"
      : subscription.status === "past_due"
        ? "badge--danger"
        : "badge--muted";

  return (
    <dl className="subscription-summary">
      <div>
        <dt>Tarifa</dt>
        <dd>
          <strong>{subscription.plan_name}</strong>
          {subscription.company_name && (
            <span className="muted small"> · {subscription.company_name}</span>
          )}
        </dd>
      </div>
      <div>
        <dt>Importe</dt>
        <dd>
          {formatMoney(subscription.amount_cents, subscription.currency)}
          <span className="muted"> /{cycleLabel}</span>
        </dd>
      </div>
      <div>
        <dt>Estado</dt>
        <dd>
          <span className={`badge ${statusClass}`}>{statusLabel}</span>
        </dd>
      </div>
      {(subscription.current_period_start || subscription.current_period_end) && (
        <div className="form-span-2">
          <dt>Periodo actual</dt>
          <dd className="muted small">
            {subscription.current_period_start
              ? new Date(subscription.current_period_start).toLocaleDateString("es-ES")
              : "—"}
            {" → "}
            {subscription.current_period_end
              ? new Date(subscription.current_period_end).toLocaleDateString("es-ES")
              : "—"}
          </dd>
        </div>
      )}
    </dl>
  );
}
