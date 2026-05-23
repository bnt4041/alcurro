import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";

interface Stats {
  employees: number;
  clockIns: number;
  breaks: number;
  pendingLeaves: number;
  documents: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

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

  return (
    <>
      <PageHeader
        title="Panel alcurro"
        subtitle="Gestión de empleados, fichajes, paradas y vacaciones"
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
            <Link to="/cuenta">Facturación y suscripción</Link>
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
