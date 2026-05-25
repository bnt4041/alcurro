import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Project } from "../api/types";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";
import { tableActionButtons } from "../lib/tableFormatters";

type ProjectRow = Project & { hours_label: string; status_label: string };

const PROJECT_IMPORT_COLUMNS = [
  { key: "name", header: "Nombre", example: "Obra Calle Mayor" },
  { key: "address", header: "Dirección", example: "C/ Mayor 1, Madrid" },
  { key: "planned_hours", header: "Horas previstas", example: "120" },
  { key: "is_active", header: "Activo (si/no)", example: "si" },
];

const emptyForm = () => ({
  name: "",
  address: "",
  planned_hours: "",
  is_active: true,
  active_for_clock: true,
});

export default function ProjectsPage() {
  const { user } = useAuth();
  const canWrite = user && canModule(user.permissions, "write", "companies");
  const [rows, setRows] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await api.get<Project[]>("/projects?include_inactive=true"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tableData = useMemo<ProjectRow[]>(
    () =>
      rows.map((p) => ({
        ...p,
        hours_label:
          p.planned_hours != null ? `${p.planned_hours} h` : "—",
        status_label: p.active_for_clock
          ? p.is_active
            ? "Activo (fichaje)"
            : "Solo fichaje"
          : "Inactivo",
      })),
    [rows]
  );

  const columns = useMemo<DataTableColumn<ProjectRow>[]>(() => {
    const cols: DataTableColumn<ProjectRow>[] = [
      {
        title: "Código",
        field: "code",
        headerFilter: "input",
        formatter: (c) => `<code>${String(c.getValue())}</code>`,
        width: 100,
      },
      { title: "Nombre", field: "name", headerFilter: "input", minWidth: 160 },
      {
        title: "Dirección",
        field: "address",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        minWidth: 180,
      },
      { title: "Horas prev.", field: "hours_label", headerFilter: "input", width: 100 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", Activo: "Activo", Inactivo: "Inactivo" },
        },
        width: 100,
      },
    ];
    if (canWrite) {
      cols.push({
        title: "",
        field: "id",
        headerFilter: false,
        download: false,
        width: 140,
        formatter: () => tableActionButtons([{ id: "edit", label: "Editar" }]),
      });
    }
    return cols;
  }, [canWrite]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm());
    setOpen(true);
  };

  const openEdit = (p: Project) => {
    setEditing(p);
    setForm({
      name: p.name,
      address: p.address ?? "",
      planned_hours: p.planned_hours != null ? String(p.planned_hours) : "",
      is_active: p.is_active,
      active_for_clock: p.active_for_clock,
    });
    setOpen(true);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!canWrite) return;
    const body = {
      name: form.name.trim(),
      address: form.address.trim() || null,
      planned_hours: form.planned_hours
        ? parseFloat(form.planned_hours.replace(",", "."))
        : null,
      is_active: form.is_active,
      active_for_clock: form.is_active ? form.active_for_clock : false,
    };
    try {
      if (editing) {
        await api.patch(`/projects/${editing.id}`, body);
        setMsg("Proyecto actualizado");
      } else {
        await api.post("/projects", body);
        setMsg("Proyecto creado");
      }
      setOpen(false);
      load();
    } catch (err) {
      setMsg(String(err));
    }
  };

  const onCellAction = (action: string, row: ProjectRow) => {
    if (action === "edit") openEdit(row);
  };

  return (
    <>
      <PageHeader
        title="Proyectos"
        subtitle="Obras o proyectos de la empresa activa en el selector de organización"
        action={
          canWrite ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + Nuevo proyecto
            </button>
          ) : undefined
        }
      />
      {msg && (
        <div
          className={`alert ${
            msg.includes("creado") || msg.includes("actualizado")
              ? "alert-ok"
              : "alert-error"
          }`}
        >
          {msg}
        </div>
      )}
      <p className="muted small" style={{ marginBottom: "1rem" }}>
        Los proyectos se gestionan por empresa. Cambia la empresa en el menú lateral si
        necesitas ver otros proyectos.
      </p>
      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="proyectos"
        onCellAction={canWrite ? onCellAction : undefined}
        importConfig={
          canWrite
            ? {
                templateFilename: "plantilla_proyectos",
                columns: PROJECT_IMPORT_COLUMNS,
                hint: "Un proyecto por fila; el código se genera automáticamente",
                onImport: async (mapped) => {
                  const res = await api.post<{ created: number; errors: string[] }>(
                    "/projects/bulk-import",
                    { rows: mapped }
                  );
                  return { created: res.created, errors: res.errors };
                },
              }
            : undefined
        }
        onImportComplete={load}
      />

      <Modal
        title={editing ? "Editar proyecto" : "Nuevo proyecto"}
        open={open}
        onClose={() => setOpen(false)}
      >
        <form onSubmit={save} className="form-grid">
          <label>
            Nombre
            <input
              required
              value={form.name}
              onChange={(ev) => setForm({ ...form, name: ev.target.value })}
            />
          </label>
          <label className="form-grid-full">
            Dirección (opcional)
            <input
              value={form.address}
              onChange={(ev) => setForm({ ...form, address: ev.target.value })}
            />
          </label>
          <label>
            Horas previstas (opcional)
            <input
              type="number"
              min={0}
              step={0.5}
              placeholder="—"
              value={form.planned_hours}
              onChange={(ev) =>
                setForm({ ...form, planned_hours: ev.target.value })
              }
            />
          </label>
          {editing && (
            <>
              <label className="checkbox" style={{ alignSelf: "end" }}>
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(ev) =>
                    setForm({
                      ...form,
                      is_active: ev.target.checked,
                      active_for_clock: ev.target.checked
                        ? form.active_for_clock
                        : false,
                    })
                  }
                />
                <span>Proyecto activo</span>
              </label>
              <label className="checkbox" style={{ alignSelf: "end" }}>
                <input
                  type="checkbox"
                  disabled={!form.is_active}
                  checked={form.active_for_clock}
                  onChange={(ev) =>
                    setForm({ ...form, active_for_clock: ev.target.checked })
                  }
                />
                <span>Disponible al fichar</span>
              </label>
            </>
          )}
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              {editing ? "Guardar" : "Crear"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
