import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import { formatMoney } from "../lib/money";

interface Invoice {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  number: string;
  concept: string;
  base_cents: number;
  vat_rate: number;
  vat_cents: number;
  total_cents: number;
  currency: string;
  issue_date: string;
  due_date: string | null;
  status: string;
  pdf_url: string | null;
  email_sent_at: string | null;
  stripe_payment_id: string | null;
  credit_note_for_id: string | null;
  created_at: string;
}

interface Tenant {
  id: string;
  name: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Borrador",
  sent: "Enviada",
  paid: "Pagada",
  cancelled: "Anulada",
  credit_note: "Rectificativa",
};

const STATUS_CLASS: Record<string, string> = {
  draft: "",
  sent: "badge--info",
  paid: "badge--ok",
  cancelled: "badge--danger",
  credit_note: "badge--warning",
};

type TableRow = Invoice & {
  date_label: string;
  status_label: string;
  total_label: string;
  tenant_label: string;
};

export default function PlatformInvoicesPage() {
  const { notify } = useToast();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterTenant, setFilterTenant] = useState("");

  // Modal crear factura manual
  const [createOpen, setCreateOpen] = useState(false);
  const [createData, setCreateData] = useState({
    tenant_id: "",
    concept: "Suscripción alcurro",
    total_cents: 0,
    currency: "EUR",
  });
  const [creating, setCreating] = useState(false);

  // Acción en curso
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [invData, tenantData] = await Promise.all([
        api.get<Invoice[]>(`/platform/invoices${filterTenant ? `?tenant_id=${filterTenant}` : ""}`),
        api.get<Tenant[]>("/platform/tenants"),
      ]);
      setInvoices(invData);
      setTenants(tenantData);
    } finally {
      setLoading(false);
    }
  }, [filterTenant]);

  useEffect(() => {
    load();
  }, [load]);

  const tableData = useMemo<TableRow[]>(
    () =>
      invoices.map((inv) => ({
        ...inv,
        date_label: new Date(inv.issue_date).toLocaleDateString("es-ES"),
        status_label: STATUS_LABELS[inv.status] ?? inv.status,
        total_label: formatMoney(inv.total_cents, inv.currency),
        tenant_label: inv.tenant_name ?? inv.tenant_id,
      })),
    [invoices]
  );

  const handleAction = async (action: string, row: TableRow) => {
    setActionLoading(row.id + action);
    try {
      if (action === "pdf") {
        await api.download(`/platform/invoices/${row.id}/pdf`, `${row.number.replace(/\//g, "-")}.pdf`);
      } else if (action === "email") {
        await api.post(`/platform/invoices/${row.id}/send-email`, {});
        notify(`Factura ${row.number} enviada por email`, "success");
        load();
      } else if (action === "credit") {
        if (!confirm(`¿Crear factura rectificativa de ${row.number}?`)) return;
        await api.post(`/platform/invoices/${row.id}/credit-note`, {});
        notify("Factura rectificativa creada", "success");
        load();
      } else if (action === "cancel") {
        if (!confirm(`¿Anular la factura ${row.number}?`)) return;
        await api.patch(`/platform/invoices/${row.id}/status`, { status: "cancelled" });
        notify("Factura anulada", "success");
        load();
      }
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setActionLoading(null);
    }
  };

  const columns = useMemo<DataTableColumn<TableRow>[]>(
    () => [
      {
        title: "Número",
        field: "number",
        headerFilter: "input",
        width: 150,
        formatter: (cell) => {
          const r = cell.getRow().getData() as TableRow;
          return `<span class="mono small">${r.number}</span>`;
        },
      },
      {
        title: "Fecha",
        field: "date_label",
        headerFilter: "input",
        width: 100,
      },
      {
        title: "Cliente",
        field: "tenant_label",
        headerFilter: "input",
        minWidth: 140,
      },
      {
        title: "Concepto",
        field: "concept",
        headerFilter: "input",
        minWidth: 180,
      },
      {
        title: "Total",
        field: "total_label",
        headerFilter: "input",
        width: 110,
      },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", ...Object.fromEntries(Object.entries(STATUS_LABELS).map(([, v]) => [v, v])) },
        },
        formatter: (cell) => {
          const r = cell.getRow().getData() as TableRow;
          return `<span class="badge ${STATUS_CLASS[r.status] ?? ""}">${r.status_label}</span>`;
        },
        width: 110,
      },
      {
        title: "Email",
        field: "email_sent_at",
        width: 80,
        formatter: (cell) => {
          const r = cell.getRow().getData() as TableRow;
          return r.email_sent_at
            ? `<span class="badge badge--ok" title="${new Date(r.email_sent_at).toLocaleString("es-ES")}">✓</span>`
            : `<span class="muted small">—</span>`;
        },
      },
      {
        title: "Acciones",
        field: "id",
        width: 200,
        formatter: (cell) => {
          const r = cell.getRow().getData() as TableRow;
          const cancelled = r.status === "cancelled" || r.status === "credit_note";
          return `
            <div class="table-actions">
              <button class="btn btn-xs" data-action="pdf" title="Descargar PDF">PDF</button>
              <button class="btn btn-xs" data-action="email" title="Enviar por email" ${cancelled ? "disabled" : ""}>Email</button>
              ${!cancelled ? `<button class="btn btn-xs btn-warning" data-action="credit" title="Factura rectificativa">Abono</button>` : ""}
              ${r.status !== "cancelled" && r.status !== "credit_note" ? `<button class="btn btn-xs btn-danger" data-action="cancel" title="Anular factura">Anular</button>` : ""}
            </div>
          `;
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [actionLoading]
  );

  const handleCreate = async () => {
    if (!createData.tenant_id || !createData.concept || !createData.total_cents) {
      notify("Completa todos los campos requeridos", "error");
      return;
    }
    setCreating(true);
    try {
      await api.post("/platform/invoices", {
        ...createData,
        total_cents: Math.round(createData.total_cents * 100),
      });
      notify("Factura creada correctamente", "success");
      setCreateOpen(false);
      setCreateData({ tenant_id: "", concept: "Suscripción alcurro", total_cents: 0, currency: "EUR" });
      load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Facturas"
        subtitle="Gestión de facturas emitidas a clientes"
        action={
          <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
            Nueva factura
          </button>
        }
      />

      <section className="card settings-section">
        <div className="toolbar" style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span className="muted small">Filtrar por cliente:</span>
            <select
              value={filterTenant}
              onChange={(e) => setFilterTenant(e.target.value)}
              style={{ minWidth: 200 }}
            >
              <option value="">Todos los clientes</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </label>
          <button type="button" className="btn btn-sm" onClick={load} disabled={loading}>
            {loading ? "Cargando…" : "Actualizar"}
          </button>
        </div>

        <DataTable
          data={tableData}
          columns={columns}
          loading={loading}
          exportFilename="facturas-alcurro"
          height="calc(100vh - 320px)"
          emptyMessage="No hay facturas registradas"
          onCellAction={(action, row) => handleAction(action, row as TableRow)}
        />
      </section>

      <Modal
        title="Nueva factura manual"
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      >
        <div className="form-grid">
          <label>
            Cliente <span className="required">*</span>
            <select
              value={createData.tenant_id}
              onChange={(e) => setCreateData({ ...createData, tenant_id: e.target.value })}
              required
            >
              <option value="">Selecciona un cliente…</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </label>
          <label>
            Concepto <span className="required">*</span>
            <input
              required
              value={createData.concept}
              onChange={(e) => setCreateData({ ...createData, concept: e.target.value })}
            />
          </label>
          <label>
            Importe total con IVA (€) <span className="required">*</span>
            <input
              type="number"
              min={0}
              step={0.01}
              required
              value={createData.total_cents || ""}
              onChange={(e) => setCreateData({ ...createData, total_cents: parseFloat(e.target.value) || 0 })}
              placeholder="18.00"
            />
          </label>
          <label>
            Moneda
            <select
              value={createData.currency}
              onChange={(e) => setCreateData({ ...createData, currency: e.target.value })}
            >
              <option value="EUR">EUR — Euro</option>
              <option value="USD">USD — Dólar</option>
            </select>
          </label>
        </div>
        <p className="muted small" style={{ marginTop: "0.5rem" }}>
          El IVA se calculará automáticamente según la configuración de plataforma (por defecto 21%).
        </p>
        <div className="form-actions" style={{ marginTop: "1.5rem" }}>
          <button type="button" className="btn" onClick={() => setCreateOpen(false)}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={creating}
            onClick={handleCreate}
          >
            {creating ? "Creando…" : "Crear factura"}
          </button>
        </div>
      </Modal>
    </>
  );
}
