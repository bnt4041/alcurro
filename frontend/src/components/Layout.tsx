import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import BrandLogo from "./BrandLogo";
import OrgSelector from "./OrgSelector";
import { useAuth } from "../context/AuthContext";
import { applyBranding, getStoredTenantSlug } from "../hooks/useBranding";
import { canModule, ROLE_LABELS } from "../lib/permissions";

const nav = [
  { to: "/app", label: "Inicio", always: true as const },
  { to: "/app/organizacion", label: "Organización", module: "companies" as const },
  { to: "/app/empleados", label: "Empleados", module: "employees" as const },
  { to: "/app/fichajes", label: "Fichajes", module: "clock_ins" as const },
  { to: "/app/vacaciones", label: "Vacaciones", module: "leave" as const },
  { to: "/app/turnos", label: "Turnos", module: "shifts" as const },
  { to: "/app/documentos", label: "Documentos", module: "documents" as const },
  { to: "/app/grupos", label: "Grupos", module: "groups" as const },
  { to: "/app/cuenta", label: "Cuenta", module: "tenant" as const, write: true },
  { to: "/app/configuracion", label: "Sistema", module: "settings" as const, write: true },
];

export default function Layout() {
  const { user, logout } = useAuth();

  useEffect(() => {
    if (!user) return;
    api
      .get<{
        slug: string;
        name: string;
        primary_color: string;
        secondary_color: string;
        accent_color: string;
        logo_url: string | null;
      }>(`/tenants/public/${getStoredTenantSlug()}/branding`)
      .then(applyBranding)
      .catch(() => {});
  }, [user]);

  if (!user) return null;

  const displayRole = ROLE_LABELS[user.user_type ?? user.role] ?? user.role;

  return (
    <div className="layout layout--light">
      <aside className="sidebar sidebar--light">
        <div className="brand">
          <BrandLogo variant="light" compact />
          <p className="tenant-label">{user.tenant_name}</p>
        </div>
        <div className="user-chip">
          <span className="user-name">{user.full_name}</span>
          <span className="badge">{displayRole}</span>
        </div>
        <OrgSelector />
        <nav>
          {nav
            .filter((item) => {
              if ("always" in item && item.always) return true;
              const coarse = "write" in item && item.write ? "write" : "read";
              return item.module
                ? canModule(user.permissions, coarse, item.module)
                : false;
            })
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/app"}
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
        {user.role === "labor_inspector" && (
          <div className="alert alert-info">
            Modo solo lectura — Inspector de Trabajo
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
