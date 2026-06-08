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
      {/* HERO */}
      <section className="landing-hero">
        <div className="landing-container landing-hero__grid">
          <div>
            <BrandLogo variant="light" showTagline className="landing-hero__logo" />
            <h1 className="landing-display">
              Tu equipo ficha por{" "}
              <span className="landing-gradient-text">WhatsApp</span>.
              <br />Tú lo controlas todo.
            </h1>
            <p className="landing-hero__lead">
              Fichajes, vacaciones, permisos e incidencias gestionados desde el chat que
              tu equipo ya tiene abierto. Sin apps extra, sin formación, sin excusas.
            </p>
            <div className="landing-hero__cta-group">
              <Link
                to="/registro"
                className="landing-hero__cta landing-rainbow-crest landing-rainbow-shadow"
              >
                Solicitar acceso
                <Icon name="arrow_forward" />
              </Link>
              <a href="#funciones" className="landing-hero__secondary-cta">
                Ver cómo funciona
                <Icon name="expand_more" />
              </a>
            </div>
            <p className="landing-hero__note">
              Configuración en 10 minutos · Sin instalaciones · Soporte incluido
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

      {/* SOCIAL PROOF */}
      <section className="landing-proof">
        <div className="landing-container landing-proof__inner">
          <span className="landing-proof__label">Lo que cambia con alcurro</span>
          <div className="landing-proof__stats">
            <div className="landing-proof__stat">
              <strong>60×</strong>
              <span>más rápido que fichar con una app</span>
            </div>
            <div className="landing-proof__stat">
              <strong>0</strong>
              <span>descargas necesarias en los móviles</span>
            </div>
            <div className="landing-proof__stat">
              <strong>100%</strong>
              <span>válido legalmente en España</span>
            </div>
          </div>
        </div>
      </section>

      {/* COMPARATIVA */}
      <section className="landing-compare">
        <div className="landing-container">
          <div className="landing-section-intro">
            <h2 className="landing-headline">El fichaje que nadie odia</h2>
            <p>
              Si fichar es un engorro, los empleados lo olvidan. Con alcurro lo hacen
              en segundos, desde el mismo sitio donde ya hablan contigo.
            </p>
          </div>
          <div className="landing-compare__grid">
            <div className="landing-glass landing-compare__old">
              <span className="landing-compare__label">Lo habitual</span>
              <h3>
                <Icon name="apps" />
                App de fichaje clásica
              </h3>
              <ol className="landing-compare__steps landing-compare__steps--long">
                <li>Buscar, descargar e instalar la app</li>
                <li>Crear usuario y recordar contraseña</li>
                <li>Abrir la app y esperar a que cargue</li>
                <li>Localizar el botón de «Fichar entrada»</li>
                <li>Aceptar permisos de ubicación</li>
              </ol>
              <div className="landing-compare__time landing-compare__time--slow">
                <Icon name="schedule" />
                ~3 minutos cada vez
              </div>
            </div>

            <div className="landing-compare__vs" aria-hidden>VS</div>

            <div className="landing-rainbow-border landing-rainbow-border--accent landing-compare__new">
              <span className="landing-compare__badge">Con alcurro</span>
              <h3>
                <Icon name="check_circle" />
                Un mensaje y listo
              </h3>
              <div className="landing-compare__hero-step">
                <strong>El empleado escribe «ficho»</strong>
                <span>La IA lo entiende y registra</span>
                <div className="landing-compare__wa-mini">
                  <Icon name="chat" />
                  «Ficho» → ✅ Entrada 08:03
                </div>
              </div>
              <div className="landing-compare__time landing-compare__time--fast">
                <Icon name="bolt" />
                ~3 segundos
              </div>
            </div>
          </div>
          <p className="landing-compare__verdict">
            <strong>El hábito ya existe</strong> — tu equipo ya usa WhatsApp. Solo tienes
            que aprovechar eso.
          </p>
        </div>
      </section>

      {/* FEATURES BENTO */}
      <section id="funciones" className="landing-bento">
        <div className="landing-container">
          <div className="landing-section-intro" style={{ textAlign: "center" }}>
            <h2 className="landing-headline">Todo lo que necesitas, conectado</h2>
            <p>Fichajes, permisos, incidencias y documentos en una sola plataforma.
              Sin integraciones raras ni consultores.</p>
          </div>
          <div className="landing-bento__grid">
            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <div className="landing-bento__head">
                <div>
                  <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                    Control horario legal
                  </h3>
                  <p style={{ color: "var(--lp-muted)", margin: 0 }}>
                    Cumple con el registro obligatorio del RDL 8/2019. Inmutable,
                    exportable y con firma electrónica.
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
                <span className="landing-bento__badge-ia">IA PRIVADA</span>
                <h3 className="landing-headline" style={{ fontSize: "1.25rem", margin: 0 }}>
                  Entiende lenguaje natural
                </h3>
              </div>
              <p style={{ color: "var(--lp-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
                Nadie aprende nada nuevo. Escribe como siempre y alcurro lo interpreta:
                fichajes, vacaciones, permisos, incidencias. Sin comandos, sin apps,
                con IA que no comparte tus datos con nadie.
              </p>
              <div className="landing-bento__chat">
                <div className="landing-wa-bubble-user" style={{ alignSelf: "flex-end" }}>
                  Me pillo vacaciones del 5 al 12 de mayo
                </div>
                <div className="landing-wa-bubble-bot" style={{ borderLeft: "4px solid var(--lp-accent)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "var(--lp-accent)", fontWeight: 700, fontSize: "0.875rem" }}>
                    <Icon name="smart_toy" />
                    alcurro
                  </div>
                  Solicitud creada: 6 días laborables del 5 al 12 de mayo 🌴
                </div>
              </div>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                Vacaciones y permisos
              </h3>
              <p style={{ color: "var(--lp-muted)" }}>
                El responsable aprueba o rechaza desde WhatsApp. Sin email, sin reuniones.
              </p>
              <div className="landing-bento__approval">
                <div className="landing-approval-row">
                  <div className="landing-approval-avatar landing-approval-avatar--user">
                    <Icon name="person" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <strong>Laura García</strong><br />
                    <span style={{ opacity: 0.6 }}>Solicita 3 días de permiso</span>
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
                    <strong>Responsable</strong><br />
                    <span style={{ opacity: 0.6 }}>«Aprobado» · vía WhatsApp</span>
                  </div>
                  <span className="landing-pill landing-pill--ok">APROBADO</span>
                </div>
              </div>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                Turnos complejos
              </h3>
              <p style={{ color: "var(--lp-muted)" }}>
                Rotativos, nocturnos, partidos. Sin hojas de cálculo.
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
              <p style={{ marginTop: "1rem", padding: "0.5rem", fontSize: "0.625rem", borderLeft: "4px solid var(--lp-accent)", background: "#fff", borderRadius: "0.25rem" }}>
                <Icon name="info" /> Cambio detectado el jueves — turno nocturno.
              </p>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                Firma electrónica
              </h3>
              <p style={{ color: "var(--lp-muted)" }}>
                Contratos, acuerdos y documentos firmados desde el móvil en segundos.
                Certificado con plena validez legal. Sin papel, sin desplazamientos.
              </p>
              <div className="landing-bento__doc-preview">
                <div className="landing-bento__doc-row">
                  <span className="material-symbols-outlined" style={{ color: "var(--lp-navy)", fontSize: "1.25rem" }}>description</span>
                  <span style={{ flex: 1, fontSize: "0.8125rem" }}>Contrato jornada parcial · Ana Pérez</span>
                  <span className="landing-pill landing-pill--ok" style={{ fontSize: "0.625rem" }}>FIRMADO</span>
                </div>
                <div className="landing-bento__doc-row">
                  <span className="material-symbols-outlined" style={{ color: "var(--lp-navy)", fontSize: "1.25rem" }}>description</span>
                  <span style={{ flex: 1, fontSize: "0.8125rem" }}>Anexo horario verano · Carlos Ruiz</span>
                  <span className="landing-pill landing-pill--pending" style={{ fontSize: "0.625rem" }}>PENDIENTE</span>
                </div>
                <div className="landing-bento__doc-row">
                  <span className="material-symbols-outlined" style={{ color: "var(--lp-navy)", fontSize: "1.25rem" }}>description</span>
                  <span style={{ flex: 1, fontSize: "0.8125rem" }}>Nómina febrero · Laura García</span>
                  <span className="landing-pill landing-pill--ok" style={{ fontSize: "0.625rem" }}>FIRMADO</span>
                </div>
              </div>
            </article>

            <article className="landing-glass landing-bento__card landing-bento__card--wide">
              <h3 className="landing-headline" style={{ fontSize: "1.25rem" }}>
                Gestor documental y nóminas
              </h3>
              <p style={{ color: "var(--lp-muted)" }}>
                Centraliza contratos, bajas, certificados y nóminas. Envía la nómina
                mensual con un clic: el empleado la recibe por WhatsApp, la firma
                y confirma la recepción automáticamente.
              </p>
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
                {[
                  { icon: "receipt_long", label: "Nóminas" },
                  { icon: "folder_shared", label: "Contratos" },
                  { icon: "sick", label: "Bajas IT" },
                  { icon: "workspace_premium", label: "Certificados" },
                ].map(({ icon, label }) => (
                  <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.35rem", background: "var(--lp-outline)", borderRadius: "8px", padding: "0.35rem 0.65rem", fontSize: "0.75rem", fontWeight: 600, color: "var(--lp-navy)" }}>
                    <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>{icon}</span>
                    {label}
                  </div>
                ))}
              </div>
              <p style={{ marginTop: "1rem", padding: "0.5rem 0.75rem", fontSize: "0.75rem", background: "rgba(37,211,102,0.08)", borderRadius: "8px", color: "var(--lp-navy)", borderLeft: "3px solid var(--lp-accent)" }}>
                <strong>+</strong> Acceso del empleado a su historial completo de documentos, siempre disponible.
              </p>
            </article>
          </div>
        </div>
      </section>

      {/* POR QUÉ ALCURRO */}
      <section className="landing-why">
        <div className="landing-container">
          <div className="landing-section-intro" style={{ textAlign: "center" }}>
            <h2 className="landing-headline">¿Por qué alcurro y no otra cosa?</h2>
            <p>Nos lo preguntan mucho. Aquí la respuesta honesta.</p>
          </div>
          <div className="landing-why__grid">
            <div className="landing-why__card">
              <div className="landing-why__icon">
                <Icon name="lock" />
              </div>
              <h3>IA privada, datos que no salen</h3>
              <p>
                Conversaciones, documentos y datos de empleados permanecen dentro
                de tu empresa. La IA procesa todo internamente, sin enviar nada
                a terceros. Cumplimiento RGPD sin esfuerzo.
              </p>
            </div>
            <div className="landing-why__card">
              <div className="landing-why__icon">
                <Icon name="bolt" />
              </div>
              <h3>Sin adopción forzada</h3>
              <p>
                WhatsApp ya lo tienen instalado. No hay que convencer a nadie de
                descargarse otra app ni pedir ayuda al equipo de IT.
              </p>
            </div>
            <div className="landing-why__card">
              <div className="landing-why__icon">
                <Icon name="gavel" />
              </div>
              <h3>Cumplimiento legal de serie</h3>
              <p>
                Registro horario inmutable conforme al RDL 8/2019. Firma electrónica
                de documentos, exportación a Excel y PDF listos para inspección.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* TARIFAS */}
      <section id="tarifas" className="marketing-pricing">
        <div className="marketing-section-inner">
          <h2>Tarifas sin sorpresas</h2>
          <p className="marketing-section-lead">
            Paga por lo que usas. Cambia de plan cuando quieras.
            Anual con descuento o mes a mes sin permanencia.
          </p>

          {loading && (
            <p style={{ textAlign: "center", color: "var(--lp-muted)" }}>Cargando tarifas…</p>
          )}
          {!loading && plans.length === 0 && (
            <p style={{ textAlign: "center", color: "var(--lp-muted)" }}>
              No hay tarifas publicadas.{" "}
              <Link to="/registro">Regístrate</Link> para conocer los precios.
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
                    /mes · ({formatMoney(plan.annual_price_per_month_cents * 12, plan.currency)}/año)
                  </p>
                  <Link to={`/registro?plan=${plan.id}`} className="btn btn-primary">
                    Empezar con {plan.name}
                  </Link>
                </article>
              ))}
            </div>
          )}

          <p className="landing-plans__note">
            ¿Necesitas algo a medida? <Link to="/contacto">Cuéntanos</Link> y lo vemos.
          </p>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="landing-final-cta">
        <div className="landing-container">
          <div className="landing-rainbow-border landing-rainbow-border--accent landing-final-cta__box">
            <BrandLogo variant="light" className="landing-hero__logo landing-hero__logo--center" />
            <h2 className="landing-headline landing-display" style={{ fontSize: "clamp(1.75rem, 4vw, 2.5rem)", marginTop: 0 }}>
              Tu equipo te lo agradecerá.
            </h2>
            <p>
              Menos fricción, menos olvidos, más tiempo para lo que importa.
              Configura alcurro en 10 minutos y compruébalo tú mismo.
            </p>
            <div className="landing-final-cta__actions">
              <Link
                to="/registro"
                className="landing-hero__cta landing-rainbow-crest landing-rainbow-shadow"
              >
                Solicitar acceso
              </Link>
              <Link to="/contacto" className="landing-final-cta__secondary">
                Hablar con el equipo
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
