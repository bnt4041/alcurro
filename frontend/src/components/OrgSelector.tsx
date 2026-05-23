import { useEffect, useState } from "react";
import { api } from "../api/client";
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

export default function OrgSelector() {
  const { user, setActiveCompany, setActiveWorkCenter, setActiveDepartment } = useAuth();
  const [tree, setTree] = useState<OrgTreeCompany[]>([]);

  useEffect(() => {
    if (!user || !canModule(user.permissions, "read", "companies")) return;
    api.get<OrgTreeCompany[]>("/org/tree").then(setTree).catch(() => {});
  }, [user]);

  if (!user || tree.length === 0) return null;

  const company = tree.find((c) => c.id === user.company_id) ?? tree[0];
  const workCenters = company?.work_centers ?? [];
  const wc =
    workCenters.find((w) => w.id === user.work_center_id) ?? workCenters[0];
  const departments = wc?.departments ?? [];
  const dept =
    departments.find((d) => d.id === user.department_id) ?? departments[0];

  return (
    <div className="org-selector">
      {tree.length > 1 && (
        <label>
          Empresa
          <select
            value={user.company_id}
            onChange={(e) => setActiveCompany(e.target.value)}
          >
            {tree.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {workCenters.length > 0 && (
        <label>
          Centro
          <select
            value={wc?.id ?? ""}
            onChange={(e) =>
              setActiveWorkCenter(e.target.value || null)
            }
          >
            {workCenters.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {departments.length > 0 && (
        <label>
          Departamento
          <select
            value={dept?.id ?? ""}
            onChange={(e) =>
              setActiveDepartment(e.target.value || null)
            }
          >
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
