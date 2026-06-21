import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  publicApi,
  type PublicDiscountPreview,
  type PublicPricingPlan,
  type PublicSignupBody,
} from "../api/public";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import {
  normalizeAccountCode,
  suggestAccountCode,
} from "../lib/slug";
import { formatMoney } from "../lib/money";
import { openPaddleCheckout } from "../lib/paddle";

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
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [discountPreview, setDiscountPreview] = useState<PublicDiscountPreview | null>(null);
  const [discountError, setDiscountError] = useState("");
  const discountCheckRef = useRef<string>("");
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
    if (form.company_name) {
      setForm((f) => ({
        ...f,
        account_code: suggestAccountCode(f.company_name, f.legal_name),
      }));
    }
  }, [form.company_name, form.legal_name]);

  const selectedPlan = plans.find((p) => p.id === planId);

  // Limpiar preview si cambia plan o ciclo
  useEffect(() => {
    setDiscountPreview(null);
    setDiscountError("");
  }, [planId, cycle]);

  const checkDiscount = async () => {
    const code = form.discount_code.trim().toUpperCase();
    if (!code || !planId) {
      setDiscountPreview(null);
      setDiscountError("");
      return;
    }
    discountCheckRef.current = code;
    try {
      const preview = await publicApi.discountPreview(planId, cycle, code);
      if (discountCheckRef.current === code) {
        setDiscountPreview(preview);
        setDiscountError("");
      }
    } catch {
      if (discountCheckRef.current === code) {
        setDiscountPreview(null);
        setDiscountError("Código de descuento no válido o expirado");
      }
    }
  };

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
      if (res.paddle_price_id && res.paddle_client_token) {
        await openPaddleCheckout({
          clientToken: res.paddle_client_token,
          env: res.paddle_env ?? "sandbox",
          priceId: res.paddle_price_id,
          customData: res.pending_signup_id
            ? { pending_signup_id: res.pending_signup_id }
            : undefined,
          customerEmail: res.customer_email ?? undefined,
          discountCode: res.paddle_discount_code,
          successUrl: res.success_url,
        });
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
                Código de cuenta (login)
                <input
                  readOnly
                  value={form.account_code}
                  placeholder="Se genera al escribir el nombre comercial"
                  style={{ background: "var(--color-bg-muted, #f5f5f5)", cursor: "default" }}
                />
                <span className="muted small">
                  Identificador único para el acceso de tu equipo — generado automáticamente
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
                  onChange={(e) => {
                    setForm({ ...form, discount_code: e.target.value });
                    if (!e.target.value.trim()) {
                      setDiscountPreview(null);
                      setDiscountError("");
                    }
                  }}
                  onBlur={checkDiscount}
                />
                {discountError && (
                  <span className="small" style={{ color: "var(--color-danger, #c0392b)" }}>
                    {discountError}
                  </span>
                )}
              </label>
            </div>
            {selectedPlan && (
              <p className="muted small signup-plan-hint">
                {cycle === "annual"
                  ? `Contrato anual: ${formatMoney(selectedPlan.annual_price_cents)} (pago único anual)`
                  : `Mensual: ${formatMoney(selectedPlan.monthly_price_cents)}/mes`}
                {discountPreview && (
                  <>
                    {" "}→{" "}
                    <strong style={{ color: "var(--color-ok, #27ae60)" }}>
                      {formatMoney(discountPreview.final_amount_cents)}
                      {cycle === "annual" ? " (anual con descuento)" : "/mes con descuento"}
                    </strong>
                  </>
                )}
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
