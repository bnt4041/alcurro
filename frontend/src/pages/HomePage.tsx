import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { publicApi, type PublicPricingPlan } from "../api/public";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import { formatMoney } from "../lib/money";

export default function HomePage() {
  const [plans, setPlans] = useState<PublicPricingPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    applyAlcurroDefaults();
    publicApi
      .getPlans()
      .then(setPlans)
      .catch(() => setPlans([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <section className="marketing-hero">
        <div className="marketing-hero__inner">
          <p className="marketing-eyebrow">RRHH por WhatsApp</p>
          <h1>
            Gestiona fichajes, vacaciones y turnos{" "}
            <span className="marketing-highlight">sin complicarte</span>
          </h1>
          <p className="marketing-lead">
            alcurro conecta tu equipo por WhatsApp con un panel web claro. Ideal
            para pymes que quieren control horario y ausencias sin instalar apps
            en cada móvil.
          </p>
          <div className="marketing-hero__actions">
            <Link to="/registro" className="btn btn-primary btn-lg">
              Empezar ahora
            </Link>
            <a href="#tarifas" className="btn btn-secondary btn-lg">
              Ver tarifas
            </a>
          </div>
        </div>
      </section>

      <section className="marketing-features">
        <div className="marketing-section-inner">
          <h2>Todo lo que necesitas</h2>
          <div className="marketing-grid">
            <article className="marketing-card">
              <h3>Fichajes</h3>
              <p>Entrada y salida por WhatsApp o panel. Historial y exportación.</p>
            </article>
            <article className="marketing-card">
              <h3>Vacaciones</h3>
              <p>Solicitudes, aprobaciones y calendario de equipo.</p>
            </article>
            <article className="marketing-card">
              <h3>Turnos</h3>
              <p>Patrones rotativos y asignación por centro o departamento.</p>
            </article>
            <article className="marketing-card">
              <h3>Multi-empresa</h3>
              <p>Varias empresas en una cuenta con facturación por empresa.</p>
            </article>
          </div>
        </div>
      </section>

      <section id="tarifas" className="marketing-pricing">
        <div className="marketing-section-inner">
          <h2>Tarifas activas</h2>
          <p className="marketing-section-lead">
            Precios transparentes. Contrato mensual o anual con mejor precio.
          </p>
          {loading && <p className="muted">Cargando tarifas…</p>}
          {!loading && plans.length === 0 && (
            <p className="muted">No hay tarifas publicadas en este momento.</p>
          )}
          <div className="pricing-cards">
            {plans.map((plan) => (
              <article key={plan.id} className="pricing-card">
                <h3>{plan.name}</h3>
                {plan.description && (
                  <p className="pricing-card__desc">{plan.description}</p>
                )}
                <p className="pricing-card__price">
                  <strong>{formatMoney(plan.monthly_price_cents, plan.currency)}</strong>
                  <span className="muted"> / mes</span>
                </p>
                <p className="pricing-card__annual muted small">
                  o {formatMoney(plan.annual_price_per_month_cents, plan.currency)}
                  /mes con contrato anual
                </p>
                <p className="pricing-card__users">
                  Hasta {plan.max_active_users} usuarios activos
                </p>
                <Link
                  to={`/registro?plan=${plan.id}`}
                  className="btn btn-primary btn-block"
                >
                  Contratar
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="marketing-cta">
        <div className="marketing-section-inner marketing-cta__inner">
          <h2>¿Listo para probarlo?</h2>
          <p>Crea tu cuenta en minutos y accede con tu código de cuenta.</p>
          <Link to="/registro" className="btn btn-primary btn-lg">
            Darse de alta
          </Link>
        </div>
      </section>
    </>
  );
}
