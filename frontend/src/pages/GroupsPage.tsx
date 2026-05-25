import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { canModule, PERM_LABELS, PERM_SECTIONS } from "../lib/permissions";
import { tableActionButtons, type TableAction } from "../lib/tableFormatters";

interface Group {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
  member_count: number;
}

type GroupRow = Group & { system_label: string; perms_count: number };

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
  const [loading, setLoading] = useState(true);
  const [catalogSections, setCatalogSections] = useState<PermSection[]>(FALLBACK_SECTIONS);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Group | null>(null);
  const [form, setForm] = useState({ name: "", description: "", permissions: [] as string[] });
  const [error, setError] = useState("");

  const canRead = user && canModule(user.permissions, "read", "groups");
  const canWrite = user && canModule(user.permissions, "write", "groups");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setGroups(await api.get<Group[]>("/groups"));
      try {
        const sections = await api.get<PermSection[]>("/groups/catalog");
        if (sections.length) setCatalogSections(sections);
      } catch {
        setCatalogSections(FALLBACK_SECTIONS);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tableData = useMemo<GroupRow[]>(
    () =>
      groups.map((g) => ({
        ...g,
        system_label: g.is_system ? "Sistema" : "Personalizado",
        perms_count: g.permissions.length,
      })),
    [groups]
  );

  const columns = useMemo<DataTableColumn<GroupRow>[]>(() => {
    const cols: DataTableColumn<GroupRow>[] = [
      { title: "Grupo", field: "name", headerFilter: "input", minWidth: 160 },
      {
        title: "Descripción",
        field: "description",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 180,
      },
      {
        title: "Tipo",
        field: "system_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", Sistema: "Sistema", Personalizado: "Personalizado" },
        },
        width: 120,
      },
      { title: "Permisos", field: "perms_count", headerFilter: "number", width: 90 },
      { title: "Miembros", field: "member_count", headerFilter: "number", width: 90 },
    ];
    if (canWrite) {
      cols.push({
        title: "",
        field: "id",
        headerFilter: false,
        sorter: false,
        download: false,
        width: 160,
        formatter: (cell) => {
          const row = cell.getRow().getData() as GroupRow;
          const actions: TableAction[] = [{ id: "edit", label: "Editar" }];
          if (!row.is_system) {
            actions.push({ id: "delete", label: "Eliminar", className: "btn-danger" });
          }
          return tableActionButtons(actions);
        },
      });
    }
    return cols;
  }, [canWrite]);

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

  const onCellAction = (action: string, row: GroupRow) => {
    if (action === "edit") openEdit(row);
    else if (action === "delete") remove(row);
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
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="grupos"
        height="480px"
        onCellAction={onCellAction}
      />

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
