import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import MarketingLayout from "./components/MarketingLayout";
import PlatformLayout from "./components/PlatformLayout";
import ProtectedRoute, { PlatformProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import AccountPage from "./pages/AccountPage";
import BreaksPage from "./pages/BreaksPage";
import ClockInsPage from "./pages/ClockInsPage";
import ClockSettingsPage from "./pages/ClockSettingsPage";
import Dashboard from "./pages/Dashboard";
import DocumentsPage from "./pages/DocumentsPage";
import LegalPage from "./pages/LegalPage";
import AvisoLegalPage from "./pages/AvisoLegalPage";
import PrivacidadPage from "./pages/PrivacidadPage";
import CookiesPage from "./pages/CookiesPage";
import ContactoPage from "./pages/ContactoPage";
import EmployeesPage from "./pages/EmployeesPage";
import GroupsPage from "./pages/GroupsPage";
import HomePage from "./pages/HomePage";
import LeaveRequestsPage from "./pages/LeaveRequestsPage";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import OrganizationPage from "./pages/OrganizationPage";
import ProjectsPage from "./pages/ProjectsPage";
import IncidentsPage from "./pages/IncidentsPage";
import JustifyIncidentPage from "./pages/JustifyIncidentPage";
import PlatformDiscountsPage from "./pages/PlatformDiscountsPage";
import PlatformPage from "./pages/PlatformPage";
import PlatformUsersPage from "./pages/PlatformUsersPage";
import PlatformPricingPage from "./pages/PlatformPricingPage";
import PlatformLemonSqueezyPage from "./pages/PlatformLemonSqueezyPage";
import PlatformWhatsAppPage from "./pages/PlatformWhatsAppPage";
import PlatformMailPage from "./pages/PlatformMailPage";
import PlatformAIPage from "./pages/PlatformAIPage";
import PlatformPurgePage from "./pages/PlatformPurgePage";
import PlatformPolicyPage from "./pages/PlatformPolicyPage";
import PlatformSettingsPage from "./pages/PlatformSettingsPage";
import OrgChartPage from "./pages/OrgChartPage";
import ShiftsPage from "./pages/ShiftsPage";
import SignupPage from "./pages/SignupPage";
import SignupSuccessPage from "./pages/SignupSuccessPage";
import SignDocumentPage from "./pages/SignDocumentPage";
import ReportsPage from "./pages/ReportsPage";
import SignaturesPage from "./pages/SignaturesPage";
import LegalTokenPage from "./pages/LegalTokenPage";
import DeveloperPage from "./pages/DeveloperPage";

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
              <Route path="aviso-legal" element={<AvisoLegalPage />} />
              <Route path="privacidad" element={<PrivacidadPage />} />
              <Route path="cookies" element={<CookiesPage />} />
              <Route path="contacto" element={<ContactoPage />} />
            </Route>

            <Route path="/firmar/:token" element={<SignDocumentPage />} />
            <Route path="/legal/:token" element={<LegalTokenPage />} />
            <Route
              path="/justificar-incidencia/:token"
              element={<JustifyIncidentPage />}
            />

            <Route path="/acceso" element={<LoginPage />} />
            <Route path="/login" element={<Navigate to="/acceso" replace />} />
            <Route path="/acceso-cliente" element={<Navigate to="/acceso" replace />} />
            <Route path="/admin/login" element={<Navigate to="/acceso" replace />} />
            <Route path="/recuperar" element={<ForgotPasswordPage />} />
            <Route path="/recuperar/:token" element={<ResetPasswordPage />} />

            <Route path="/admin" element={<PlatformProtectedRoute />}>
              <Route element={<PlatformLayout />}>
                <Route index element={<PlatformPage />} />
                <Route path="usuarios" element={<PlatformUsersPage />} />
                <Route path="tarifas" element={<PlatformPricingPage />} />
                <Route path="descuentos" element={<PlatformDiscountsPage />} />
                <Route path="cobros" element={<PlatformLemonSqueezyPage />} />
                <Route path="configuracion" element={<PlatformSettingsPage />} />
                <Route path="whatsapp" element={<PlatformWhatsAppPage />} />
                <Route path="mail" element={<PlatformMailPage />} />
                <Route path="ia" element={<PlatformAIPage />} />
                <Route path="politicas" element={<PlatformPolicyPage />} />
                <Route path="purgar" element={<PlatformPurgePage />} />
              </Route>
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route path="/app" element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="fichajes" element={<ClockInsPage />} />
                <Route path="fichajes/configuracion" element={<ClockSettingsPage />} />
                <Route path="incidencias" element={<IncidentsPage />} />
                <Route path="paradas" element={<BreaksPage />} />
                <Route path="organizacion" element={<OrganizationPage />} />
                <Route path="organigrama" element={<OrgChartPage />} />
                <Route path="proyectos" element={<ProjectsPage />} />
                <Route path="empleados" element={<EmployeesPage />} />
                <Route path="informes" element={<ReportsPage />} />
                <Route path="permisos" element={<LeaveRequestsPage />} />
                <Route path="vacaciones" element={<LeaveRequestsPage />} />
                <Route path="turnos" element={<ShiftsPage />} />
                <Route path="documentos" element={<DocumentsPage />} />
                <Route path="firmas" element={<SignaturesPage />} />
                <Route path="legal" element={<LegalPage />} />
                <Route path="grupos" element={<GroupsPage />} />
                <Route path="cuenta" element={<AccountPage />} />
                <Route path="developer" element={<DeveloperPage />} />
                <Route path="whatsapp" element={<Navigate to="/app" replace />} />
                <Route path="configuracion" element={<Navigate to="/app/cuenta" replace />} />
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
