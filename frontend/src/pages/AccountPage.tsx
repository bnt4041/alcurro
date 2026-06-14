import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import Modal from "../components/Modal";
import InvoiceHistoryTable from "../components/InvoiceHistoryTable";
import PageHeader from "../components/PageHeader";
import SubscriptionSummaryCard from "../components/SubscriptionSummaryCard";
import { useAuth } from "../context/AuthContext";
import { canModule, hasPerm } from "../lib/permissions";
import type { InvoiceRow, SubscriptionSummary } from "../lib/subscription";
import { publicApi, type PublicPricingPlan } from "../api/public";
import { formatMoney } from "../lib/money";
import { useToast } from "../context/ToastContext";

interface TenantInfo {
  id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  billing_company_id: string | null;
  legal_name: string | null;
  tax_id: string | null;
  billing_email: string | null;
  billing_phone: string | null;
  billing_address: string | null;
  billing_city: string | null;
  billing_postal_code: string | null;
  billing_province: string | null;
  billing_country: string;
}

interface Company {
  id: string;
  name: string;
  tax_id: string | null;
  is_active: boolean;
}

interface BillingSummaryResponse {
  subscription: SubscriptionSummary | null;
  invoices: InvoiceRow[];
  active_users: number;
  max_users: number | null;
  customer_portal_url?: string | null;
}

export default function AccountPage() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [billingSummary, setBillingSummary] = useState<BillingSummaryResponse | null>(null);
  const [billingLoading, setBillingLoading] = useState(true);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [msg, setMsg] = useState("");
  const [newCompany, setNewCompany] = useState({ name: "", tax_id: "" });
  const [logoUploading, setLogoUploading] = useState(false);

  // Edición de empresa
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [editCompanyForm, setEditCompanyForm] = useState({ name: "", tax_id: "" });
  const [editCompanySaving, setEditCompanySaving] = useState(false);

  // Plan change
  const [plans, setPlans] = useState<PublicPricingPlan[]>([]);
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<PublicPricingPlan | null>(null);
  const [selectedCycle, setSelectedCycle] = useState<"monthly" | "annual">("monthly");
  const [planChanging, setPlanChanging] = useState(false);

  const canTenant = user && canModule(user.permissions, "read", "tenant");
  const canWriteTenant = user && canModule(user.permissions, "write", "tenant");
  const canBilling = user && hasPerm(user.permissions, "tenant.billing");

  const load = useCallback(async () => {
    setBillingLoading(true);
    try {
      const [tenantData, companiesData, summaryData] = await Promise.all([
        api.get<TenantInfo>("/tenants/current"),
        api.get<Company[]>("/tenants/current/companies"),
        api.get<BillingSummaryResponse>("/tenants/current/billing-summary"),
      ]);
      setTenant(tenantData);
      setCompanies(companiesData);
      setBillingSummary(summaryData);
    } finally {
      setBillingLoading(false);
    }
  }, []);

  useEffect(() => {
    publicApi.getPlans().then(setPlans).catch(() => setPlans([]));
  }, []);

  const openPlanChange = (plan: PublicPricingPlan) => {
    setSelectedPlan(plan);
    setSelectedCycle("monthly");
    setPlanModalOpen(true);
  };

  const confirmPlanChange = async () => {
    if (!selectedPlan) return;
    setPlanChanging(true);
    try {
      const result = await api.post<{ ok: boolean; message: string }>(
        "/tenants/current/change-plan",
        { plan_id: selectedPlan.id, billing_cycle: selectedCycle }
      );
      notify(result.message, "success");
      setPlanModalOpen(false);
      load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setPlanChanging(false);
    }
  };

  useEffect(() => {
    load();
  }, [load]);

  const uploadLogo = async (file: File) => {
    if (!canWriteTenant) return;
    setLogoUploading(true);
    setMsg("");
    try {
      const form = new FormData();
      form.append("file", file);
      const updated = await api.upload<TenantInfo>("/tenants/current/logo", form);
      setTenant(updated);
      setMsg("Logo actualizado");
    } catch (err) {
      setMsg(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setLogoUploading(false);
    }
  };

  const removeLogo = async () => {
    if (!canWriteTenant || !tenant?.logo_url) return;
    if (!confirm("¿Quitar el logo de la cuenta?")) return;
    setLogoUploading(true);
    try {
      await api.delete("/tenants/current/logo");
      await load();
      setMsg("Logo eliminado");
    } catch (err) {
      setMsg(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setLogoUploading(false);
    }
  };

  const addCompany = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/tenants/current/companies", newCompany);
    setNewCompany({ name: "", tax_id: "" });
    load();
    setMsg("Empresa creada");
  };

  if (!canTenant) {
    return <p className="muted">No tienes permiso para gestionar la cuenta.</p>;
  }

  return (
    <>
      <PageHeader
        title="Cuenta"
        subtitle={`${user.tenant_name} · código ${user.tenant_slug}`}
      />
      {msg && <div className="alert alert-info">{msg}</div>}

      {tenant && (
        <section className="card settings-section">
          <h3>Identidad visual</h3>
          <p className="muted small">
            Logo opcional de tu cuenta. Se muestra en el panel de inicio y en la
            página pública de firma de documentos.
          </p>
          <div className="account-logo-row">
            <div className="account-logo-preview">
              {tenant.logo_url ? (
                <img src={tenant.logo_url} alt={`Logo ${tenant.name}`} />
              ) : (
                <span className="muted small">Sin logo</span>
              )}
            </div>
            {canWriteTenant && (
              <div className="account-logo-actions">
                <label className={`btn btn-sm btn-primary${logoUploading ? " disabled" : ""}`}>
                  {logoUploading ? "Subiendo…" : tenant.logo_url ? "Cambiar logo" : "Subir logo"}
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/svg+xml"
                    hidden
                    disabled={logoUploading}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) uploadLogo(file);
                      e.target.value = "";
                    }}
                  />
                </label>
                {tenant.logo_url && (
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={logoUploading}
                    onClick={removeLogo}
                  >
                    Quitar logo
                  </button>
                )}
              </div>
            )}
          </div>
          <p className="muted small" style={{ marginTop: "0.25rem" }}>
            PNG, JPG, WEBP o SVG · máx. 2 MB
          </p>
        </section>
      )}

      <section className="card settings-section">
        <h3>Suscripción y tarifa</h3>
        <SubscriptionSummaryCard
          subscription={billingSummary?.subscription ?? null}
          loading={billingLoading}
        />
        {billingSummary && billingSummary.max_users != null && (
          <div className={`alert ${billingSummary.active_users >= billingSummary.max_users ? "alert-warning" : "alert-info"}`} style={{ marginTop: "0.75rem" }}>
            Usuarios activos: <strong>{billingSummary.active_users} / {billingSummary.max_users}</strong>
            {billingSummary.active_users >= billingSummary.max_users && (
              <> — Has alcanzado el límite. Cambia de tarifa en la sección inferior para añadir más empleados.</>
            )}
          </div>
        )}
        {billingSummary?.subscription?.pending_plan_id && (
          <div className="alert alert-info" style={{ marginTop: "0.75rem" }}>
            Cambio de tarifa programado para el final del período actual.
          </div>
        )}
        {billingSummary?.customer_portal_url && (
          <div style={{ marginTop: "1rem" }}>
            <a
              href={billingSummary.customer_portal_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary btn-sm"
            >
              Portal de cliente (Lemon Squeezy)
            </a>
            <p className="muted small" style={{ marginTop: "0.4rem" }}>
              Actualiza tu método de pago, descarga facturas y gestiona tu suscripción.
            </p>
          </div>
        )}
      </section>

      {canBilling && plans.length > 0 && (
        <section className="card settings-section">
          <h3>Cambiar tarifa</h3>
          <p className="muted small">
            El cambio se aplica al inicio del siguiente período de facturación.
            {billingSummary?.subscription?.billing_cycle === "annual" && (
              <> No se permite downgrade con una suscripción anual activa.</>
            )}
          </p>
          <div className="plan-change-grid">
            {plans.map((plan) => {
              const isCurrent = billingSummary?.subscription?.plan_code === plan.code
                || billingSummary?.subscription?.plan_name === plan.name;
              return (
                <div key={plan.id} className={`plan-change-card${isCurrent ? " plan-change-card--current" : ""}`}>
                  {isCurrent && <span className="plan-change-card__badge">Plan actual</span>}
                  <h4>{plan.name}</h4>
                  {plan.description && <p className="muted small">{plan.description}</p>}
                  <p className="plan-change-card__price">
                    {formatMoney(plan.monthly_price_cents, plan.currency)}
                    <span className="muted"> /mes</span>
                  </p>
                  <p className="muted small">
                    Anual: {formatMoney(plan.annual_price_cents, plan.currency)}/año
                  </p>
                  <p className="muted small">Hasta {plan.max_active_users} usuarios</p>
                  {!isCurrent && (
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => openPlanChange(plan)}
                    >
                      Cambiar a {plan.name}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <Modal
        title={`Cambiar a ${selectedPlan?.name ?? ""}`}
        open={planModalOpen}
        onClose={() => setPlanModalOpen(false)}
      >
        {selectedPlan && (
          <div>
            <p>
              Estás a punto de solicitar el cambio de tarifa a{" "}
              <strong>{selectedPlan.name}</strong>. El cambio se aplicará al
              inicio del siguiente período de facturación.
            </p>
            <div className="form-grid" style={{ marginTop: "1rem" }}>
              <label>
                Ciclo de facturación
                <select
                  value={selectedCycle}
                  onChange={(e) => setSelectedCycle(e.target.value as "monthly" | "annual")}
                >
                  <option value="monthly">
                    Mensual — {formatMoney(selectedPlan.monthly_price_cents, selectedPlan.currency)}/mes
                  </option>
                  <option value="annual">
                    Anual — {formatMoney(selectedPlan.annual_price_cents, selectedPlan.currency)}/año
                  </option>
                </select>
              </label>
            </div>
            <div className="form-actions" style={{ marginTop: "1.5rem" }}>
              <button type="button" className="btn" onClick={() => setPlanModalOpen(false)}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={planChanging}
                onClick={confirmPlanChange}
              >
                {planChanging ? "Procesando…" : "Confirmar cambio"}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {canBilling && tenant && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await api.patch("/tenants/current/billing", {
              legal_name: tenant.legal_name,
              tax_id: tenant.tax_id,
              billing_email: tenant.billing_email,
              billing_phone: tenant.billing_phone,
              billing_address: tenant.billing_address,
              billing_city: tenant.billing_city,
              billing_postal_code: tenant.billing_postal_code,
              billing_province: tenant.billing_province,
              billing_country: tenant.billing_country,
            });
            setMsg("Datos de facturación guardados");
          }}
          className="card settings-section"
        >
          <h3>Datos de facturación</h3>
          <p className="muted small">
            Información fiscal y de contacto para las facturas de tu cuenta.
          </p>
          <div className="form-grid">
            <label>
              Razón social
              <input
                required
                value={tenant.legal_name ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, legal_name: e.target.value || null })
                }
              />
            </label>
            <label>
              CIF/NIF
              <input
                required
                value={tenant.tax_id ?? ""}
                onChange={(e) => setTenant({ ...tenant, tax_id: e.target.value || null })}
              />
            </label>
            <label>
              Email facturación
              <input
                type="email"
                required
                value={tenant.billing_email ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_email: e.target.value || null })
                }
              />
            </label>
            <label>
              Teléfono
              <input
                value={tenant.billing_phone ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_phone: e.target.value || null })
                }
              />
            </label>
            <label>
              Dirección
              <input
                required
                value={tenant.billing_address ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_address: e.target.value || null })
                }
              />
            </label>
            <label>
              Ciudad
              <input
                required
                value={tenant.billing_city ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_city: e.target.value || null })
                }
              />
            </label>
            <label>
              Código postal
              <input
                required
                value={tenant.billing_postal_code ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_postal_code: e.target.value || null })
                }
              />
            </label>
            <label>
              Provincia
              <input
                value={tenant.billing_province ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_province: e.target.value || null })
                }
              />
            </label>
            <label>
              País
              <input
                maxLength={2}
                value={tenant.billing_country ?? "ES"}
                onChange={(e) =>
                  setTenant({ ...tenant, billing_country: e.target.value })
                }
              />
            </label>
          </div>
          <button type="submit" className="btn btn-primary">
            Guardar facturación
          </button>
        </form>
      )}

      <section className="card settings-section">
        <h3>Histórico de facturas</h3>
        <InvoiceHistoryTable
          invoices={billingSummary?.invoices ?? []}
          loading={billingLoading}
          onDownload={async (id, filename) => {
            try {
              await api.download(`/tenants/current/invoices/${id}/pdf`, filename);
            } catch (err) {
              notify(String(err).replace(/^Error:\s*/i, ""), "error");
            }
          }}
        />
      </section>

      <section className="card settings-section">
        <h3>Empresas de la cuenta</h3>
        <p className="muted small">
          Cada empresa tiene su propia estructura organizativa (centros de trabajo y departamentos) y sus propios empleados.{tenant?.billing_company_id && <> La marcada como <strong>Facturación</strong> es la que aparecerá como titular en las facturas.</>}
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem" }}>
          {companies.map((c) => (
            <div key={c.id} className="company-row" style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "0.5rem 0.75rem", border: "1px solid var(--c-border)", borderRadius: 6 }}>
              <div style={{ flex: 1 }}>
                <strong>{c.name}</strong>
                {tenant?.billing_company_id === c.id && (
                  <span className="badge badge--info" style={{ marginLeft: "0.5rem" }}>Facturación</span>
                )}
                {c.tax_id && <span className="muted small" style={{ marginLeft: "0.5rem" }}>CIF/NIF: {c.tax_id}</span>}
                {!c.is_active && <span className="badge badge--danger" style={{ marginLeft: "0.5rem" }}>Inactiva</span>}
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                {canWriteTenant && tenant?.billing_company_id !== c.id && c.is_active && (
                  <button
                    type="button"
                    className="btn btn-xs"
                    onClick={async () => {
                      try {
                        await api.put("/tenants/current/billing-company", { company_id: c.id });
                        notify(`«${c.name}» establecida como empresa de facturación`, "success");
                        load();
                      } catch (err) {
                        notify(String(err).replace(/^Error:\s*/i, ""), "error");
                      }
                    }}
                  >
                    Facturar aquí
                  </button>
                )}
                {canWriteTenant && (
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => {
                      setEditingCompany(c);
                      setEditCompanyForm({ name: c.name, tax_id: c.tax_id ?? "" });
                    }}
                  >
                    Editar
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {canWriteTenant && (
          <form onSubmit={addCompany} className="form-grid">
            <label>
              Nueva empresa
              <input
                required
                value={newCompany.name}
                onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })}
              />
            </label>
            <label>
              CIF/NIF
              <input
                value={newCompany.tax_id}
                onChange={(e) => setNewCompany({ ...newCompany, tax_id: e.target.value })}
              />
            </label>
            <button type="submit" className="btn">
              Añadir empresa
            </button>
          </form>
        )}
      </section>

      <Modal
        title={`Editar empresa — ${editingCompany?.name ?? ""}`}
        open={!!editingCompany}
        onClose={() => setEditingCompany(null)}
      >
        <div className="form-grid">
          <label>
            Nombre <span className="required">*</span>
            <input
              required
              value={editCompanyForm.name}
              onChange={(e) => setEditCompanyForm({ ...editCompanyForm, name: e.target.value })}
            />
          </label>
          <label>
            CIF/NIF
            <input
              value={editCompanyForm.tax_id}
              onChange={(e) => setEditCompanyForm({ ...editCompanyForm, tax_id: e.target.value })}
            />
          </label>
        </div>
        <div className="form-actions" style={{ marginTop: "1.5rem" }}>
          <button type="button" className="btn" onClick={() => setEditingCompany(null)}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={editCompanySaving}
            onClick={async () => {
              if (!editingCompany) return;
              setEditCompanySaving(true);
              try {
                await api.patch(`/tenants/current/companies/${editingCompany.id}`, {
                  name: editCompanyForm.name || undefined,
                  tax_id: editCompanyForm.tax_id || null,
                });
                notify("Empresa actualizada", "success");
                setEditingCompany(null);
                load();
              } catch (err) {
                notify(String(err).replace(/^Error:\s*/i, ""), "error");
              } finally {
                setEditCompanySaving(false);
              }
            }}
          >
            {editCompanySaving ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </Modal>
    </>
  );
}
