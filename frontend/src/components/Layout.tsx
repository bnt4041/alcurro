import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useResponsiveSidebar } from "../hooks/useResponsiveSidebar";
import { api } from "../api/client";
import BrandLogo from "./BrandLogo";
import NotificationBell from "./NotificationBell";
import OrgSelector from "./OrgSelector";
import { useAuth } from "../context/AuthContext";
import { applyBranding, getStoredTenantSlug } from "../hooks/useBranding";
import { canModule, ROLE_LABELS } from "../lib/permissions";
import LegalAcceptanceModal from "./LegalAcceptanceModal";

const nav = [
  { to: "/app", label: "Inicio", always: true as const },
  { to: "/app/organizacion", label: "Organización", module: "companies" as const },
  { to: "/app/organigrama", label: "Organigrama", module: "employees" as const },
  { to: "/app/proyectos", label: "Proyectos", module: "companies" as const },
  { to: "/app/empleados", label: "Empleados", module: "employees" as const },
  { to: "/app/fichajes", label: "Fichajes", module: "clock_ins" as const },
  { to: "/app/incidencias", label: "Incidencias", module: "clock_ins" as const },
  { to: "/app/paradas", label: "Paradas", module: "breaks" as const },
  { to: "/app/permisos", label: "Permisos", module: "leave" as const },
  { to: "/app/turnos", label: "Turnos", module: "shifts" as const },
  { to: "/app/documentos", label: "Documentos", module: "documents" as const },
  { to: "/app/firmas", label: "Firmas", module: "signatures" as const },
  { to: "/app/legal", label: "Textos legales", module: "legal" as const },
  { to: "/app/grupos", label: "Grupos", module: "groups" as const },
  { to: "/app/cuenta", label: "Cuenta", module: "tenant" as const, write: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { open: sidebarOpen, toggle: toggleSidebar, close: closeSidebar } =
    useResponsiveSidebar();
  const [tenantLogo, setTenantLogo] = useState<string | null>(null);

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
      .then((b) => {
        applyBranding(b);
        setTenantLogo(b.logo_url);
      })
      .catch(() => {});
  }, [user]);

  if (!user) return null;

  const displayRole = ROLE_LABELS[user.user_type ?? user.role] ?? user.role;

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
      <aside id="app-sidebar" className="sidebar sidebar--light">
        <div className="brand">
          <BrandLogo variant="light" compact logoSrc={tenantLogo} alt={user.tenant_name} />
          <p className="tenant-label">{user.tenant_name}</p>
        </div>
        <div className="user-chip">
          <span className="user-name">{user.full_name}</span>
          <span className="badge">{displayRole}</span>
        </div>
        <OrgSelector />
        <nav onClick={closeSidebar}>
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
        <div className="main-topbar">
          <button
            type="button"
            className="sidebar-toggle"
            aria-expanded={sidebarOpen}
            aria-controls="app-sidebar"
            onClick={toggleSidebar}
          >
            <span className="sidebar-toggle__bars" aria-hidden />
            <span className="sidebar-toggle__label">Menú</span>
          </button>
          <NotificationBell />
        </div>
        <LegalAcceptanceModal />
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
