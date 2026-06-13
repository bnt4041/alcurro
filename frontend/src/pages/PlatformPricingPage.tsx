import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import { centsToEurosInput, formatMoney, parseEurosToCents } from "../lib/money";
import { tableActionButtons } from "../lib/tableFormatters";

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
  ls_product_id: string | null;
  ls_variant_id_monthly: string | null;
  ls_variant_id_annual: string | null;
}

type PlanTableRow = PricingPlan & {
  monthly_label: string;
  annual_label: string;
  status_label: string;
};

const empty = () => ({
  code: "",
  name: "",
  description: "",
  monthly_eur: "18.00",
  annual_monthly_eur: "15.00",
  max_active_users: "3",
  sort_order: "0",
  is_active: true,
  ls_variant_id_monthly: "",
  ls_variant_id_annual: "",
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
      ls_variant_id_monthly: p.ls_variant_id_monthly ?? "",
      ls_variant_id_annual: p.ls_variant_id_annual ?? "",
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
      ls_variant_id_monthly: form.ls_variant_id_monthly.trim() || null,
      ls_variant_id_annual: form.ls_variant_id_annual.trim() || null,
    };
    try {
      if (editingId) {
        const { code: _code, ...patchBody } = body;
        await api.patch(`/platform/pricing-plans/${editingId}`, patchBody);
        toast.success("Tarifa actualizada");
      } else {
        await api.post<PricingPlan>("/platform/pricing-plans", body);
        toast.success("Tarifa creada");
      }
      setOpen(false);
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const tableData = useMemo<PlanTableRow[]>(
    () =>
      plans.map((p) => ({
        ...p,
        monthly_label: `${formatMoney(p.monthly_price_cents, p.currency)}/mes`,
        annual_label: `${formatMoney(p.annual_price_per_month_cents, p.currency)}/mes (${formatMoney(p.annual_price_per_month_cents * 12, p.currency)}/año)`,
        status_label: p.is_active ? "Activa" : "Inactiva",
      })),
    [plans]
  );

  const columns = useMemo<DataTableColumn<PlanTableRow>[]>(
    () => [
      {
        title: "Código",
        field: "code",
        headerFilter: "input",
        formatter: (c) => `<code>${String(c.getValue())}</code>`,
        width: 100,
      },
      {
        title: "Nombre",
        field: "name",
        headerFilter: "input",
        minWidth: 160,
        formatter: (cell) => {
          const r = cell.getRow().getData() as PlanTableRow;
          const desc = r.description ? `<div class="muted small">${r.description}</div>` : "";
          return `<strong>${r.name}</strong>${desc}`;
        },
      },
      { title: "Mensual", field: "monthly_label", headerFilter: "input", width: 120 },
      { title: "Anual (€/mes)", field: "annual_label", headerFilter: "input", minWidth: 140 },
      { title: "Usuarios", field: "max_active_users", headerFilter: "number", width: 90 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", Activa: "Activa", Inactiva: "Inactiva" },
        },
        formatter: (cell) => {
          const r = cell.getRow().getData() as PlanTableRow;
          const cls = r.is_active ? "badge--ok" : "badge--muted";
          return `<span class="badge ${cls}">${r.status_label}</span>`;
        },
        width: 100,
      },
      {
        title: "",
        field: "id",
        headerFilter: false,
        download: false,
        width: 140,
        minWidth: 140,
        formatter: () =>
          tableActionButtons([
            { id: "toggle", label: "Activar/Desactivar" },
            { id: "edit", label: "Editar" },
            { id: "delete", label: "Eliminar", className: "btn-danger" },
          ]),
      },
    ],
    []
  );

  const onCellAction = (action: string, row: PlanTableRow) => {
    if (action === "toggle") void toggleActive(row);
    if (action === "edit") openEdit(row);
    if (action === "delete") void remove(row);
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

      <DataTable
        data={tableData}
        columns={columns}
        exportFilename="tarifas"
        onCellAction={onCellAction}
      />

      <Modal
        title={editingId ? "Editar tarifa" : "Nueva tarifa"}
        open={open}
        onClose={() => setOpen(false)}
        wide
      >
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

          <div className="form-span-2">
            <p className="muted small" style={{ margin: "0.5rem 0 0.75rem" }}>
              <strong>Lemon Squeezy</strong> — Crea el producto y sus variantes en el dashboard de LS
              y pega aquí los IDs numéricos de cada variante.
            </p>
          </div>
          <label>
            Variant ID mensual (LS)
            <input
              value={form.ls_variant_id_monthly}
              placeholder="p. ej. 123456"
              onChange={(e) =>
                setForm({ ...form, ls_variant_id_monthly: e.target.value })
              }
            />
            <span className="field-hint muted small">
              ID de la variante mensual en Lemon Squeezy
            </span>
          </label>
          <label>
            Variant ID anual (LS)
            <input
              value={form.ls_variant_id_annual}
              placeholder="p. ej. 123457"
              onChange={(e) =>
                setForm({ ...form, ls_variant_id_annual: e.target.value })
              }
            />
            <span className="field-hint muted small">
              ID de la variante anual en Lemon Squeezy
            </span>
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
      </Modal>
    </>
  );
}
