import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import MarketingLayout from "./components/MarketingLayout";
import PlatformLayout from "./components/PlatformLayout";
import ProtectedRoute, { PlatformProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import AccountPage from "./pages/AccountPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import ClockInsPage from "./pages/ClockInsPage";
import Dashboard from "./pages/Dashboard";
import DocumentsPage from "./pages/DocumentsPage";
import EmployeesPage from "./pages/EmployeesPage";
import GroupsPage from "./pages/GroupsPage";
import HomePage from "./pages/HomePage";
import LeaveRequestsPage from "./pages/LeaveRequestsPage";
import TenantLoginPage from "./pages/TenantLoginPage";
import OrganizationPage from "./pages/OrganizationPage";
import PlatformDiscountsPage from "./pages/PlatformDiscountsPage";
import PlatformPage from "./pages/PlatformPage";
import PlatformPricingPage from "./pages/PlatformPricingPage";
import PlatformStripePage from "./pages/PlatformStripePage";
import SettingsPage from "./pages/SettingsPage";
import ShiftsPage from "./pages/ShiftsPage";
import SignupPage from "./pages/SignupPage";
import SignupSuccessPage from "./pages/SignupSuccessPage";

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<MarketingLayout />}>
              <Route index element={<HomePage />} />
              <Route path="registro" element={<SignupPage />} />
              <Route path="registro/ok" element={<SignupSuccessPage />} />
            </Route>

            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/login" element={<Navigate to="/admin/login" replace />} />
            <Route path="/acceso-cliente" element={<TenantLoginPage />} />

            <Route path="/admin" element={<PlatformProtectedRoute />}>
              <Route element={<PlatformLayout />}>
                <Route index element={<PlatformPage />} />
                <Route path="tarifas" element={<PlatformPricingPage />} />
                <Route path="descuentos" element={<PlatformDiscountsPage />} />
                <Route path="cobros" element={<PlatformStripePage />} />
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

            <Route path="/plataforma" element={<Navigate to="/admin" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
