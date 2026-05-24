import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

interface PlatformUserRow {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

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

      {loading ? (
        <p className="muted">Cargando…</p>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Email</th>
                <th>Estado</th>
                <th>Alta</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} className={!u.is_active ? "row-inactive" : ""}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{u.is_active ? "Activo" : "Inactivo"}</td>
                  <td>{new Date(u.created_at).toLocaleDateString("es-ES")}</td>
                  <td className="actions">
                    <button type="button" className="btn btn-sm" onClick={() => resetPassword(u)}>
                      Contraseña
                    </button>
                    <button type="button" className="btn btn-sm" onClick={() => toggleActive(u)}>
                      {u.is_active ? "Desactivar" : "Activar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
