import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useToast } from "../context/ToastContext";
import { formatMoney } from "../lib/money";

interface PricingPlanOption {
  id: string;
  code: string;
  name: string;
  monthly_price_cents: number;
  annual_price_per_month_cents: number;
  max_active_users: number;
  currency: string;
}

interface DiscountOption {
  id: string;
  code: string;
  name: string;
  discount_type: string;
  value: number;
  pricing_plan_id: string | null;
  valid_from: string;
  valid_until: string;
  is_active: boolean;
}

export interface BillingMethodRow {
  id: string;
  company_id: string | null;
  label: string;
  method_type: string;
  is_default: boolean;
  holder_name: string | null;
  iban_masked: string | null;
  card_brand: string | null;
  card_last4: string | null;
}

export interface SubscriptionRow {
  id: string;
  company_id: string;
  pricing_plan_id: string | null;
  discount_id: string | null;
  plan_code: string;
  plan_name: string;
  status: string;
  amount_cents: number;
  currency: string;
  billing_cycle: string;
  max_active_users: number | null;
  billing_method_id: string | null;
}

export interface CompanyBillingRow {
  id: string;
  name: string;
  tax_id: string | null;
  is_active: boolean;
  legal_name: string | null;
  billing_email: string | null;
  billing_phone: string | null;
  billing_address: string | null;
  billing_city: string | null;
  billing_postal_code: string | null;
  billing_province: string | null;
  billing_country: string;
  subscription: SubscriptionRow | null;
  billing_methods: BillingMethodRow[];
}

export interface TenantBillingOverview {
  tenant_id: string;
  tenant_name: string;
  account_billing_methods: BillingMethodRow[];
  companies: CompanyBillingRow[];
}

const SUB_STATUS: Record<string, string> = {
  active: "Activa",
  trialing: "Prueba",
  cancelled: "Cancelada",
  past_due: "Impago",
};

const METHOD_TYPE: Record<string, string> = {
  bank_transfer: "Transferencia",
  card: "Tarjeta",
  sepa_direct_debit: "SEPA",
  other: "Otro",
};

interface Props {
  tenantId: string;
  overview: TenantBillingOverview | null;
  loading: boolean;
  onReload: () => void;
}

export default function TenantBillingTab({
  tenantId,
  overview,
  loading,
  onReload,
}: Props) {
  const toast = useToast();
  const [newCompanyName, setNewCompanyName] = useState("");
  const [addingCompany, setAddingCompany] = useState(false);
  const [newMethodLabel, setNewMethodLabel] = useState("");
  const [newMethodCompanyId, setNewMethodCompanyId] = useState<string>("");
  const [plans, setPlans] = useState<PricingPlanOption[]>([]);
  const [discounts, setDiscounts] = useState<DiscountOption[]>([]);

  useEffect(() => {
    void api
      .get<PricingPlanOption[]>("/platform/pricing-plans?active_only=true")
      .then(setPlans)
      .catch(() => api.get<PricingPlanOption[]>("/platform/pricing-plans").then(setPlans));
    void api.get<DiscountOption[]>("/platform/discounts").then(setDiscounts);
  }, []);

  const activeDiscountsForPlan = (planId: string | null) => {
    const today = new Date().toISOString().slice(0, 10);
    return discounts.filter(
      (d) =>
        d.is_active &&
        d.valid_from <= today &&
        d.valid_until >= today &&
        (!d.pricing_plan_id || d.pricing_plan_id === planId)
    );
  };

  const addCompany = async () => {
    if (!newCompanyName.trim()) return;
    setAddingCompany(true);
    try {
      await api.post(`/platform/tenants/${tenantId}/companies`, {
        name: newCompanyName.trim(),
      });
      toast.success(`Empresa «${newCompanyName.trim()}» añadida`);
      setNewCompanyName("");
      onReload();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setAddingCompany(false);
    }
  };

  const addPaymentMethod = async () => {
    if (!newMethodLabel.trim()) return;
    try {
      await api.post(`/platform/tenants/${tenantId}/billing-methods`, {
        label: newMethodLabel.trim(),
        company_id: newMethodCompanyId || null,
        method_type: "bank_transfer",
      });
      toast.success("Método de pago añadido");
      setNewMethodLabel("");
      setNewMethodCompanyId("");
      onReload();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const updateSubscription = async (
    subId: string,
    patch: Record<string, unknown>
  ) => {
    try {
      await api.patch(`/platform/tenants/${tenantId}/subscriptions/${subId}`, patch);
      toast.success("Suscripción actualizada");
      onReload();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  if (loading) {
    return <p className="muted">Cargando facturación…</p>;
  }

  if (!overview) {
    return (
      <div className="sheet-placeholder">
        <p className="muted">Guarda la cuenta para gestionar empresas y facturación.</p>
      </div>
    );
  }

  return (
    <div className="sheet-tab-panel billing-tab">
      <p className="muted small billing-tab-intro">
        Una cuenta puede incluir <strong>varias empresas</strong>. Cada empresa tiene su
        propia suscripción y puede usar métodos de pago propios o compartidos a nivel
        cuenta.
      </p>

      <section className="billing-block">
        <h4>Métodos de pago (cuenta)</h4>
        <p className="muted small">
          Válidos para todas las empresas salvo que indiques uno específico por empresa.
        </p>
        {overview.account_billing_methods.length === 0 ? (
          <p className="muted small">Sin métodos compartidos.</p>
        ) : (
          <ul className="billing-method-list">
            {overview.account_billing_methods.map((m) => (
              <li key={m.id}>
                <strong>{m.label}</strong>
                <span className="muted small">
                  {" "}
                  · {METHOD_TYPE[m.method_type] ?? m.method_type}
                  {m.iban_masked && ` · ${m.iban_masked}`}
                  {m.card_last4 && ` · **** ${m.card_last4}`}
                  {m.is_default && " · Por defecto"}
                </span>
              </li>
            ))}
          </ul>
        )}
        <div className="billing-inline-form">
          <input
            placeholder="Nuevo método (ej. Transferencia BBVA)"
            value={newMethodLabel}
            onChange={(e) => setNewMethodLabel(e.target.value)}
          />
          <select
            value={newMethodCompanyId}
            onChange={(e) => setNewMethodCompanyId(e.target.value)}
            title="Ámbito del método"
          >
            <option value="">Toda la cuenta</option>
            {overview.companies.map((c) => (
              <option key={c.id} value={c.id}>
                Solo {c.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={addPaymentMethod}
            disabled={!newMethodLabel.trim()}
          >
            Añadir método
          </button>
        </div>
      </section>

      <section className="billing-block">
        <div className="label-row">
          <h4>Empresas y suscripciones</h4>
          <span className="badge">{overview.companies.length}</span>
        </div>

        <div className="billing-inline-form">
          <input
            placeholder="Nombre nueva empresa"
            value={newCompanyName}
            onChange={(e) => setNewCompanyName(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={addCompany}
            disabled={addingCompany || !newCompanyName.trim()}
          >
            {addingCompany ? "Añadiendo…" : "+ Empresa"}
          </button>
        </div>

        <div className="company-billing-cards">
          {overview.companies.map((c) => (
            <article key={c.id} className="company-billing-card card">
              <header className="company-billing-card__head">
                <div>
                  <h5>{c.name}</h5>
                  <span className="muted small">
                    {c.legal_name ?? "—"} · CIF {c.tax_id ?? "—"}
                  </span>
                </div>
                {!c.is_active && <span className="badge badge--muted">Inactiva</span>}
              </header>

              {c.subscription && (
                <div className="subscription-editor">
                  <div className="subscription-row">
                    <strong>Importe:</strong>{" "}
                    {formatMoney(c.subscription.amount_cents, c.subscription.currency)}
                    {c.subscription.billing_cycle === "annual" ? "/año" : "/mes"}
                    {c.subscription.max_active_users != null && (
                      <span className="muted small">
                        {" "}
                        · hasta {c.subscription.max_active_users} usuarios
                      </span>
                    )}
                  </div>
                  <div className="form-grid subscription-fields">
                    <label>
                      Tarifa
                      <select
                        value={c.subscription.pricing_plan_id ?? ""}
                        onChange={(e) =>
                          updateSubscription(c.subscription!.id, {
                            pricing_plan_id: e.target.value || null,
                            billing_cycle: c.subscription!.billing_cycle,
                          })
                        }
                      >
                        <option value="">—</option>
                        {plans.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} ({p.max_active_users} usuarios)
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Ciclo
                      <select
                        value={c.subscription.billing_cycle}
                        onChange={(e) =>
                          updateSubscription(c.subscription!.id, {
                            billing_cycle: e.target.value,
                          })
                        }
                      >
                        <option value="monthly">Mensual</option>
                        <option value="annual">Anual (12 meses)</option>
                      </select>
                    </label>
                    <label>
                      Descuento
                      <select
                        value={c.subscription.discount_id ?? ""}
                        onChange={(e) =>
                          updateSubscription(c.subscription!.id, {
                            discount_id: e.target.value || null,
                          })
                        }
                      >
                        <option value="">Sin descuento</option>
                        {activeDiscountsForPlan(c.subscription.pricing_plan_id).map(
                          (d) => (
                            <option key={d.id} value={d.id}>
                              {d.name} (
                              {d.discount_type === "percent"
                                ? `${d.value}%`
                                : formatMoney(d.value)}
                              )
                            </option>
                          )
                        )}
                      </select>
                    </label>
                    <label>
                      Estado
                      <select
                        value={c.subscription.status}
                        onChange={(e) =>
                          updateSubscription(c.subscription!.id, {
                            status: e.target.value,
                          })
                        }
                      >
                        {Object.entries(SUB_STATUS).map(([k, label]) => (
                          <option key={k} value={k}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>
              )}

              <dl className="billing-dl muted small">
                <div>
                  <dt>Email fact.</dt>
                  <dd>{c.billing_email ?? "—"}</dd>
                </div>
                <div>
                  <dt>Teléfono</dt>
                  <dd>{c.billing_phone ?? "—"}</dd>
                </div>
                <div>
                  <dt>Dirección</dt>
                  <dd>
                    {[c.billing_address, c.billing_postal_code, c.billing_city]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </dd>
                </div>
              </dl>

              {c.billing_methods.length > 0 && (
                <div className="company-methods">
                  <span className="small muted">Métodos de esta empresa:</span>
                  <ul className="billing-method-list">
                    {c.billing_methods
                      .filter((m) => m.company_id === c.id)
                      .map((m) => (
                        <li key={m.id}>
                          {m.label} ({METHOD_TYPE[m.method_type] ?? m.method_type})
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
