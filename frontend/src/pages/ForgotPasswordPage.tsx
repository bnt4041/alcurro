import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { applyAlcurroDefaults } from "../hooks/useBranding";

export default function ForgotPasswordPage() {
  const [emailOrPhone, setEmailOrPhone] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    applyAlcurroDefaults();
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const val = emailOrPhone.trim();
    if (!val) {
      setError("Indica tu email o teléfono");
      return;
    }
    setLoading(true);
    try {
      const isEmail = val.includes("@");
      const body: Record<string, string> = {};
      if (isEmail) body.email = val;
      else body.phone = val;
      if (tenantSlug.trim()) body.tenant_slug = tenantSlug.trim().toLowerCase();

      await fetch("/api/public/forgot-password", {
        method: "POST",
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
      });
      setSent(true);
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

        {sent ? (
          <>
            <div className="alert alert-success">
              <strong>Revisa tu email o WhatsApp.</strong>
              <p className="muted small" style={{ marginTop: "0.5rem" }}>
                Si los datos corresponden a un usuario activo, recibirás un enlace
                para restablecer tu contraseña. El enlace caduca en 15 minutos.
              </p>
            </div>
            <p className="login-footer-link" style={{ marginTop: "1rem" }}>
              <Link to="/acceso">← Volver al acceso</Link>
            </p>
          </>
        ) : (
          <form onSubmit={submit}>
            <h3 style={{ textAlign: "center", marginBottom: "0.5rem" }}>
              Recuperar contraseña
            </h3>
            <p className="muted small" style={{ textAlign: "center", marginBottom: "1rem" }}>
              Te enviaremos un enlace por email o WhatsApp.
            </p>
            {error && <div className="alert alert-error">{error}</div>}
            <label>
              Email o teléfono
              <input
                required
                autoFocus
                placeholder="tu@email.com o +34600000000"
                value={emailOrPhone}
                onChange={(e) => setEmailOrPhone(e.target.value)}
              />
            </label>
            <label>
              Código de cuenta{" "}
              <span className="muted small">(opcional, acelera la búsqueda)</span>
              <input
                placeholder="ej. demo"
                value={tenantSlug}
                onChange={(e) => setTenantSlug(e.target.value)}
              />
            </label>
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading}
            >
              {loading ? "Enviando…" : "Enviar enlace"}
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
