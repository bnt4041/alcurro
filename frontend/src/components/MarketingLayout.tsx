import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import BrandLogo from "./BrandLogo";
import { useHideOnScroll } from "../hooks/useHideOnScroll";
import "../styles/landing.css";

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
            <span className="landing-nav__menu-icon" aria-hidden />
            <span className="visually-hidden">
              {mobileNavOpen ? "Cerrar menú" : "Abrir menú"}
            </span>
          </button>
          <nav className="landing-nav__links" aria-label="Secciones">
            <a href="/#funciones" className={isHome ? "is-active" : ""}>
              Funciones
            </a>
            <a href="/#tarifas">Tarifas</a>
          </nav>
          <nav
            id="landing-mobile-nav"
            className={`landing-nav__mobile${mobileNavOpen ? " is-open" : ""}`}
            aria-label="Menú móvil"
          >
            <a
              href="/#funciones"
              className={isHome ? "is-active" : ""}
              onClick={() => setMobileNavOpen(false)}
            >
              Funciones
            </a>
            <a href="/#tarifas" onClick={() => setMobileNavOpen(false)}>
              Tarifas
            </a>
            <Link to="/acceso" onClick={() => setMobileNavOpen(false)}>
              Acceder
            </Link>
            <Link
              to="/registro"
              className="landing-nav__cta landing-rainbow-crest"
              onClick={() => setMobileNavOpen(false)}
            >
              Empezar
            </Link>
          </nav>
          <div className="landing-nav__actions">
            <Link to="/acceso" className="landing-nav__login">
              Acceder
            </Link>
            <Link
              to="/registro"
              className="landing-nav__cta landing-rainbow-crest landing-rainbow-shadow"
            >
              Empezar
            </Link>
          </div>
        </div>
      </header>

      <main className="landing-main">
        <Outlet />
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer__inner">
          <div>
            <div className="landing-footer__logo">
              <BrandLogo variant="light" showTagline />
            </div>
            <p className="landing-footer__copy">
              © {new Date().getFullYear()} alcurro. RRHH sin fricción por WhatsApp.
            </p>
          </div>
          <div className="landing-footer__links">
            <a href="/#tarifas">Tarifas</a>
            <Link to="/registro">Alta</Link>
            <Link to="/acceso">Acceder</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
