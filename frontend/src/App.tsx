import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import PlatformLayout from "./components/PlatformLayout";
import ProtectedRoute, { PlatformProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import AccountPage from "./pages/AccountPage";
import ClockInsPage from "./pages/ClockInsPage";
import Dashboard from "./pages/Dashboard";
import DocumentsPage from "./pages/DocumentsPage";
import EmployeesPage from "./pages/EmployeesPage";
import GroupsPage from "./pages/GroupsPage";
import LeaveRequestsPage from "./pages/LeaveRequestsPage";
import LoginPage from "./pages/LoginPage";
import TenantLoginPage from "./pages/TenantLoginPage";
import OrganizationPage from "./pages/OrganizationPage";
import PlatformPage from "./pages/PlatformPage";
import SettingsPage from "./pages/SettingsPage";
import ShiftsPage from "./pages/ShiftsPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/acceso-cliente" element={<TenantLoginPage />} />
          <Route element={<PlatformProtectedRoute />}>
            <Route element={<PlatformLayout />}>
              <Route index element={<PlatformPage />} />
            </Route>
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="organizacion" element={<OrganizationPage />} />
              <Route path="empleados" element={<EmployeesPage />} />
              <Route path="fichajes" element={<ClockInsPage />} />
              <Route path="vacaciones" element={<LeaveRequestsPage />} />
              <Route path="turnos" element={<ShiftsPage />} />
              <Route path="documentos" element={<DocumentsPage />} />
              <Route path="grupos" element={<GroupsPage />} />
              <Route path="cuenta" element={<AccountPage />} />
              <Route path="configuracion" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="/plataforma" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
