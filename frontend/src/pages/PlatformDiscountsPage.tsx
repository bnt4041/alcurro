import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import PageHeader from "../components/PageHeader";
import { tableActionButtons } from "../lib/tableFormatters";
import { useToast } from "../context/ToastContext";
import { formatMoney, parseEurosToCents } from "../lib/money";

interface PricingPlan {
  id: string;
  code: string;
  name: string;
}

interface Discount {
  id: string;
  code: string;
  name: string;
  description: string | null;
  discount_type: "percent" | "fixed";
  value: number;
  valid_from: string;
  valid_until: string;
  pricing_plan_id: string | null;
  is_active: boolean;
}

const empty = () => ({
  code: "",
  name: "",
  description: "",
  discount_type: "percent" as "percent" | "fixed",
  value: "10",
  valid_from: "",
  valid_until: "",
  pricing_plan_id: "",
  is_active: true,
});

function formatDiscountValue(d: Discount) {
  if (d.discount_type === "percent") return `${d.value}%`;
  return formatMoney(d.value);
}

export default function PlatformDiscountsPage() {
  const toast = useToast();
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [form, setForm] = useState(empty());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = async () => {
    const [d, p] = await Promise.all([
      api.get<Discount[]>("/platform/discounts"),
      api.get<PricingPlan[]>("/platform/pricing-plans?active_only=true").catch(
        () => api.get<PricingPlan[]>("/platform/pricing-plans")
      ),
    ]);
    setDiscounts(d);
    setPlans(p);
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditingId(null);
    const today = new Date().toISOString().slice(0, 10);
    setForm({ ...empty(), valid_from: today });
    setOpen(true);
  };

  const openEdit = (d: Discount) => {
    setEditingId(d.id);
    setForm({
      code: d.code,
      name: d.name,
      description: d.description ?? "",
      discount_type: d.discount_type,
      value:
        d.discount_type === "percent"
          ? String(d.value)
          : String((d.value / 100).toFixed(2)),
      valid_from: d.valid_from,
      valid_until: d.valid_until,
      pricing_plan_id: d.pricing_plan_id ?? "",
      is_active: d.is_active,
    });
    setOpen(true);
  };

  const toggleActive = async (d: Discount) => {
    try {
      await api.patch(`/platform/discounts/${d.id}`, { is_active: !d.is_active });
      toast.success(d.is_active ? "Descuento desactivado" : "Descuento activado");
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
      discount_type: form.discount_type,
      value:
        form.discount_type === "percent"
          ? parseInt(form.value, 10)
          : parseEurosToCents(form.value),
      valid_from: form.valid_from,
      valid_until: form.valid_until,
      pricing_plan_id: form.pricing_plan_id || null,
      is_active: form.is_active,
    };
    try {
      if (editingId) {
        await api.patch(`/platform/discounts/${editingId}`, body);
        toast.success("Descuento actualizado");
      } else {
        await api.post("/platform/discounts", body);
        toast.success("Descuento creado");
      }
      setOpen(false);
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const remove = async (d: Discount) => {
    if (!confirm(`¿Eliminar el descuento «${d.name}»?`)) return;
    try {
      await api.delete(`/platform/discounts/${d.id}`);
      toast.success("Descuento eliminado");
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const planName = (id: string | null) =>
    id ? plans.find((p) => p.id === id)?.name ?? "—" : "Todas las tarifas";

  type DiscountTableRow = Discount & {
    type_label: string;
    value_label: string;
    validity_label: string;
    plan_label: string;
    status_label: string;
  };

  const tableData = useMemo<DiscountTableRow[]>(
    () =>
      discounts.map((d) => ({
        ...d,
        type_label: d.discount_type === "percent" ? "%" : "Fijo",
        value_label: formatDiscountValue(d),
        validity_label: `${d.valid_from} → ${d.valid_until}`,
        plan_label: planName(d.pricing_plan_id),
        status_label: d.is_active ? "Activo" : "Inactivo",
      })),
    [discounts, plans]
  );

  const columns = useMemo(
    (): DataTableColumn<DiscountTableRow>[] => [
      {
        title: "Código",
        field: "code",
        headerFilter: "input",
        formatter: (c) => `<code>${String(c.getValue())}</code>`,
        width: 100,
      },
      { title: "Nombre", field: "name", headerFilter: "input", minWidth: 140 },
      {
        title: "Tipo",
        field: "type_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", "%": "%", Fijo: "Fijo" } as Record<string, string> },
        width: 80,
      },
      { title: "Valor", field: "value_label", headerFilter: "input", width: 90 },
      { title: "Vigencia", field: "validity_label", headerFilter: "input", minWidth: 180 },
      { title: "Tarifa", field: "plan_label", headerFilter: "input", minWidth: 120 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", Activo: "Activo", Inactivo: "Inactivo" } },
        formatter: (cell) => {
          const r = cell.getRow().getData() as DiscountTableRow;
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
        width: 220,
        formatter: () =>
          tableActionButtons([
            { id: "toggle", label: "Activar/Desactivar" },
            { id: "edit", label: "Editar" },
            { id: "delete", label: "Eliminar" },
          ]),
      },
    ],
    []
  );

  const onCellAction = (action: string, row: DiscountTableRow) => {
    if (action === "toggle") void toggleActive(row);
    if (action === "edit") openEdit(row);
    if (action === "delete") void remove(row);
  };

  return (
    <>
      <PageHeader
        title="Descuentos"
        subtitle="Porcentaje o importe fijo durante un periodo determinado"
        action={
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            + Nuevo descuento
          </button>
        }
      />

      <DataTable
        data={tableData}
        columns={columns}
        exportFilename="descuentos"
        onCellAction={onCellAction}
      />

      {open && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => e.target === e.currentTarget && setOpen(false)}
        >
          <div className="modal-panel">
            <h3>{editingId ? "Editar descuento" : "Nuevo descuento"}</h3>
            <form onSubmit={save} className="form-grid">
              <label>
                Código
                <input
                  required
                  disabled={!!editingId}
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
              <label>
                Tipo
                <select
                  value={form.discount_type}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      discount_type: e.target.value as "percent" | "fixed",
                    })
                  }
                >
                  <option value="percent">Porcentaje (%)</option>
                  <option value="fixed">Importe fijo (€)</option>
                </select>
              </label>
              <label>
                Valor
                <input
                  required
                  type="number"
                  min="0"
                  step={form.discount_type === "percent" ? "1" : "0.01"}
                  max={form.discount_type === "percent" ? "100" : undefined}
                  value={form.value}
                  onChange={(e) => setForm({ ...form, value: e.target.value })}
                />
              </label>
              <label>
                Desde
                <input
                  required
                  type="date"
                  value={form.valid_from}
                  onChange={(e) =>
                    setForm({ ...form, valid_from: e.target.value })
                  }
                />
              </label>
              <label>
                Hasta
                <input
                  required
                  type="date"
                  value={form.valid_until}
                  onChange={(e) =>
                    setForm({ ...form, valid_until: e.target.value })
                  }
                />
              </label>
              <label className="form-span-2">
                Aplica a tarifa
                <select
                  value={form.pricing_plan_id}
                  onChange={(e) =>
                    setForm({ ...form, pricing_plan_id: e.target.value })
                  }
                >
                  <option value="">Todas las tarifas</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-span-2 checkbox-row">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) =>
                    setForm({ ...form, is_active: e.target.checked })
                  }
                />
                Descuento activo
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
