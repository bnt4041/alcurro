import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { useAuth } from "../context/AuthContext";
import { applyAlcurroDefaults, getStoredTenantSlug } from "../hooks/useBranding";

export default function TenantLoginPage() {
  const { user, login } = useAuth();
  const [tenantSlug, setTenantSlug] = useState(getStoredTenantSlug() || "demo");
  const [username, setUsername] = useState("ADM001");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    applyAlcurroDefaults();
  }, [tenantSlug]);

  if (user) return <Navigate to="/app" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!tenantSlug.trim()) {
      setError("Indica el código de tu cuenta (ej. demo)");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await login(tenantSlug.trim(), username.trim(), password);
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
          Panel de tu organización (según permisos de tu grupo)
        </p>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Cuenta
          <input
            required
            placeholder="ej. demo"
            value={tenantSlug}
            onChange={(e) => setTenantSlug(e.target.value.toLowerCase())}
          />
        </label>
        <label>
          Usuario
          <input
            required
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
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
        <p className="muted small">
          Demo: cuenta <code>demo</code> · <code>ADM001</code> · <code>admin123</code>
        </p>
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Entrando…" : "Iniciar sesión"}
        </button>
        <p className="muted small login-footer-link">
          <Link to="/login">← Administración plataforma</Link>
        </p>
      </form>
    </div>
  );
}
