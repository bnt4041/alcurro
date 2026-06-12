import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { useAuth } from "../context/AuthContext";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import { getTenantHomePath } from "../lib/auth-routes";

export default function LoginPage() {
  const navigate = useNavigate();
  const { user, platformUser, loginUnified, loading: authLoading } = useAuth();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    applyAlcurroDefaults();
  }, []);

  if (!authLoading && platformUser) return <Navigate to="/admin" replace />;
  if (!authLoading && user) return <Navigate to={getTenantHomePath(user)} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!loginId.trim() || !password) {
      setError("Indica usuario y contraseña");
      return;
    }
    setLoading(true);
    try {
      const result = await loginUnified(loginId.trim(), password);
      if (result.scope === "platform") {
        navigate("/admin", { replace: true });
      } else if (result.user) {
        navigate(getTenantHomePath(result.user), { replace: true });
      }
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
          Mismo acceso para todos. Tras entrar irás a tu portal según tu perfil.
        </p>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Usuario
          <input
            required
            autoComplete="username"
            placeholder="ej. demo/ADM001 o tu email"
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
          />
          <span className="muted small">
            Organización: <code>cuenta/usuario</code> o <code>usuario@cuenta</code> ·
            Plataforma: tu email
          </span>
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
          <Link to="/registro">Alta de cliente</Link>
          <br />
          <Link to="/recuperar">¿Olvidaste tu contraseña?</Link>
        </p>
      </form>
    </div>
  );
}
