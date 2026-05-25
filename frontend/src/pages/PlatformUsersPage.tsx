import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { tableActionButtons } from "../lib/tableFormatters";

interface PlatformUserRow {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

type UserTableRow = PlatformUserRow & {
  status_label: string;
  created_label: string;
};

const emptyForm = () => ({
  email: "",
  full_name: "",
  password: "",
});

export default function PlatformUsersPage() {
  const toast = useToast();
  const { platformUser } = useAuth();
  const [rows, setRows] = useState<PlatformUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setRows(await api.get<PlatformUserRow[]>("/platform/users"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const tableData = useMemo<UserTableRow[]>(
    () =>
      rows.map((u) => ({
        ...u,
        status_label: u.is_active ? "Activo" : "Inactivo",
        created_label: new Date(u.created_at).toLocaleDateString("es-ES"),
      })),
    [rows]
  );

  const columns = useMemo<DataTableColumn<UserTableRow>[]>(
    () => [
      { title: "Nombre", field: "full_name", headerFilter: "input", minWidth: 160 },
      { title: "Email", field: "email", headerFilter: "input", minWidth: 180 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", Activo: "Activo", Inactivo: "Inactivo" },
        },
        width: 100,
      },
      { title: "Alta", field: "created_label", headerFilter: "input", width: 110 },
      {
        title: "",
        field: "id",
        headerFilter: false,
        download: false,
        width: 200,
        formatter: () =>
          tableActionButtons([
            { id: "password", label: "Contraseña" },
            { id: "toggle", label: "Activar/Desactivar" },
          ]),
      },
    ],
    []
  );

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/platform/users", form);
      toast.success("Administrador creado correctamente");
      setOpen(false);
      setForm(emptyForm());
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (row: PlatformUserRow) => {
    if (row.id === platformUser?.id && row.is_active) {
      toast.error("No puedes desactivarte a ti mismo");
      return;
    }
    try {
      await api.patch(`/platform/users/${row.id}`, { is_active: !row.is_active });
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const resetPassword = async (row: PlatformUserRow) => {
    const password = prompt(`Nueva contraseña para ${row.email}:`);
    if (!password || password.length < 6) return;
    try {
      await api.patch(`/platform/users/${row.id}`, { password });
      toast.success("Contraseña actualizada");
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const onCellAction = (action: string, row: UserTableRow) => {
    if (action === "password") void resetPassword(row);
    if (action === "toggle") void toggleActive(row);
  };

  return (
    <>
      <PageHeader
        title="Usuarios de administración"
        subtitle="Acceso al panel global de alcurro (/admin)"
        action={
          <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
            + Nuevo administrador
          </button>
        }
      />

      <DataTable
        data={tableData}
        columns={columns}
        loading={loading}
        exportFilename="administradores"
        onCellAction={onCellAction}
      />

      <Modal title="Nuevo administrador" open={open} onClose={() => setOpen(false)}>
        <form onSubmit={create} className="form-grid">
          <label>
            Nombre completo
            <input
              required
              value={form.full_name}
              onChange={(ev) => setForm({ ...form, full_name: ev.target.value })}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              required
              value={form.email}
              onChange={(ev) => setForm({ ...form, email: ev.target.value })}
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              required
              minLength={6}
              value={form.password}
              onChange={(ev) => setForm({ ...form, password: ev.target.value })}
            />
          </label>
          <div className="form-actions form-grid-full">
            <button type="button" className="btn" onClick={() => setOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Creando…" : "Crear"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
