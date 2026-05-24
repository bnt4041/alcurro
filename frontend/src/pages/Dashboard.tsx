import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import BrandLogo from "../components/BrandLogo";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";

interface Stats {
  employees: number;
  clockIns: number;
  breaks: number;
  pendingLeaves: number;
  documents: number;
}

interface TenantBranding {
  name: string;
  logo_url: string | null;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [branding, setBranding] = useState<TenantBranding | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<TenantBranding>("/tenants/current")
      .then((t) => setBranding({ name: t.name, logo_url: t.logo_url }))
      .catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([
      api.get<unknown[]>("/employees"),
      api.get<unknown[]>("/clock-ins?limit=500"),
      api.get<unknown[]>("/breaks?limit=500"),
      api.get<unknown[]>("/leave-requests?status=pending"),
      api.get<unknown[]>("/documents"),
    ])
      .then(([e, c, b, l, d]) =>
        setStats({
          employees: e.length,
          clockIns: c.length,
          breaks: b.length,
          pendingLeaves: l.length,
          documents: d.length,
        })
      )
      .catch((err) => setError(String(err)));
  }, []);

  const displayName = branding?.name ?? user?.tenant_name ?? "Panel";

  return (
    <>
      <div className="dashboard-hero card">
        <BrandLogo
          variant="light"
          logoSrc={branding?.logo_url}
          alt={displayName}
          className="dashboard-hero__logo"
        />
        <div className="dashboard-hero__text">
          <h2 className="dashboard-hero__title">{displayName}</h2>
          <p className="muted">Gestión de empleados, fichajes, paradas y vacaciones</p>
        </div>
      </div>
      <PageHeader
        title="Resumen"
        subtitle="Accesos rápidos y métricas del día"
      />
      {error && <div className="alert alert-error">{error}</div>}
      <div className="stats-grid">
        <StatCard label="Empleados" value={stats?.employees} to="/empleados" />
        <StatCard label="Fichajes" value={stats?.clockIns} to="/fichajes" />
        <StatCard label="Paradas" value={stats?.breaks} to="/paradas" />
        <StatCard
          label="Vacaciones pendientes"
          value={stats?.pendingLeaves}
          to="/vacaciones"
        />
        <StatCard label="Documentos" value={stats?.documents} to="/documentos" />
      </div>
      <section className="card">
        <h3>Accesos rápidos</h3>
        <ul className="quick-links">
          <li>
            <Link to="/empleados">Alta de empleados</Link>
          </li>
          <li>
            <Link to="/fichajes">Consultar fichajes</Link>
          </li>
          <li>
            <Link to="/paradas">Paradas y resumen por empresa</Link>
          </li>
          <li>
            <Link to="/documentos">Subir nóminas / contratos</Link>
          </li>
          <li>
            <Link to="/cuenta">Facturación, logo y suscripción</Link>
          </li>
        </ul>
      </section>
    </>
  );
}

function StatCard({
  label,
  value,
  to,
}: {
  label: string;
  value?: number;
  to: string;
}) {
  return (
    <Link to={to} className="stat-card">
      <span className="stat-card__label">{label}</span>
      <strong className="stat-card__value">{value ?? "…"}</strong>
    </Link>
  );
}
