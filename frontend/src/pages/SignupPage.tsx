import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  publicApi,
  type PublicPricingPlan,
  type PublicSignupBody,
} from "../api/public";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import {
  isValidAccountCode,
  normalizeAccountCode,
  suggestAccountCode,
} from "../lib/slug";
import { formatMoney } from "../lib/money";

const emptyForm = () => ({
  company_name: "",
  legal_name: "",
  tax_id: "",
  billing_email: "",
  billing_phone: "",
  billing_address: "",
  billing_city: "",
  billing_postal_code: "",
  billing_province: "",
  billing_country: "ES",
  account_code: "",
  admin_name: "",
  admin_email: "",
  admin_phone: "",
  admin_password: "",
  admin_password2: "",
  discount_code: "",
  accept_terms: false,
});

export default function SignupPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<PublicPricingPlan[]>([]);
  const [planId, setPlanId] = useState("");
  const [cycle, setCycle] = useState<"monthly" | "annual">("monthly");
  const [form, setForm] = useState(emptyForm);
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    applyAlcurroDefaults();
    publicApi.getPlans().then((list) => {
      setPlans(list);
      const fromUrl = searchParams.get("plan");
      const pick = fromUrl && list.some((p) => p.id === fromUrl) ? fromUrl : list[0]?.id;
      if (pick) setPlanId(pick);
    });
    if (searchParams.get("cancelled")) {
      setError("Pago cancelado. Puedes completar el alta o intentar de nuevo.");
    }
  }, [searchParams]);

  useEffect(() => {
    if (!slugTouched && form.company_name) {
      setForm((f) => ({
        ...f,
        account_code: suggestAccountCode(f.company_name, f.legal_name),
      }));
    }
  }, [form.company_name, form.legal_name, slugTouched]);

  const selectedPlan = plans.find((p) => p.id === planId);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!planId) {
      setError("Selecciona una tarifa");
      return;
    }
    if (!form.accept_terms) {
      setError("Debes aceptar los términos y condiciones");
      return;
    }
    if (form.admin_password !== form.admin_password2) {
      setError("Las contraseñas no coinciden");
      return;
    }
    const code = normalizeAccountCode(form.account_code);
    if (!isValidAccountCode(code)) {
      setError(
        "Código de cuenta inválido: solo minúsculas, números y guiones (mín. 2 caracteres)"
      );
      return;
    }
    const body: PublicSignupBody = {
      company_name: form.company_name.trim(),
      legal_name: form.legal_name.trim(),
      tax_id: form.tax_id.trim(),
      billing_email: form.billing_email.trim(),
      billing_phone: form.billing_phone.trim(),
      billing_address: form.billing_address.trim() || undefined,
      billing_city: form.billing_city.trim() || undefined,
      billing_postal_code: form.billing_postal_code.trim() || undefined,
      billing_province: form.billing_province.trim() || undefined,
      billing_country: form.billing_country.trim() || "ES",
      account_code: code,
      pricing_plan_id: planId,
      billing_cycle: cycle,
      discount_code: form.discount_code.trim() || undefined,
      admin_name: form.admin_name.trim(),
      admin_email: form.admin_email.trim(),
      admin_phone: form.admin_phone.trim(),
      admin_password: form.admin_password,
      accept_terms: true,
    };
    setLoading(true);
    try {
      const res = await publicApi.signup(body);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
        return;
      }
      navigate("/registro/ok", {
        state: {
          slug: res.tenant_slug,
          hint: res.admin_login_hint,
          company: res.company_name,
        },
      });
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-page">
      <div className="signup-page__inner">
        <h1>Alta de cliente</h1>
        <p className="muted">
          Crea tu cuenta alcurro. Tras el registro podrás acceder con tu código de
          cuenta y el usuario administrador ADM001.
        </p>
        {error && <div className="alert alert-error">{error}</div>}

        <form className="signup-form card" onSubmit={submit}>
          <fieldset>
            <legend>Empresa y facturación</legend>
            <div className="form-grid">
              <label>
                Nombre comercial <span className="required">*</span>
                <input
                  required
                  value={form.company_name}
                  onChange={(e) =>
                    setForm({ ...form, company_name: e.target.value })
                  }
                />
              </label>
              <label>
                Razón social <span className="required">*</span>
                <input
                  required
                  value={form.legal_name}
                  onChange={(e) =>
                    setForm({ ...form, legal_name: e.target.value })
                  }
                />
              </label>
              <label>
                CIF/NIF <span className="required">*</span>
                <input
                  required
                  value={form.tax_id}
                  onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
                />
              </label>
              <label>
                Email facturación <span className="required">*</span>
                <input
                  type="email"
                  required
                  value={form.billing_email}
                  onChange={(e) =>
                    setForm({ ...form, billing_email: e.target.value })
                  }
                />
              </label>
              <label>
                Teléfono <span className="required">*</span>
                <input
                  required
                  value={form.billing_phone}
                  onChange={(e) =>
                    setForm({ ...form, billing_phone: e.target.value })
                  }
                />
              </label>
              <label className="full">
                Código de cuenta (login) <span className="required">*</span>
                <input
                  required
                  value={form.account_code}
                  onChange={(e) => {
                    setSlugTouched(true);
                    setForm({
                      ...form,
                      account_code: normalizeAccountCode(e.target.value),
                    });
                  }}
                  placeholder="ej. mi-empresa"
                />
                <span className="muted small">
                  Identificador único para el acceso de tu equipo
                </span>
              </label>
            </div>
          </fieldset>

          <fieldset>
            <legend>Tarifa</legend>
            <div className="form-grid">
              <label>
                Plan <span className="required">*</span>
                <select
                  required
                  value={planId}
                  onChange={(e) => setPlanId(e.target.value)}
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {formatMoney(p.monthly_price_cents)}/mes
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Ciclo de facturación
                <select
                  value={cycle}
                  onChange={(e) =>
                    setCycle(e.target.value as "monthly" | "annual")
                  }
                >
                  <option value="monthly">Mensual</option>
                  <option value="annual">Anual (mejor precio)</option>
                </select>
              </label>
              <label>
                Código descuento
                <input
                  value={form.discount_code}
                  onChange={(e) =>
                    setForm({ ...form, discount_code: e.target.value })
                  }
                />
              </label>
            </div>
            {selectedPlan && (
              <p className="muted small signup-plan-hint">
                {cycle === "annual"
                  ? `Contrato anual: ${formatMoney(
                      selectedPlan.annual_price_cents
                    )} (pago único anual)`
                  : `Mensual: ${formatMoney(selectedPlan.monthly_price_cents)}/mes`}
              </p>
            )}
          </fieldset>

          <fieldset>
            <legend>Administrador (ADM001)</legend>
            <div className="form-grid">
              <label>
                Nombre <span className="required">*</span>
                <input
                  required
                  value={form.admin_name}
                  onChange={(e) =>
                    setForm({ ...form, admin_name: e.target.value })
                  }
                />
              </label>
              <label>
                Email <span className="required">*</span>
                <input
                  type="email"
                  required
                  value={form.admin_email}
                  onChange={(e) =>
                    setForm({ ...form, admin_email: e.target.value })
                  }
                />
              </label>
              <label>
                Teléfono móvil <span className="required">*</span>
                <input
                  required
                  value={form.admin_phone}
                  onChange={(e) =>
                    setForm({ ...form, admin_phone: e.target.value })
                  }
                />
              </label>
              <label>
                Contraseña <span className="required">*</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={form.admin_password}
                  onChange={(e) =>
                    setForm({ ...form, admin_password: e.target.value })
                  }
                />
              </label>
              <label>
                Repetir contraseña <span className="required">*</span>
                <input
                  type="password"
                  required
                  value={form.admin_password2}
                  onChange={(e) =>
                    setForm({ ...form, admin_password2: e.target.value })
                  }
                />
              </label>
            </div>
          </fieldset>

          <label className="signup-terms">
            <input
              type="checkbox"
              checked={form.accept_terms}
              onChange={(e) =>
                setForm({ ...form, accept_terms: e.target.checked })
              }
            />
            <span>
              He leído y acepto el{" "}
              <Link to="/aviso-legal" target="_blank" rel="noopener">aviso legal</Link>,
              la{" "}
              <Link to="/privacidad" target="_blank" rel="noopener">política de privacidad</Link>{" "}
              y las condiciones del servicio.
            </span>
          </label>

          <div className="signup-actions">
            <Link to="/" className="btn btn-secondary">
              Volver
            </Link>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !plans.length}
            >
              {loading ? "Creando cuenta…" : "Crear cuenta"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
