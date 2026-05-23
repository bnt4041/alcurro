import { Link, Outlet } from "react-router-dom";
import BrandLogo from "./BrandLogo";

export default function MarketingLayout() {
  return (
    <div className="marketing">
      <header className="marketing-header">
        <Link to="/" className="marketing-brand">
          <BrandLogo variant="light" compact />
        </Link>
        <nav className="marketing-nav">
          <a href="/#tarifas">Tarifas</a>
          <Link to="/registro">Alta</Link>
          <Link to="/acceso-cliente">Acceso cliente</Link>
          <Link to="/admin/login" className="marketing-nav-admin">
            Admin
          </Link>
        </nav>
      </header>
      <Outlet />
      <footer className="marketing-footer">
        <p>
          © {new Date().getFullYear()} alcurro — HRM que se gestiona por WhatsApp
        </p>
      </footer>
    </div>
  );
}
