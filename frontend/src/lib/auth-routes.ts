import type { AuthUser } from "../context/AuthContext";

/** Ruta tras login según tipo de usuario (portal tenant). */
export function getTenantHomePath(user: AuthUser): string {
  switch (user.role) {
    case "tenant_admin":
    case "admin":
      return "/app";
    case "labor_inspector":
      return "/app/fichajes";
    case "employee":
      return "/app";
    case "manager":
    case "supervisor":
    default:
      return "/app";
  }
}
