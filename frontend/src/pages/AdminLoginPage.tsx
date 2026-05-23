import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { useAuth } from "../context/AuthContext";
import { applyAlcurroDefaults } from "../hooks/useBranding";

/** Login administradores de plataforma. */
export default function AdminLoginPage() {
  const { platformUser, loginPlatform } = useAuth();
  const [email, setEmail] = useState("platform@hrm.local");
  const [password, setPassword] = useState("platform123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    applyAlcurroDefaults();
  }, []);

  if (platformUser) return <Navigate to="/admin" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await loginPlatform(email.trim(), password);
    } catch (err) {
      const msg = String(err).replace(/^Error:\s*/i, "");
      setError(msg || "Credenciales inválidas");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <BrandLogo variant="light" showTagline />
        <p className="login-admin-hint muted small">
          Acceso <strong>administradores de la plataforma</strong> alcurro
        </p>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Email
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Entrando…" : "Iniciar sesión"}
        </button>
        <p className="muted small login-footer-link">
          <Link to="/">Volver al inicio</Link>
          {" · "}
          <Link to="/acceso-cliente">Acceso cliente</Link>
        </p>
      </form>
    </div>
  );
}
