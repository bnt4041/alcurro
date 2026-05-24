import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { canModule, PERM_LABELS, PERM_SECTIONS, type Perm } from "../lib/permissions";

interface Group {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
  member_count: number;
}

interface PermItem {
  key: string;
  label: string;
}

interface PermSection {
  section: string;
  items: PermItem[];
}

const FALLBACK_SECTIONS: PermSection[] = PERM_SECTIONS.map((s) => ({
  section: s.section,
  items: s.keys.map((key) => ({ key, label: PERM_LABELS[key] })),
}));

export default function GroupsPage() {
  const { user } = useAuth();
  const [groups, setGroups] = useState<Group[]>([]);
  const [catalogSections, setCatalogSections] = useState<PermSection[]>(FALLBACK_SECTIONS);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Group | null>(null);
  const [form, setForm] = useState({ name: "", description: "", permissions: [] as string[] });
  const [error, setError] = useState("");

  const canRead = user && canModule(user.permissions, "read", "groups");
  const canWrite = user && canModule(user.permissions, "write", "groups");

  const load = useCallback(async () => {
    setGroups(await api.get<Group[]>("/groups"));
    try {
      const sections = await api.get<PermSection[]>("/groups/catalog");
      if (sections.length) setCatalogSections(sections);
    } catch {
      setCatalogSections(FALLBACK_SECTIONS);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", description: "", permissions: [] });
    setOpen(true);
  };

  const openEdit = (g: Group) => {
    setEditing(g);
    setForm({
      name: g.name,
      description: g.description ?? "",
      permissions: [...g.permissions],
    });
    setOpen(true);
  };

  const togglePerm = (key: string) => {
    setForm((f) => ({
      ...f,
      permissions: f.permissions.includes(key)
        ? f.permissions.filter((p) => p !== key)
        : [...f.permissions, key],
    }));
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (editing) {
        await api.patch(`/groups/${editing.id}`, form);
      } else {
        await api.post("/groups", form);
      }
      setOpen(false);
      load();
    } catch (err) {
      setError(String(err));
    }
  };

  const remove = async (g: Group) => {
    if (g.is_system || !confirm(`¿Eliminar grupo "${g.name}"?`)) return;
    await api.delete(`/groups/${g.id}`);
    load();
  };

  if (!canRead) {
    return <p className="muted">No tienes permiso para ver grupos.</p>;
  }

  return (
    <>
      <PageHeader
        title="Grupos y permisos"
        subtitle="Personaliza qué puede hacer cada grupo de usuarios"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nuevo grupo
            </button>
          ) : undefined
        }
      />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Grupo</th>
              <th>Permisos</th>
              <th>Miembros</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.id}>
                <td>
                  <strong>{g.name}</strong>
                  {g.is_system && <span className="badge">Sistema</span>}
                  {g.description && <div className="muted small">{g.description}</div>}
                </td>
                <td className="small">{g.permissions.length} permisos</td>
                <td>{g.member_count}</td>
                <td>
                  {canWrite && (
                    <>
                      <button type="button" className="btn btn-sm" onClick={() => openEdit(g)}>
                        Editar
                      </button>
                      {!g.is_system && (
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => remove(g)}
                        >
                          Eliminar
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Editar grupo" : "Nuevo grupo"}>
        <form onSubmit={save}>
          {error && <div className="alert alert-error">{error}</div>}
          <label>
            Nombre
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              disabled={editing?.is_system}
            />
          </label>
          <label>
            Descripción
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className="perm-sections">
            {catalogSections.map((section) => (
              <fieldset key={section.section} className="perm-grid">
                <legend>{section.section}</legend>
                {section.items.map((p) => (
                  <label key={p.key} className="perm-check">
                    <input
                      type="checkbox"
                      checked={form.permissions.includes(p.key)}
                      onChange={() => togglePerm(p.key)}
                    />
                    {p.label}
                  </label>
                ))}
              </fieldset>
            ))}
          </div>
          <button type="submit" className="btn btn-primary">
            Guardar
          </button>
        </form>
      </Modal>
    </>
  );
}
