import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";

interface Department {
  id: string;
  name: string;
  code: string;
}

interface WorkCenter {
  id: string;
  name: string;
  code: string;
  departments: Department[];
}

interface OrgTreeCompany {
  id: string;
  name: string;
  work_centers: WorkCenter[];
}

export default function OrganizationPage() {
  const { user } = useAuth();
  const [tree, setTree] = useState<OrgTreeCompany[]>([]);
  const [wcForm, setWcForm] = useState({ name: "" });
  const [deptForm, setDeptForm] = useState({ name: "", work_center_id: "" });
  const [msg, setMsg] = useState("");

  const load = () => api.get<OrgTreeCompany[]>("/org/tree").then(setTree);

  useEffect(() => {
    load();
  }, []);

  const canWc = user && canModule(user.permissions, "write", "work_centers");
  const canDept = user && canModule(user.permissions, "write", "departments");

  const addWc = async (e: FormEvent) => {
    e.preventDefault();
    const created = await api.post<{ code: string }>("/org/work-centers", wcForm);
    setWcForm({ name: "" });
    setMsg(`Centro creado (código ${created.code})`);
    load();
  };

  const addDept = async (e: FormEvent) => {
    e.preventDefault();
    const created = await api.post<{ code: string }>("/org/departments", deptForm);
    setDeptForm({ name: "", work_center_id: "" });
    setMsg(`Departamento creado (código ${created.code})`);
    load();
  };

  return (
    <>
      <PageHeader
        title="Organización"
        subtitle="Empresa → Centro de trabajo → Departamento → Empleados"
      />
      {msg && <div className="alert alert-info">{msg}</div>}

      {canWc && (
        <section className="card settings-section">
          <h3>Nuevo centro de trabajo</h3>
          <p className="muted small">
            El código se asigna automáticamente (p. ej. CEN-001, CEN-002…).
          </p>
          <form onSubmit={addWc} className="form-grid">
            <label>
              Nombre
              <input
                required
                value={wcForm.name}
                onChange={(e) => setWcForm({ ...wcForm, name: e.target.value })}
              />
            </label>
            <button type="submit" className="btn btn-primary">
              Crear centro
            </button>
          </form>
        </section>
      )}

      {canDept && (
        <section className="card settings-section">
          <h3>Nuevo departamento</h3>
          <p className="muted small">
            El código se asigna automáticamente (p. ej. DEP-001, DEP-002…).
          </p>
          <form onSubmit={addDept} className="form-grid">
            <label>
              Centro
              <select
                required
                value={deptForm.work_center_id}
                onChange={(e) =>
                  setDeptForm({ ...deptForm, work_center_id: e.target.value })
                }
              >
                <option value="">—</option>
                {tree
                  .flatMap((c) => c.work_centers)
                  .map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Nombre
              <input
                required
                value={deptForm.name}
                onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
              />
            </label>
            <button type="submit" className="btn btn-primary">
              Crear departamento
            </button>
          </form>
        </section>
      )}

      <div className="org-tree card">
        {tree.map((company) => (
          <div key={company.id} className="org-tree__company">
            <h3>{company.name}</h3>
            {company.work_centers.map((wc) => (
              <div key={wc.id} className="org-tree__wc">
                <strong>
                  {wc.name} <code>{wc.code}</code>
                </strong>
                <ul>
                  {wc.departments.map((d) => (
                    <li key={d.id}>
                      {d.name} <code>{d.code}</code>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
