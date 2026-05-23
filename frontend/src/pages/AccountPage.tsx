import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { canModule, hasPerm } from "../lib/permissions";
import PageHeader from "../components/PageHeader";

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
  logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  gowa_port: number | null;
  gowa_ui_url: string;
  gowa_status: string;
  gowa_error: string | null;
}

interface Company {
  id: string;
  name: string;
  tax_id: string | null;
}

export default function AccountPage() {
  const { user } = useAuth();
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [msg, setMsg] = useState("");
  const [newCompany, setNewCompany] = useState({ name: "", tax_id: "" });

  const load = useCallback(async () => {
    setTenant(await api.get<TenantInfo>("/tenants/current"));
    setCompanies(await api.get<Company[]>("/tenants/current/companies"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const saveBranding = async (e: FormEvent) => {
    e.preventDefault();
    if (!tenant) return;
    await api.patch("/tenants/current/branding", tenant);
    setMsg("Personalización guardada");
  };

  const provisionGowa = async () => {
    setMsg("Provisionando goWA…");
    const t = await api.post<TenantInfo>("/tenants/current/provision-gowa", {});
    setTenant(t);
    setMsg(
      t.gowa_status === "running"
        ? `WhatsApp listo en ${t.gowa_ui_url}`
        : `Error: ${t.gowa_error ?? t.gowa_status}`
    );
  };

  const addCompany = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/tenants/current/companies", newCompany);
    setNewCompany({ name: "", tax_id: "" });
    load();
    setMsg("Empresa creada");
  };

  const canTenant = user && canModule(user.permissions, "read", "tenant");
  const canBilling = user && hasPerm(user.permissions, "tenant.billing");
  const canGowa = user && hasPerm(user.permissions, "gowa.manage");

  if (!canTenant) {
    return <p className="muted">No tienes permiso para gestionar la cuenta.</p>;
  }

  return (
    <>
      <PageHeader
        title="Cuenta y white-label"
        subtitle={`Tenant: ${user.tenant_name} (${user.tenant_slug})`}
      />
      {msg && <div className="alert alert-info">{msg}</div>}

      {tenant && (
        <form onSubmit={saveBranding} className="card settings-section">
          <h3>Personalización (zona blanca)</h3>
          <div className="form-grid">
            <label>
              Logo URL
              <input
                value={tenant.logo_url ?? ""}
                onChange={(e) =>
                  setTenant({ ...tenant, logo_url: e.target.value || null })
                }
                placeholder="https://…/logo.png"
              />
            </label>
            <label>
              Color primario
              <input
                type="color"
                value={tenant.primary_color}
                onChange={(e) =>
                  setTenant({ ...tenant, primary_color: e.target.value })
                }
              />
            </label>
            <label>
              Color sidebar
              <input
                type="color"
                value={tenant.secondary_color}
                onChange={(e) =>
                  setTenant({ ...tenant, secondary_color: e.target.value })
                }
              />
            </label>
            <label>
              Color acento
              <input
                type="color"
                value={tenant.accent_color}
                onChange={(e) =>
                  setTenant({ ...tenant, accent_color: e.target.value })
                }
              />
            </label>
          </div>
          <button type="submit" className="btn btn-primary">
            Guardar colores y logo
          </button>
        </form>
      )}

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
          <p className="muted small">Campos mínimos para emitir facturas de la cuenta.</p>
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

      {canGowa && (
      <section className="card settings-section">
        <h3>WhatsApp dedicado (goWA)</h3>
        <p className="muted small">
          Cada cuenta obtiene su propio contenedor Docker y puerto para vincular un
          móvil.
        </p>
        {tenant && (
          <>
            <p>
              Estado: <strong>{tenant.gowa_status}</strong>
              {tenant.gowa_port && ` · puerto ${tenant.gowa_port}`}
            </p>
            {tenant.gowa_ui_url && (
              <p>
                Panel QR:{" "}
                <a href={tenant.gowa_ui_url} target="_blank" rel="noreferrer">
                  {tenant.gowa_ui_url}
                </a>
              </p>
            )}
            <button type="button" className="btn btn-primary" onClick={provisionGowa}>
              Crear / reiniciar contenedor goWA
            </button>
          </>
        )}
      </section>
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
