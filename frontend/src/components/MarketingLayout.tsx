import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import BrandLogo from "./BrandLogo";
import { useHideOnScroll } from "../hooks/useHideOnScroll";
import "../styles/landing.css";

function CookieBanner() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!localStorage.getItem("cookie_consent")) setVisible(true);
  }, []);
  const accept = () => {
    localStorage.setItem("cookie_consent", "accepted");
    setVisible(false);
  };
  const decline = () => {
    localStorage.setItem("cookie_consent", "declined");
    setVisible(false);
  };
  if (!visible) return null;
  return (
    <div className="cookie-banner" role="dialog" aria-label="Aviso de cookies">
      <div className="cookie-banner__text">
        <strong>Usamos cookies esenciales</strong> para que la plataforma funcione.
        Sin datos de seguimiento ni publicidad.{" "}
        <Link to="/cookies" className="cookie-banner__link">Saber más</Link>
      </div>
      <div className="cookie-banner__actions">
        <button type="button" className="cookie-banner__btn cookie-banner__btn--decline" onClick={decline}>
          Solo esenciales
        </button>
        <button type="button" className="cookie-banner__btn cookie-banner__btn--accept" onClick={accept}>
          Aceptar
        </button>
      </div>
    </div>
  );
}

export default function MarketingLayout() {
  const { pathname } = useLocation();
  const isHome = pathname === "/";
  const { hidden, scrolled } = useHideOnScroll();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.classList.toggle("landing-nav-scroll-lock", mobileNavOpen);
    return () => document.body.classList.remove("landing-nav-scroll-lock");
  }, [mobileNavOpen]);

  return (
    <div className={`landing${mobileNavOpen ? " landing--nav-open" : ""}`}>
      <header
        className={[
          "landing-nav",
          scrolled && "landing-nav--scrolled",
          hidden && "landing-nav--hidden",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <div className="landing-nav__inner">
          <Link to="/" className="landing-nav__logo" aria-label="alcurro — inicio">
            <BrandLogo variant="light" compact />
          </Link>

          <button
            type="button"
            className="landing-nav__menu-btn"
            aria-expanded={mobileNavOpen}
            aria-controls="landing-mobile-nav"
            onClick={() => setMobileNavOpen((v) => !v)}
          >
            <span className={`landing-nav__menu-icon${mobileNavOpen ? " is-open" : ""}`} aria-hidden />
            <span className="visually-hidden">
              {mobileNavOpen ? "Cerrar menú" : "Abrir menú"}
            </span>
          </button>

          <nav className="landing-nav__links" aria-label="Secciones">
            {isHome && <a href="#funciones">Funciones</a>}
            {isHome && <a href="#tarifas">Tarifas</a>}
            {!isHome && <Link to="/#funciones">Funciones</Link>}
            {!isHome && <Link to="/#tarifas">Tarifas</Link>}
            <Link to="/contacto">Contacto</Link>
          </nav>

          <nav
            id="landing-mobile-nav"
            className={`landing-nav__mobile${mobileNavOpen ? " is-open" : ""}`}
            aria-label="Menú móvil"
          >
            <a href="/#funciones" onClick={() => setMobileNavOpen(false)}>Funciones</a>
            <a href="/#tarifas" onClick={() => setMobileNavOpen(false)}>Tarifas</a>
            <Link to="/contacto" onClick={() => setMobileNavOpen(false)}>Contacto</Link>
            <Link to="/acceso" onClick={() => setMobileNavOpen(false)}>Acceder</Link>
            <Link
              to="/registro"
              className="landing-nav__cta landing-rainbow-crest"
              onClick={() => setMobileNavOpen(false)}
            >
              Empezar gratis
            </Link>
          </nav>

          <div className="landing-nav__actions">
            <Link to="/acceso" className="landing-nav__login">Acceder</Link>
            <Link
              to="/registro"
              className="landing-nav__cta landing-rainbow-crest landing-rainbow-shadow"
            >
              Empezar gratis
            </Link>
          </div>
        </div>
      </header>

      <main className="landing-main">
        <Outlet />
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer__inner">
          <div className="landing-footer__brand">
            <div className="landing-footer__logo">
              <BrandLogo variant="light" showTagline />
            </div>
            <p className="landing-footer__copy">
              © {new Date().getFullYear()} alcurro · RRHH sin fricción por WhatsApp
            </p>
          </div>
          <div className="landing-footer__cols">
            <div className="landing-footer__col">
              <p className="landing-footer__col-title">Producto</p>
              <a href="/#funciones">Funciones</a>
              <a href="/#tarifas">Tarifas</a>
              <Link to="/registro">Alta gratuita</Link>
            </div>
            <div className="landing-footer__col">
              <p className="landing-footer__col-title">Cuenta</p>
              <Link to="/acceso">Acceder</Link>
              <Link to="/contacto">Contacto y soporte</Link>
            </div>
            <div className="landing-footer__col">
              <p className="landing-footer__col-title">Legal</p>
              <Link to="/aviso-legal">Aviso legal</Link>
              <Link to="/privacidad">Privacidad</Link>
              <Link to="/cookies">Cookies</Link>
            </div>
          </div>
        </div>
      </footer>

      <CookieBanner />
    </div>
  );
}
