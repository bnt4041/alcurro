import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  publicApi,
  type SimulateCheckoutPreview,
  type SimulatePaymentResponse,
} from "../api/public";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import { fireConfetti } from "../lib/confetti";
import { formatMoney } from "../lib/money";

export default function SignupSimulatePaymentPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";
  const [preview, setPreview] = useState<SimulateCheckoutPreview | null>(null);
  const [result, setResult] = useState<SimulatePaymentResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    applyAlcurroDefaults();
    if (!token) {
      setError("Falta el token de pago simulado");
      return;
    }
    setLoading(true);
    publicApi
      .getSimulateCheckout(token)
      .then(setPreview)
      .catch((err) => setError(String(err).replace(/^Error:\s*/i, "")))
      .finally(() => setLoading(false));
  }, [token]);

  const confirmPayment = async () => {
    if (!token) return;
    setPaying(true);
    setError("");
    try {
      const res = await publicApi.confirmSimulatePayment(token);
      setResult(res);
      if (!res.already_completed) fireConfetti();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setPaying(false);
    }
  };

  const goSuccess = () => {
    if (!result) return;
    navigate("/registro/ok", {
      state: {
        slug: result.tenant_slug,
        company: result.company_name,
      },
    });
  };

  if (result) {
    return (
      <div className="signup-page">
        <div className="signup-page__inner card simulate-pay">
          <span className="simulate-badge">Modo simulación</span>
          <h1>Pago simulado completado</h1>
          <p>
            Cuenta <strong>{result.company_name}</strong> ({result.tenant_slug})
          </p>
          <p className="muted">
            Importe: {formatMoney(result.amount_cents, result.currency)} · Suscripción{" "}
            {result.subscription_status}
          </p>

          <div className="simulate-gowa card-inner">
            <h3>WhatsApp</h3>
            <p className="muted small">
              Todas las cuentas usan la misma línea de WhatsApp de alcurro, configurada
              por el administrador de la plataforma.
            </p>
          </div>

          <div className="signup-actions">
            <button type="button" className="btn btn-primary" onClick={goSuccess}>
              Continuar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="signup-page">
      <div className="signup-page__inner card simulate-pay">
        <span className="simulate-badge">Modo simulación Stripe</span>
        <h1>Confirmar pago (prueba)</h1>
        <p className="muted">
          No se cargará ningún importe real. Al confirmar se activará la suscripción de
          la cuenta.
        </p>

        {loading && <p className="muted">Cargando…</p>}
        {error && <div className="alert alert-error">{error}</div>}

        {preview && !loading && (
          <>
            <dl className="simulate-summary">
              <dt>Empresa</dt>
              <dd>{preview.company_name}</dd>
              <dt>Cuenta</dt>
              <dd>
                <code>{preview.tenant_slug}</code>
              </dd>
              <dt>Tarifa</dt>
              <dd>
                {preview.plan_name} ({preview.billing_cycle === "annual" ? "anual" : "mensual"})
              </dd>
              <dt>Total</dt>
              <dd>
                <strong>{formatMoney(preview.amount_cents, preview.currency)}</strong>
              </dd>
            </dl>
            <div className="signup-actions">
              <Link to="/registro" className="btn btn-secondary">
                Cancelar
              </Link>
              <button
                type="button"
                className="btn btn-primary"
                disabled={paying}
                onClick={confirmPayment}
              >
                {paying ? "Procesando…" : "Simular pago y activar cuenta"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
