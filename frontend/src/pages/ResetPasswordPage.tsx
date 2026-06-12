import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { applyAlcurroDefaults } from "../hooks/useBranding";

export default function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    applyAlcurroDefaults();
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!password || password.length < 4) {
      setError("La contraseña debe tener al menos 4 caracteres");
      return;
    }
    if (password !== confirm) {
      setError("Las contraseñas no coinciden");
      return;
    }
    if (!token) {
      setError("Token no encontrado en la URL");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/public/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
        headers: { "Content-Type": "application/json" },
      });
      const data = await res.json();
      if (data.ok) {
        setDone(true);
      } else {
        setError(data.message || "Error al cambiar la contraseña");
      }
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <BrandLogo variant="light" showTagline />

        {done ? (
          <>
            <div className="alert alert-success">
              <strong>¡Contraseña actualizada!</strong>
              <p className="muted small" style={{ marginTop: "0.5rem" }}>
                Ya puedes iniciar sesión con tu nueva contraseña.
              </p>
            </div>
            <Link to="/acceso" className="btn btn-primary btn-block" style={{ marginTop: "1rem" }}>
              Ir al acceso
            </Link>
          </>
        ) : (
          <form onSubmit={submit}>
            <h3 style={{ textAlign: "center", marginBottom: "0.5rem" }}>
              Nueva contraseña
            </h3>
            <p className="muted small" style={{ textAlign: "center", marginBottom: "1rem" }}>
              Elige una contraseña nueva para tu cuenta.
            </p>
            {error && <div className="alert alert-error">{error}</div>}
            <label>
              Nueva contraseña
              <input
                type="password"
                required
                autoFocus
                minLength={4}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label>
              Repetir contraseña
              <input
                type="password"
                required
                minLength={4}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </label>
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading}
            >
              {loading ? "Guardando…" : "Cambiar contraseña"}
            </button>
            <p className="login-footer-link" style={{ marginTop: "1rem", textAlign: "center" }}>
              <Link to="/acceso">← Volver al acceso</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
