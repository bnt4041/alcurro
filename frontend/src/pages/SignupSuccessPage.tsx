import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { publicApi } from "../api/public";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import { fireConfetti } from "../lib/confetti";

interface LocationState {
  slug?: string;
  hint?: string;
  company?: string;
}

export default function SignupSuccessPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const state = (location.state as LocationState) || {};

  const pendingId = searchParams.get("pending");

  const [pollStatus, setPollStatus] = useState<"polling" | "active" | "failed">(
    pendingId ? "polling" : "active"
  );
  const [tenantSlug, setTenantSlug] = useState<string | null>(state.slug ?? null);
  const [loginHint, setLoginHint] = useState<string | null>(state.hint ?? null);
  const [company] = useState<string | null>(state.company ?? null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    applyAlcurroDefaults();
  }, []);

  useEffect(() => {
    if (pollStatus === "active") {
      fireConfetti();
    }
  }, [pollStatus]);

  useEffect(() => {
    if (!pendingId) return;

    const poll = async () => {
      try {
        const res = await publicApi.getPendingSignup(pendingId);
        if (res.status === "active") {
          setTenantSlug(res.tenant_slug);
          setLoginHint(res.admin_login_hint);
          setPollStatus("active");
          if (intervalRef.current) clearInterval(intervalRef.current);
        } else if (res.status === "failed") {
          setErrorMsg(res.error_message ?? "Error desconocido al procesar el alta.");
          setPollStatus("failed");
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        // network error — keep polling
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [pendingId]);

  if (pollStatus === "polling") {
    return (
      <div className="signup-page signup-success">
        <div className="signup-page__inner card">
          <h1>Procesando tu alta…</h1>
          <p className="muted">
            Estamos verificando el pago y creando tu cuenta. Esto solo tarda unos segundos.
          </p>
          <div style={{ display: "flex", justifyContent: "center", margin: "2rem 0" }}>
            <span className="spinner" style={{ width: 40, height: 40, border: "4px solid var(--color-border)", borderTop: "4px solid var(--color-primary)", borderRadius: "50%", animation: "spin 0.9s linear infinite" }} />
          </div>
          <p className="muted small">No cierres esta pestaña.</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  if (pollStatus === "failed") {
    return (
      <div className="signup-page signup-success">
        <div className="signup-page__inner card">
          <h1>Error al activar la cuenta</h1>
          <div className="alert alert-error">
            {errorMsg ?? "No se pudo crear la cuenta. Contacta con soporte."}
          </div>
          <div className="signup-actions" style={{ marginTop: "1.5rem" }}>
            <Link to="/registro" className="btn btn-secondary">
              Volver al formulario
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="signup-page signup-success">
      <div className="signup-page__inner card">
        <h1>¡Cuenta creada!</h1>
        {company && (
          <p>
            Bienvenido a alcurro, <strong>{company}</strong>.
          </p>
        )}
        {tenantSlug && (
          <p>
            Tu código de cuenta es: <code>{tenantSlug}</code>
          </p>
        )}
        <div className="simulate-gowa card-inner">
          <h3>WhatsApp</h3>
          <p className="muted small">
            El fichaje por WhatsApp usa la línea compartida de alcurro. No necesitas
            vincular un número propio: solo asegúrate de que los empleados tengan su
            teléfono registrado en la ficha.
          </p>
        </div>
        {loginHint && <p className="muted">{loginHint}</p>}
        <div className="signup-actions">
          <Link to="/acceso" className="btn btn-primary">
            Iniciar sesión
          </Link>
          <Link to="/" className="btn btn-secondary">
            Inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
