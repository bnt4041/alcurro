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
  paddle_payment_id: string | null;
  paddle_invoice_ref: string | null;
  paddle_receipt_url: string | null;
  credit_note_for_id: string | null;
  created_at: string;
}

interface InvoiceDetail extends Invoice {
  recipient_legal_name: string | null;
  recipient_tax_id: string | null;
  recipient_address: string | null;
  recipient_city: string | null;
  recipient_postal_code: string | null;
  recipient_province: string | null;
  recipient_country: string;
  recipient_email: string | null;
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

  // Modal editar factura
  const [editOpen, setEditOpen] = useState(false);
  const [editInvoice, setEditInvoice] = useState<InvoiceDetail | null>(null);
  const [editData, setEditData] = useState<Partial<InvoiceDetail>>({});
  const [saving, setSaving] = useState(false);

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

  const handleSaveEdit = async () => {
    if (!editInvoice) return;
    setSaving(true);
    try {
      await api.patch(`/platform/invoices/${editInvoice.id}`, editData);
      notify("Factura actualizada", "success");
      setEditOpen(false);
      load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setSaving(false);
    }
  };

  const handleAction = async (action: string, row: TableRow) => {
    if (action === "edit") {
      try {
        const detail = await api.get<InvoiceDetail>(`/platform/invoices/${row.id}`);
        setEditInvoice(detail);
        setEditData({
          concept: detail.concept,
          due_date: detail.due_date,
          recipient_legal_name: detail.recipient_legal_name,
          recipient_tax_id: detail.recipient_tax_id,
          recipient_address: detail.recipient_address,
          recipient_city: detail.recipient_city,
          recipient_postal_code: detail.recipient_postal_code,
          recipient_province: detail.recipient_province,
          recipient_country: detail.recipient_country,
          recipient_email: detail.recipient_email,
        });
        setEditOpen(true);
      } catch (err) {
        notify(String(err).replace(/^Error:\s*/i, ""), "error");
      }
      return;
    }
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
      } else if (action === "paddle-refund") {
        if (!confirm(`¿Emitir abono de ${row.number}?\n\nSe realizará el reembolso monetario en Paddle y se generará la factura rectificativa en Alcurro.`)) return;
        const res = await api.post<{ credit_note_number: string }>(`/platform/paddle/refund/${row.paddle_payment_id}`, {});
        notify(`Abono ${res.credit_note_number} generado correctamente`, "success");
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
        width: 220,
        formatter: (cell) => {
          const r = cell.getRow().getData() as TableRow;
          let badges = "";
          if (r.paddle_receipt_url) {
            badges += `<a href="${r.paddle_receipt_url}" target="_blank" rel="noopener" class="badge badge--info" title="Ver factura en Paddle">Paddle ${r.paddle_invoice_ref ?? "factura"}</a> `;
          } else if (r.paddle_invoice_ref) {
            badges += `<span class="badge badge--info" title="Referencia Paddle: ${r.paddle_invoice_ref}">Paddle ${r.paddle_invoice_ref}</span> `;
          } else if (r.paddle_payment_id) {
            badges += `<span class="badge badge--info" title="Vinculada a cobro Paddle">Paddle</span> `;
          }
          if (r.credit_note_for_id) badges += `<span class="badge badge--warning" title="Rectificativa">ABONO</span> `;
          return `${badges}<span class="mono small">${r.number}</span>`;
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
        width: 300,
        formatter: (cell) => {
          const r = cell.getRow().getData() as TableRow;
          const cancelled = r.status === "cancelled" || r.status === "credit_note";
          const lsAbono = !cancelled && r.paddle_payment_id
            ? `<button class="btn btn-xs btn-warning" data-action="paddle-refund" title="Reembolso en Paddle + factura rectificativa">Abono Paddle</button>`
            : (!cancelled ? `<button class="btn btn-xs btn-warning" data-action="credit" title="Factura rectificativa">Abono</button>` : "");
          return `
            <div class="table-actions">
              <button class="btn btn-xs" data-action="pdf" title="Descargar PDF">PDF</button>
              <button class="btn btn-xs" data-action="edit" title="Editar datos de factura">Editar</button>
              <button class="btn btn-xs" data-action="email" title="Enviar por email" ${cancelled ? "disabled" : ""}>Email</button>
              ${lsAbono}
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
        title={`Editar factura ${editInvoice?.number ?? ""}`}
        open={editOpen}
        onClose={() => setEditOpen(false)}
      >
        {editInvoice && (
          <div className="form-grid">
            <label>
              Concepto
              <input
                value={editData.concept ?? ""}
                onChange={(e) => setEditData({ ...editData, concept: e.target.value })}
              />
            </label>
            <label>
              Fecha de vencimiento
              <input
                type="date"
                value={editData.due_date ?? ""}
                onChange={(e) => setEditData({ ...editData, due_date: e.target.value || null })}
              />
            </label>
            <label>
              Razón social del cliente
              <input
                value={editData.recipient_legal_name ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_legal_name: e.target.value || null })}
              />
            </label>
            <label>
              NIF / CIF del cliente
              <input
                value={editData.recipient_tax_id ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_tax_id: e.target.value || null })}
              />
            </label>
            <label>
              Email del cliente
              <input
                type="email"
                value={editData.recipient_email ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_email: e.target.value || null })}
              />
            </label>
            <label>
              Dirección
              <input
                value={editData.recipient_address ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_address: e.target.value || null })}
              />
            </label>
            <label>
              Ciudad
              <input
                value={editData.recipient_city ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_city: e.target.value || null })}
              />
            </label>
            <label>
              Código postal
              <input
                value={editData.recipient_postal_code ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_postal_code: e.target.value || null })}
              />
            </label>
            <label>
              Provincia
              <input
                value={editData.recipient_province ?? ""}
                onChange={(e) => setEditData({ ...editData, recipient_province: e.target.value || null })}
              />
            </label>
            <label>
              País
              <input
                value={editData.recipient_country ?? "ES"}
                onChange={(e) => setEditData({ ...editData, recipient_country: e.target.value })}
              />
            </label>
          </div>
        )}
        <div className="form-actions" style={{ marginTop: "1.5rem" }}>
          <button type="button" className="btn" onClick={() => setEditOpen(false)}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={saving}
            onClick={handleSaveEdit}
          >
            {saving ? "Guardando…" : "Guardar cambios"}
          </button>
        </div>
      </Modal>

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
