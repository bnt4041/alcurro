import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="login-page">
        <p className="muted">Cargando sesión…</p>
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export function PlatformProtectedRoute() {
  const { platformUser, loading } = useAuth();
  if (loading)
    return (
      <div className="login-page">
        <p className="muted">Cargando sesión…</p>
      </div>
    );
  if (!platformUser) return <Navigate to="/login" replace />;
  return <Outlet />;
}
