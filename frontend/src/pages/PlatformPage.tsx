import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import {
  isValidAccountCode,
  normalizeAccountCode,
  suggestAccountCode,
} from "../lib/slug";

interface GroupTemplate {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
  is_system: boolean;
}

interface TenantRow {
  id: string;
  slug: string;
  name: string;
  legal_name: string | null;
  tax_id: string | null;
  billing_email: string | null;
  billing_phone: string | null;
  is_active: boolean;
  created_at: string;
}

const emptyForm = {
  accountCode: "",
  name: "",
  legal_name: "",
  tax_id: "",
  billing_email: "",
  billing_phone: "",
  billing_address: "",
  billing_city: "",
  billing_postal_code: "",
  billing_province: "",
  billing_country: "ES",
};

export default function PlatformPage() {
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [templates, setTemplates] = useState<GroupTemplate[]>([]);
  const [form, setForm] = useState(emptyForm);
  /** Si el admin editó el código manualmente, no sobrescribir al cambiar el nombre. */
  const [accountCodeManual, setAccountCodeManual] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    setTenants(await api.get<TenantRow[]>("/platform/tenants"));
    setTemplates(await api.get<GroupTemplate[]>("/platform/group-templates"));
  };

  useEffect(() => {
    load();
  }, []);

  const syncAutoCode = (
    name: string,
    legalName: string,
    manual: boolean,
    currentCode: string
  ) => (manual ? currentCode : suggestAccountCode(name, legalName));

  const onNameChange = (name: string) => {
    setForm((f) => ({
      ...f,
      name,
      accountCode: syncAutoCode(name, f.legal_name, accountCodeManual, f.accountCode),
    }));
  };

  const onLegalNameChange = (legal_name: string) => {
    setForm((f) => ({
      ...f,
      legal_name,
      accountCode: syncAutoCode(f.name, legal_name, accountCodeManual, f.accountCode),
    }));
  };

  const onAccountCodeChange = (raw: string) => {
    setAccountCodeManual(true);
    setForm((f) => ({ ...f, accountCode: normalizeAccountCode(raw) }));
  };

  const regenerateCode = () => {
    setAccountCodeManual(false);
    setForm((f) => ({
      ...f,
      accountCode: suggestAccountCode(f.name, f.legal_name),
    }));
  };

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setMsg("");

    const autoSlug = suggestAccountCode(form.name, form.legal_name);
    const slug = normalizeAccountCode(form.accountCode || autoSlug);
    if (!isValidAccountCode(slug)) {
      setError("Indica un nombre comercial válido para generar el código de cuenta.");
      return;
    }

    const payload: Record<string, string | undefined> = {
      name: form.name.trim(),
      legal_name: form.legal_name.trim(),
      tax_id: form.tax_id.trim(),
      billing_email: form.billing_email.trim(),
      billing_phone: form.billing_phone.trim(),
      billing_address: form.billing_address.trim() || undefined,
      billing_city: form.billing_city.trim() || undefined,
      billing_postal_code: form.billing_postal_code.trim() || undefined,
      billing_province: form.billing_province.trim() || undefined,
      billing_country: form.billing_country.trim() || "ES",
    };
    if (accountCodeManual || form.accountCode.trim()) {
      payload.slug = slug;
    }

    try {
      const created = await api.post<TenantRow>("/platform/tenants", payload);
      const finalSlug = created.slug || slug;
      setMsg(`Cuenta «${form.name.trim()}» creada. Código de acceso: ${finalSlug}`);
      setForm(emptyForm);
      setAccountCodeManual(false);
      load();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  return (
    <>
      <PageHeader
        title="Cuentas cliente"
        subtitle="Administración global de alcurro"
      />
      {msg && <div className="alert alert-info">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <section className="card settings-section">
        <h3>Grupos por defecto (nuevos clientes)</h3>
        <p className="muted small">
          Al crear una cuenta se clonan estos grupos con sus permisos. El cliente puede
          personalizarlos después.
        </p>
        <ul className="template-list">
          {templates.map((t) => (
            <li key={t.id}>
              <strong>{t.name}</strong>
              {t.is_system && <span className="badge"> Sistema</span>}
              <div className="muted small">{t.description}</div>
              <div className="small">{t.permissions.length} permisos</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card settings-section">
        <h3>Nueva cuenta</h3>
        <p className="muted small">
          Los campos con <span className="required-mark">*</span> son obligatorios.
        </p>
        <form onSubmit={create} className="form-grid">
          <label>
            <span>
              Nombre comercial <span className="required-mark">*</span>
            </span>
            <input
              required
              value={form.name}
              onChange={(e) => onNameChange(e.target.value)}
            />
          </label>
          <label>
            <span>
              Razón social <span className="required-mark">*</span>
            </span>
            <input
              required
              value={form.legal_name}
              onChange={(e) => onLegalNameChange(e.target.value)}
            />
          </label>
          <label className="form-span-2">
            <span className="label-row">
              <span>Código de cuenta</span>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={regenerateCode}
                disabled={!form.name.trim() && !form.legal_name.trim()}
              >
                Regenerar
              </button>
            </span>
            <input
              readOnly={!accountCodeManual}
              placeholder="Se genera al escribir el nombre"
              value={form.accountCode}
              onChange={(e) => onAccountCodeChange(e.target.value)}
              onFocus={() => setAccountCodeManual(true)}
            />
            <span className="field-hint muted small">
              {accountCodeManual
                ? "Has personalizado el código. Los empleados lo usarán en «Acceso a tu cuenta»."
                : "Se genera automáticamente desde el nombre. Haz clic para editarlo si lo necesitas."}
              {form.accountCode && (
                <>
                  {" "}
                  Vista previa: <code>{form.accountCode}</code>
                </>
              )}
            </span>
          </label>
          <label>
            <span>
              CIF/NIF <span className="required-mark">*</span>
            </span>
            <input
              required
              value={form.tax_id}
              onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
            />
          </label>
          <label>
            <span>
              Email facturación <span className="required-mark">*</span>
            </span>
            <input
              type="email"
              required
              value={form.billing_email}
              onChange={(e) => setForm({ ...form, billing_email: e.target.value })}
            />
          </label>
          <label>
            <span>
              Teléfono <span className="required-mark">*</span>
            </span>
            <input
              type="tel"
              required
              placeholder="ej. +34 600 000 000"
              value={form.billing_phone}
              onChange={(e) => setForm({ ...form, billing_phone: e.target.value })}
            />
          </label>
          <label>
            Dirección
            <input
              value={form.billing_address}
              onChange={(e) => setForm({ ...form, billing_address: e.target.value })}
            />
          </label>
          <label>
            Ciudad
            <input
              value={form.billing_city}
              onChange={(e) => setForm({ ...form, billing_city: e.target.value })}
            />
          </label>
          <label>
            CP
            <input
              value={form.billing_postal_code}
              onChange={(e) => setForm({ ...form, billing_postal_code: e.target.value })}
            />
          </label>
          <label>
            Provincia
            <input
              value={form.billing_province}
              onChange={(e) => setForm({ ...form, billing_province: e.target.value })}
            />
          </label>
          <button type="submit" className="btn btn-primary">
            Crear cuenta
          </button>
        </form>
      </section>

      <div className="table-wrap card">
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Razón social</th>
              <th>CIF</th>
              <th>Email fact.</th>
              <th>Teléfono</th>
              <th>Activa</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => (
              <tr key={t.id}>
                <td>
                  <code>{t.slug}</code>
                </td>
                <td>{t.name}</td>
                <td>{t.legal_name ?? "—"}</td>
                <td>{t.tax_id ?? "—"}</td>
                <td>{t.billing_email ?? "—"}</td>
                <td>{t.billing_phone ?? "—"}</td>
                <td>{t.is_active ? "Sí" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
