import { NavLink, Outlet } from "react-router-dom";
import BrandLogo from "./BrandLogo";
import { useAuth } from "../context/AuthContext";

const nav = [
  { to: "/admin", label: "Cuentas", end: true },
  { to: "/admin/usuarios", label: "Usuarios", end: false },
  { to: "/admin/tarifas", label: "Tarifas", end: false },
  { to: "/admin/descuentos", label: "Descuentos", end: false },
  { to: "/admin/cobros", label: "Cobros Stripe", end: false },
  { to: "/admin/whatsapp", label: "WhatsApp", end: false },
  { to: "/admin/mail", label: "Correo", end: false },
  { to: "/admin/ia", label: "IA", end: false },
];

export default function PlatformLayout() {
  const { platformUser, logout } = useAuth();
  if (!platformUser) return null;

  return (
    <div className="layout layout--light">
      <aside className="sidebar sidebar--light">
        <div className="brand">
          <BrandLogo variant="light" compact />
        </div>
        <div className="user-chip">
          <span className="user-name">{platformUser.full_name}</span>
          <span className="badge">Administrador</span>
        </div>
        <nav>
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
        <Outlet />
      </main>
    </div>
  );
}
