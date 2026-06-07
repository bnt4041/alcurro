import { useMemo } from "react";
import DataTable, { type DataTableColumn } from "./DataTable";
import { formatMoney } from "../lib/money";
import type { InvoiceRow } from "../lib/subscription";
import { PAYMENT_STATUS_LABELS } from "../lib/subscription";

interface Props {
  invoices: InvoiceRow[];
  loading?: boolean;
}

type InvoiceTableRow = InvoiceRow & {
  date_label: string;
  status_label: string;
  amount_label: string;
};

export default function InvoiceHistoryTable({ invoices, loading }: Props) {
  const tableData = useMemo<InvoiceTableRow[]>(
    () =>
      invoices.map((inv) => ({
        ...inv,
        date_label: new Date(inv.paid_at ?? inv.created_at).toLocaleDateString("es-ES"),
        status_label: PAYMENT_STATUS_LABELS[inv.status] ?? inv.status,
        amount_label: formatMoney(inv.amount_cents, inv.currency),
      })),
    [invoices]
  );

  const columns = useMemo<DataTableColumn<InvoiceTableRow>[]>(
    () => [
      { title: "Fecha", field: "date_label", headerFilter: "input", width: 110 },
      {
        title: "Factura",
        field: "invoice_number",
        headerFilter: "input",
        formatter: (cell) => {
          const r = cell.getRow().getData() as InvoiceTableRow;
          const label = r.invoice_number || r.stripe_invoice_id || "—";
          const pdfUrl = r.invoice_pdf_url || r.invoice_url;
          if (pdfUrl) {
            return `<a href="${pdfUrl}" target="_blank" rel="noopener" class="invoice-pdf-link" title="Ver / descargar factura PDF">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              ${label}
            </a>`;
          }
          return `<span class="mono small">${label}</span>`;
        },
        minWidth: 150,
      },
      {
        title: "Concepto",
        field: "description",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "Suscripción alcurro"),
        minWidth: 160,
      },
      { title: "Importe", field: "amount_label", headerFilter: "input", width: 110 },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: {
          values: { "": "Todos", ...Object.fromEntries(Object.entries(PAYMENT_STATUS_LABELS).map(([, v]) => [v, v])) },
        },
        formatter: (cell) => {
          const r = cell.getRow().getData() as InvoiceTableRow;
          const cls =
            r.status === "succeeded"
              ? "badge--ok"
              : r.status === "failed"
                ? "badge--danger"
                : "";
          return `<span class="badge ${cls}">${r.status_label}</span>`;
        },
        width: 120,
      },
    ],
    []
  );

  if (!loading && invoices.length === 0) {
    return (
      <p className="muted small">
        Aún no hay facturas registradas para esta cuenta.
      </p>
    );
  }

  return (
    <DataTable
      data={tableData}
      columns={columns}
      loading={loading}
      exportFilename="facturas"
      height="360px"
      emptyMessage="Sin facturas"
    />
  );
}
