import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConnectionTest, SystemSettings } from "../api/types";
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

  const [ollama, setOllama] = useState<SystemSettings | null>(null);
  const [ollamaTest, setOllamaTest] = useState<ConnectionTest | null>(null);
  const [ollamaSaving, setOllamaSaving] = useState(false);

  const canTenant = user && canModule(user.permissions, "read", "tenant");
  const canBilling = user && hasPerm(user.permissions, "tenant.billing");
  const canSettings = user && canModule(user.permissions, "write", "settings");

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

  useEffect(() => {
    if (!canSettings) return;
    api.get<SystemSettings>("/settings").then(setOllama).catch(() => {});
  }, [canSettings]);

  const saveOllama = async (e: FormEvent) => {
    e.preventDefault();
    if (!ollama) return;
    setOllamaSaving(true);
    try {
      const updated = await api.put<SystemSettings>("/settings", {
        company_name: ollama.company_name,
        ollama_base_url: ollama.ollama_base_url,
        ollama_model: ollama.ollama_model,
      });
      setOllama(updated);
      setMsg("Integración Ollama guardada");
    } catch (err) {
      setMsg(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setOllamaSaving(false);
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

      {canSettings && ollama && (
        <form onSubmit={saveOllama} className="card settings-section">
          <h3>Integración Ollama (IA local)</h3>
          <p className="muted small">Configuración técnica del asistente por WhatsApp.</p>
          <div className="form-grid">
            <label>
              URL base
              <input
                value={ollama.ollama_base_url}
                onChange={(e) =>
                  setOllama({ ...ollama, ollama_base_url: e.target.value })
                }
              />
            </label>
            <label>
              Modelo
              <input
                value={ollama.ollama_model}
                onChange={(e) => setOllama({ ...ollama, ollama_model: e.target.value })}
              />
            </label>
          </div>
          <div className="test-row">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() =>
                api
                  .post<ConnectionTest>("/settings/test/ollama", {})
                  .then(setOllamaTest)
              }
            >
              Probar Ollama
            </button>
            {ollamaTest && (
              <span className={ollamaTest.ok ? "test-ok" : "test-fail"}>
                {ollamaTest.message}
              </span>
            )}
          </div>
          <button type="submit" className="btn btn-primary" disabled={ollamaSaving}>
            {ollamaSaving ? "Guardando…" : "Guardar Ollama"}
          </button>
        </form>
      )}

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
