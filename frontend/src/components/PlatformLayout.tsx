import { NavLink, Outlet } from "react-router-dom";
import { useResponsiveSidebar } from "../hooks/useResponsiveSidebar";
import BrandLogo from "./BrandLogo";
import { useAuth } from "../context/AuthContext";

const nav = [
  { to: "/admin", label: "Cuentas", end: true },
  { to: "/admin/usuarios", label: "Usuarios", end: false },
  { to: "/admin/tarifas", label: "Tarifas", end: false },
  { to: "/admin/descuentos", label: "Descuentos", end: false },
  { to: "/admin/cobros", label: "Cobros Stripe", end: false },
  { to: "/admin/facturas", label: "Facturas", end: false },
  { to: "/admin/configuracion", label: "Configuración", end: false },
  { to: "/admin/whatsapp", label: "WhatsApp", end: false },
  { to: "/admin/mail", label: "Correo", end: false },
  { to: "/admin/ia", label: "IA", end: false },
  { to: "/admin/politicas", label: "Políticas de uso", end: false },
  { to: "/admin/purgar", label: "Purgar datos", end: false },
];

export default function PlatformLayout() {
  const { platformUser, logout } = useAuth();
  const { open: sidebarOpen, toggle: toggleSidebar, close: closeSidebar } =
    useResponsiveSidebar();
  if (!platformUser) return null;

  return (
    <div
      className={`layout layout--light${sidebarOpen ? " layout--sidebar-open" : ""}`}
    >
      <button
        type="button"
        className="sidebar-backdrop"
        aria-label="Cerrar menú"
        onClick={closeSidebar}
        tabIndex={sidebarOpen ? 0 : -1}
      />
      <aside id="platform-sidebar" className="sidebar sidebar--light">
        <div className="brand">
          <BrandLogo variant="light" compact />
        </div>
        <div className="user-chip">
          <span className="user-name">{platformUser.full_name}</span>
          <span className="badge">Administrador</span>
        </div>
        <nav onClick={closeSidebar}>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button type="button" className="btn btn-logout" onClick={logout}>
          Cerrar sesión
        </button>
      </aside>
      <main className="main">
        <button
          type="button"
          className="sidebar-toggle"
          aria-expanded={sidebarOpen}
          aria-controls="platform-sidebar"
          onClick={toggleSidebar}
        >
          <span className="sidebar-toggle__bars" aria-hidden />
          <span className="sidebar-toggle__label">Menú</span>
        </button>
        <Outlet />
      </main>
    </div>
  );
}
