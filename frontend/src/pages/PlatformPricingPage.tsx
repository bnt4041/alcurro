import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import { centsToEurosInput, formatMoney, parseEurosToCents } from "../lib/money";

interface PricingPlan {
  id: string;
  code: string;
  name: string;
  description: string | null;
  monthly_price_cents: number;
  annual_price_per_month_cents: number;
  max_active_users: number;
  currency: string;
  is_active: boolean;
  sort_order: number;
}

const empty = () => ({
  code: "",
  name: "",
  description: "",
  monthly_eur: "18.00",
  annual_monthly_eur: "15.00",
  max_active_users: "3",
  sort_order: "0",
  is_active: true,
});

export default function PlatformPricingPage() {
  const toast = useToast();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [form, setForm] = useState(empty());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = () =>
    api.get<PricingPlan[]>("/platform/pricing-plans").then(setPlans);

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(empty());
    setOpen(true);
  };

  const openEdit = (p: PricingPlan) => {
    setEditingId(p.id);
    setForm({
      code: p.code,
      name: p.name,
      description: p.description ?? "",
      monthly_eur: centsToEurosInput(p.monthly_price_cents),
      annual_monthly_eur: centsToEurosInput(p.annual_price_per_month_cents),
      max_active_users: String(p.max_active_users),
      sort_order: String(p.sort_order),
      is_active: p.is_active,
    });
    setOpen(true);
  };

  const toggleActive = async (p: PricingPlan) => {
    try {
      await api.patch(`/platform/pricing-plans/${p.id}`, {
        is_active: !p.is_active,
      });
      toast.success(p.is_active ? "Tarifa desactivada" : "Tarifa activada");
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    const body = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description.trim() || null,
      monthly_price_cents: parseEurosToCents(form.monthly_eur),
      annual_price_per_month_cents: parseEurosToCents(form.annual_monthly_eur),
      max_active_users: parseInt(form.max_active_users, 10) || 1,
      sort_order: parseInt(form.sort_order, 10) || 0,
      is_active: form.is_active,
    };
    try {
      if (editingId) {
        const { code: _code, ...patchBody } = body;
        await api.patch(`/platform/pricing-plans/${editingId}`, patchBody);
        toast.success("Tarifa actualizada");
      } else {
        await api.post("/platform/pricing-plans", body);
        toast.success("Tarifa creada");
      }
      setOpen(false);
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const remove = async (p: PricingPlan) => {
    if (!confirm(`¿Eliminar la tarifa «${p.name}»?`)) return;
    try {
      await api.delete(`/platform/pricing-plans/${p.id}`);
      toast.success("Tarifa eliminada");
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  return (
    <>
      <PageHeader
        title="Tarifas"
        subtitle="Planes de suscripción: precio mensual, precio anual y usuarios activos"
        action={
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            + Nueva tarifa
          </button>
        }
      />

      <div className="table-wrap card">
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Mensual</th>
              <th>Anual (€/mes)</th>
              <th>Usuarios</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id} className={!p.is_active ? "row-inactive" : ""}>
                <td>
                  <code>{p.code}</code>
                </td>
                <td>
                  <strong>{p.name}</strong>
                  {p.description && (
                    <div className="muted small">{p.description}</div>
                  )}
                </td>
                <td>{formatMoney(p.monthly_price_cents, p.currency)}/mes</td>
                <td>
                  {formatMoney(p.annual_price_per_month_cents, p.currency)}/mes
                  <div className="muted small">
                    ({formatMoney(p.annual_price_per_month_cents * 12, p.currency)}
                    /año)
                  </div>
                </td>
                <td>{p.max_active_users}</td>
                <td>
                  <span
                    className={`badge ${p.is_active ? "badge--ok" : "badge--muted"}`}
                  >
                    {p.is_active ? "Activa" : "Inactiva"}
                  </span>
                </td>
                <td>
                  <div className="table-actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => toggleActive(p)}
                    >
                      {p.is_active ? "Desactivar" : "Activar"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => openEdit(p)}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => remove(p)}
                    >
                      Eliminar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {open && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => e.target === e.currentTarget && setOpen(false)}
        >
          <div className="modal-panel">
            <h3>{editingId ? "Editar tarifa" : "Nueva tarifa"}</h3>
            <form onSubmit={save} className="form-grid">
              <label>
                Código
                <input
                  required
                  disabled={!!editingId}
                  pattern="[a-z0-9_-]+"
                  value={form.code}
                  onChange={(e) =>
                    setForm({ ...form, code: e.target.value.toLowerCase() })
                  }
                />
              </label>
              <label>
                Nombre
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </label>
              <label className="form-span-2">
                Descripción
                <input
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                />
              </label>
              <label>
                Precio mensual (€)
                <input
                  required
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.monthly_eur}
                  onChange={(e) =>
                    setForm({ ...form, monthly_eur: e.target.value })
                  }
                />
              </label>
              <label>
                Precio anual (€/mes)
                <input
                  required
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.annual_monthly_eur}
                  onChange={(e) =>
                    setForm({ ...form, annual_monthly_eur: e.target.value })
                  }
                />
                <span className="field-hint muted small">
                  Equivalente mensual si contrata 12 meses
                </span>
              </label>
              <label>
                Usuarios activos máx.
                <input
                  required
                  type="number"
                  min="1"
                  value={form.max_active_users}
                  onChange={(e) =>
                    setForm({ ...form, max_active_users: e.target.value })
                  }
                />
              </label>
              <label>
                Orden
                <input
                  type="number"
                  value={form.sort_order}
                  onChange={(e) =>
                    setForm({ ...form, sort_order: e.target.value })
                  }
                />
              </label>
              <label className="form-span-2 checkbox-row">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) =>
                    setForm({ ...form, is_active: e.target.checked })
                  }
                />
                Tarifa activa (disponible para nuevas suscripciones)
              </label>
              <div className="modal-actions form-span-2">
                <button type="submit" className="btn btn-primary">
                  Guardar
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setOpen(false)}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
