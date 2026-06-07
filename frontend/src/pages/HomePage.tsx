import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { publicApi, type PublicPricingPlan } from "../api/public";
import { applyAlcurroDefaults } from "../hooks/useBranding";
import { formatMoney } from "../lib/money";

function Icon({ name }: { name: string }) {
  return <span className="material-symbols-outlined">{name}</span>;
}

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
      <section className="landing-hero">
        <div className="landing-container landing-hero__grid">
          <div>
            <BrandLogo variant="light" showTagline className="landing-hero__logo" />
            <h1 className="landing-display">
              RRHH a la velocidad de un{" "}
              <span className="landing-gradient-text">WhatsApp</span>
            </h1>
            <p className="landing-hero__lead">
              Gestiona fichajes, vacaciones y turnos complejos desde el chat que ya
              usas. Sin descargas en cada móvil, sin complicaciones.
            </p>
            <Link
              to="/registro"
              className="landing-hero__cta landing-rainbow-crest landing-rainbow-shadow"
            >
              Empezar ahora
              <Icon name="arrow_forward" />
            </Link>
            <p className="landing-hero__note">
              Configura tu cuenta en minutos. Prueba el flujo completo.
            </p>
          </div>

          <div className="landing-phone-wrap">
            <div className="landing-phone-glow" aria-hidden />
            <div className="landing-phone">
              <div className="landing-phone__notch" aria-hidden />
              <div className="landing-phone__screen">
                <video
                  className="landing-phone__video"
                  autoPlay
                  muted
                  loop
                  playsInline
                >
                  <source src="/Video_comienza_con_el_chat_vac.mp4" type="video/mp4" />
                </video>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-compare">
        <div className="landing-container">
          <div className="landing-section-intro">
            <h2 className="landing-headline">Fichar por alcurro es más práctico</h2>
            <p>
              Sin apps nuevas ni contraseñas: el fichaje ocurre donde ya están tus
              empleados cada día.
            </p>
          </div>
          <div className="landing-compare__grid">
            <div className="landing-glass landing-compare__old">
              <span className="landing-compare__label">Lo habitual</span>
              <h3>
                <Icon name="apps" />
                App de fichaje
              </h3>
              <ol className="landing-compare__steps landing-compare__steps--long">
                <li>Buscar y descargar la app</li>
                <li>Crear usuario y recordar contraseña</li>
                <li>Abrir la app y esperar a que cargue</li>
                <li>Navegar hasta «Fichar entrada»</li>
                <li>Confirmar ubicación o permisos</li>
              </ol>
              <div className="landing-compare__time landing-compare__time--slow">
                <Icon name="schedule" />
                ~3 minutos por fichaje
              </div>
            </div>

            <div className="landing-compare__vs" aria-hidden>
              VS
            </div>

            <div className="landing-rainbow-border landing-rainbow-border--accent landing-compare__new">
              <span className="landing-compare__badge">Más práctico</span>
              <h3>
                <Icon name="check_circle" />
                Fichar con alcurro
              </h3>
              <div className="landing-compare__hero-step">
                <strong>Un mensaje y listo</strong>
                <span>El empleado no cambia de hábito</span>
                <div className="landing-compare__wa-mini">
                  <Icon name="chat" />
                  «Ficho»
                </div>
              </div>
              <div className="landing-compare__time landing-compare__time--fast">
                <Icon name="bolt" />
                ~3 segundos
              </div>
            </div>
          </div>
          <p className="landing-compare__verdict">
            <strong>60 veces más rápido</strong> que una app de fichaje clásica — y sin
            olvidos al final del mes.
          </p>
        </div>
      </section>

      <section id="funciones" className="landing-bento">
        <div className="landing-container">
          <h2 className="landing-headline" style={{ textAlign: "center", marginBottom: "4rem" }}>
            Potencia real en un entorno familiar
          </h2>
          <div className="landing-bento__grid">
            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <div className="landing-bento__head">
                <div>
                  <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                    Fichajes
                  </h3>
                  <p style={{ color: "var(--lp-muted)", margin: 0 }}>
                    Control horario total con validez legal.
                  </p>
                </div>
                <span className="landing-bento__tag">
                  <Icon name="location_on" />
                  GEOLOCALIZACIÓN
                </span>
              </div>
              <div className="landing-bento__map-preview">
                <div className="landing-bento__map-overlay">
                  <Icon name="history" />
                  10:02 — Oficina central
                </div>
              </div>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide landing-bento__ia">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <span className="landing-bento__badge-ia">IA LOCAL</span>
                <h3 className="landing-headline" style={{ fontSize: "1.25rem", margin: 0 }}>
                  IA privada
                </h3>
              </div>
              <p style={{ color: "var(--lp-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
                Entiende el lenguaje natural. Procesado en tu infraestructura.
              </p>
              <div className="landing-bento__chat">
                <div className="landing-wa-bubble-user" style={{ alignSelf: "flex-end" }}>
                  Me voy de vacaciones del 5 al 12 de mayo
                </div>
                <div
                  className="landing-wa-bubble-bot"
                  style={{ borderLeft: "4px solid var(--lp-accent)" }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      color: "var(--lp-accent)",
                      fontWeight: 700,
                      fontSize: "0.875rem",
                    }}
                  >
                    <Icon name="smart_toy" />
                    Procesando…
                  </div>
                  Solicitud creada: 7 días de vacaciones detectados.
                </div>
              </div>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                Vacaciones
              </h3>
              <p style={{ color: "var(--lp-muted)" }}>Flujos de aprobación automáticos.</p>
              <div className="landing-bento__approval">
                <div className="landing-approval-row">
                  <div className="landing-approval-avatar landing-approval-avatar--user">
                    <Icon name="person" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong>Juan Pérez</strong>
                    <br />
                    <span style={{ opacity: 0.6 }}>Solicitó 3 días</span>
                  </div>
                  <span className="landing-pill landing-pill--pending">PENDIENTE</span>
                </div>
                <div style={{ textAlign: "center", color: "var(--lp-outline)" }}>
                  <Icon name="arrow_downward" />
                </div>
                <div className="landing-approval-row landing-approval-row--ok">
                  <div className="landing-approval-avatar landing-approval-avatar--mgr">
                    <Icon name="verified_user" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong>Responsable</strong>
                    <br />
                    <span style={{ opacity: 0.6 }}>Aprobado vía WhatsApp</span>
                  </div>
                  <span className="landing-pill landing-pill--ok">OK</span>
                </div>
              </div>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                Turnos complejos
              </h3>
              <p style={{ color: "var(--lp-muted)" }}>
                Rotativos, nocturnos o partidos sin líos.
              </p>
              <div className="landing-shift-scroll">
                <div className="landing-shift-grid">
                <span className="is-light">L</span>
                <span className="is-work">M</span>
                <span className="is-work">X</span>
                <span className="is-alt">J</span>
                <span className="is-light">V</span>
                <span className="is-off">S</span>
                <span className="is-off">D</span>
                </div>
              </div>
              <p
                style={{
                  marginTop: "1rem",
                  padding: "0.5rem",
                  fontSize: "0.625rem",
                  borderLeft: "4px solid var(--lp-accent)",
                  background: "#fff",
                  borderRadius: "0.25rem",
                }}
              >
                <Icon name="info" /> Cambio de turno detectado el jueves (nocturno).
              </p>
            </article>
          </div>
        </div>
      </section>

      <section id="tarifas" className="marketing-pricing">
        <div className="marketing-section-inner">
          <h2>Tarifas</h2>
          <p className="marketing-section-lead">
            Los mismos planes que configuras en el panel de administración. Contrato
            mensual o anual.
          </p>

          {loading && (
            <p style={{ textAlign: "center", color: "var(--lp-muted)" }}>
              Cargando tarifas…
            </p>
          )}
          {!loading && plans.length === 0 && (
            <p style={{ textAlign: "center", color: "var(--lp-muted)" }}>
              No hay tarifas activas. Actívalas en Admin → Tarifas o{" "}
              <Link to="/registro">regístrate</Link> para más información.
            </p>
          )}

          {!loading && plans.length > 0 && (
            <div className="pricing-cards">
              {plans.map((plan) => (
                <article key={plan.id} className="pricing-card">
                  <h3>{plan.name}</h3>
                  {plan.description && (
                    <p className="muted small">{plan.description}</p>
                  )}
                  <p className="pricing-card__price">
                    {formatMoney(plan.monthly_price_cents, plan.currency)}
                    <span className="muted"> / mes</span>
                  </p>
                  <p className="pricing-card__users">
                    Hasta <strong>{plan.max_active_users}</strong> usuarios activos
                  </p>
                  <p className="muted small">
                    Anual: {formatMoney(plan.annual_price_per_month_cents, plan.currency)}
                    /mes (
                    {formatMoney(plan.annual_price_per_month_cents * 12, plan.currency)}
                    /año facturados)
                  </p>
                  <Link
                    to={`/registro?plan=${plan.id}`}
                    className="btn btn-primary"
                  >
                    Empezar con {plan.name}
                  </Link>
                </article>
              ))}
            </div>
          )}

          <p className="landing-plans__note">
            Precios y límites definidos en tu catálogo de tarifas (orden y estado
            activo).
          </p>
        </div>
      </section>

      <section className="landing-final-cta">
        <div className="landing-container">
          <div className="landing-rainbow-border landing-rainbow-border--accent landing-final-cta__box">
            <BrandLogo variant="light" className="landing-hero__logo landing-hero__logo--center" />
            <h2
              className="landing-headline landing-display"
              style={{ fontSize: "clamp(1.75rem, 4vw, 2.5rem)", marginTop: 0 }}
            >
              ¿Listo para el cambio?
            </h2>
            <p>
              Tus empleados te lo agradecerán. Menos fricción significa más
              productividad y un mejor ambiente laboral.
            </p>
            <div className="landing-final-cta__actions">
              <Link
                to="/registro"
                className="landing-hero__cta landing-rainbow-crest landing-rainbow-shadow"
              >
                Empezar ahora
              </Link>
              <Link to="/acceso" className="landing-final-cta__secondary">
                Ya tengo cuenta
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
