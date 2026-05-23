import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import { fireConfetti } from "../lib/confetti";

interface LocationState {
  slug?: string;
  hint?: string;
  company?: string;
}

export default function SignupSuccessPage() {
  const location = useLocation();
  const state = (location.state as LocationState) || {};

  useEffect(() => {
    applyAlcurroDefaults();
    fireConfetti();
  }, []);

  return (
    <div className="signup-page signup-success">
      <div className="signup-page__inner card">
        <h1>¡Cuenta creada!</h1>
        {state.company && (
          <p>
            Bienvenido a alcurro, <strong>{state.company}</strong>.
          </p>
        )}
        {state.slug && (
          <p>
            Tu código de cuenta es: <code>{state.slug}</code>
          </p>
        )}
        {state.hint && <p className="muted">{state.hint}</p>}
        <div className="signup-actions">
          <Link to="/acceso-cliente" className="btn btn-primary">
            Ir al acceso cliente
          </Link>
          <Link to="/" className="btn btn-secondary">
            Inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
