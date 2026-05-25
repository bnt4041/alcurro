import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import { formatMoney } from "../lib/money";

interface StripeStatus {
  configured: boolean;
  simulation_mode: boolean;
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

interface SimulateResult {
  tenant_slug: string;
  company_name: string;
  gowa_status: string;
  gowa_ui_url: string | null;
  gowa_error: string | null;
}

const statusLabel: Record<string, string> = {
  succeeded: "Cobrado",
  pending: "Pendiente",
  failed: "Fallido",
  refunded: "Reembolsado",
};

export default function PlatformStripePage() {
  const toast = useToast();
  const [status, setStatus] = useState<StripeStatus | null>(null);
  const [payments, setPayments] = useState<StripePayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [tenantId, setTenantId] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [lastSim, setLastSim] = useState<SimulateResult | null>(null);

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

  const runSimulate = async () => {
    if (!tenantId.trim()) {
      toast.error("Indica el UUID de la cuenta");
      return;
    }
    setSimulating(true);
    setLastSim(null);
    try {
      const res = await api.post<SimulateResult>(
        `/platform/stripe/simulate-tenant/${tenantId.trim()}`,
        {}
      );
      setLastSim(res);
      toast.success(`Cobro simulado · goWA: ${res.gowa_status}`);
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSimulating(false);
    }
  };

  type PaymentRow = StripePayment & {
    date_label: string;
    amount_label: string;
    status_text: string;
  };

  const paymentTableData = useMemo<PaymentRow[]>(
    () =>
      payments.map((p) => ({
        ...p,
        date_label: new Date(p.paid_at || p.created_at).toLocaleString("es-ES"),
        amount_label: formatMoney(p.amount_cents, p.currency),
        status_text: statusLabel[p.status] || p.status,
      })),
    [payments]
  );

  const paymentColumns = useMemo<DataTableColumn<PaymentRow>[]>(
    () => [
      { title: "Fecha", field: "date_label", headerFilter: "input", minWidth: 150 },
      {
        title: "Cuenta",
        field: "tenant_name",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 140,
      },
      { title: "Importe", field: "amount_label", headerFilter: "input", width: 110 },
      {
        title: "Estado",
        field: "status_text",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", ...Object.fromEntries(Object.entries(statusLabel).map(([, v]) => [v, v])) } as Record<string, string>,
        },
        formatter: (cell) => {
          const r = cell.getRow().getData() as PaymentRow;
          return `<span class="badge badge-${r.status}">${r.status_text}</span>`;
        },
        width: 110,
      },
      {
        title: "Descripción",
        field: "description",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 160,
      },
      {
        title: "Referencia",
        field: "stripe_invoice_id",
        headerFilter: "input",
        formatter: (c) => `<span class="mono small">${String(c.getValue() ?? "—")}</span>`,
        minWidth: 140,
      },
    ],
    []
  );

  return (
    <>
      <PageHeader
        title="Cobros Stripe"
        subtitle="Pagos recibidos, simulación y estado de la integración"
      />

      {status && (
        <div
          className={`stripe-status card ${
            status.configured ? "ok" : status.simulation_mode ? "simulate" : "warn"
          }`}
        >
          <h3>Estado de pagos</h3>
          {status.simulation_mode && !status.configured && (
            <>
              <p>
                <strong>Modo simulación activo</strong> (
                <code>STRIPE_SIMULATION_MODE=true</code>). El alta en{" "}
                <code>/registro</code> redirige a un checkout falso y registra el cobro.
              </p>
              <p className="muted small">
                Para Stripe real: configura las claves y pon{" "}
                <code>STRIPE_SIMULATION_MODE=false</code>.
              </p>
            </>
          )}
          {status.configured && (
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
              {status.simulation_mode && (
                <li className="warn-text">
                  Simulación también activa (prioridad: Stripe real en el alta si ambos)
                </li>
              )}
              <li>URL pública: {status.public_app_url}</li>
            </ul>
          )}
          {!status.configured && !status.simulation_mode && (
            <p>
              Sin Stripe ni simulación. Activa{" "}
              <code>STRIPE_SIMULATION_MODE=true</code> o configura Stripe.
            </p>
          )}
        </div>
      )}

      {status?.simulation_mode && (
        <div className="card simulate-admin" style={{ marginTop: "1rem" }}>
          <h3>Simular cobro + goWA (cuenta existente)</h3>
          <p className="muted small">
            UUID de la cuenta (columna en la ficha o listado de cuentas). Útil para
            reprobar el flujo sin pasar por el registro.
          </p>
          <div className="simulate-admin-row">
            <input
              type="text"
              placeholder="UUID del tenant"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={simulating}
              onClick={runSimulate}
            >
              {simulating ? "Ejecutando…" : "Simular cobro y crear goWA"}
            </button>
          </div>
          {lastSim && (
            <div className="simulate-gowa card-inner">
              <p>
                <strong>{lastSim.company_name}</strong> ({lastSim.tenant_slug}) · goWA:{" "}
                {lastSim.gowa_status}
              </p>
              {lastSim.gowa_ui_url && (
                <p>
                  <a href={lastSim.gowa_ui_url} target="_blank" rel="noreferrer">
                    {lastSim.gowa_ui_url}
                  </a>
                </p>
              )}
              {lastSim.gowa_error && (
                <div className="alert alert-error">{lastSim.gowa_error}</div>
              )}
            </div>
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
          <DataTable
            data={paymentTableData}
            columns={paymentColumns}
            exportFilename="cobros_stripe"
            height="400px"
          />
        )}
      </div>
    </>
  );
}
