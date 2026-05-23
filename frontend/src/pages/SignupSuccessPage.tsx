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
        <div className="simulate-gowa card-inner">
          <h3>WhatsApp</h3>
          <p className="muted small">
            El fichaje por WhatsApp usa la línea compartida de alcurro. No necesitas
            vincular un número propio: solo asegúrate de que los empleados tengan su
            teléfono registrado en la ficha.
          </p>
        </div>
        {state.hint && <p className="muted">{state.hint}</p>}
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
