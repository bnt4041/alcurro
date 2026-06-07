import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import InvoiceHistoryTable from "../components/InvoiceHistoryTable";
import PageHeader from "../components/PageHeader";
import SubscriptionSummaryCard from "../components/SubscriptionSummaryCard";
import { useAuth } from "../context/AuthContext";
import { canModule, hasPerm } from "../lib/permissions";
import type { InvoiceRow, SubscriptionSummary } from "../lib/subscription";

interface TenantInfo {
  id: string;
  slug: string;
  name: string;
  logo_url: string | null;
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
}

interface BillingSummaryResponse {
  subscription: SubscriptionSummary | null;
  invoices: InvoiceRow[];
}

export default function AccountPage() {
  const { user } = useAuth();
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [billingSummary, setBillingSummary] = useState<BillingSummaryResponse | null>(
    null
  );
  const [billingLoading, setBillingLoading] = useState(true);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [msg, setMsg] = useState("");
  const [newCompany, setNewCompany] = useState({ name: "", tax_id: "" });
  const [logoUploading, setLogoUploading] = useState(false);

  const canTenant = user && canModule(user.permissions, "read", "tenant");
  const canWriteTenant = user && canModule(user.permissions, "write", "tenant");
  const canBilling = user && hasPerm(user.permissions, "tenant.billing");

  const load = useCallback(async () => {
    setBillingLoading(true);
    try {
      setTenant(await api.get<TenantInfo>("/tenants/current"));
      setCompanies(await api.get<Company[]>("/tenants/current/companies"));
      setBillingSummary(
        await api.get<BillingSummaryResponse>("/tenants/current/billing-summary")
      );
    } finally {
      setBillingLoading(false);
    }
  }, []);

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
      </section>

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
        />
      </section>

      <section className="card settings-section">
        <h3>Empresas de la cuenta</h3>
        <ul>
          {companies.map((c) => (
            <li key={c.id}>
              {c.name} {c.tax_id && `(${c.tax_id})`}
            </li>
          ))}
        </ul>
        <form onSubmit={addCompany} className="form-grid">
          <label>
            Nueva empresa
            <input
              required
              value={newCompany.name}
              onChange={(e) =>
                setNewCompany({ ...newCompany, name: e.target.value })
              }
            />
          </label>
          <label>
            CIF/NIF
            <input
              value={newCompany.tax_id}
              onChange={(e) =>
                setNewCompany({ ...newCompany, tax_id: e.target.value })
              }
            />
          </label>
          <button type="submit" className="btn">
            Añadir empresa
          </button>
        </form>
      </section>
    </>
  );
}
