import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";

interface Stats {
  employees: number;
  clockIns: number;
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
      api.get<unknown[]>("/leave-requests?status=pending"),
      api.get<unknown[]>("/documents"),
    ])
      .then(([e, c, l, d]) =>
        setStats({
          employees: e.length,
          clockIns: c.length,
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
        subtitle="Gestión de empleados, fichajes, vacaciones y WhatsApp"
      />
      {error && <div className="alert alert-error">{error}</div>}
      <div className="stats-grid">
        <StatCard label="Empleados" value={stats?.employees} to="/empleados" />
        <StatCard label="Fichajes" value={stats?.clockIns} to="/fichajes" />
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
            <Link to="/configuracion">Configurar goWA y Ollama</Link>
          </li>
          <li>
            <Link to="/empleados">Alta de empleados</Link>
          </li>
          <li>
            <Link to="/documentos">Subir nóminas / contratos</Link>
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
      <span className="stat-value">{value ?? "—"}</span>
      <span className="stat-label">{label}</span>
    </Link>
  );
}
