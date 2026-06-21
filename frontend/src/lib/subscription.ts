export const SUBSCRIPTION_STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  trialing: "Prueba",
  cancelled: "Cancelada",
  past_due: "Impago",
};

export const PAYMENT_STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  succeeded: "Pagada",
  failed: "Fallida",
  refunded: "Reembolsada",
};

export interface SubscriptionSummary {
  id: string;
  plan_name: string;
  plan_code: string;
  status: string;
  amount_cents: number;
  currency: string;
  billing_cycle: string;
  company_name?: string | null;
  current_period_start?: string | null;
  current_period_end?: string | null;
  pending_plan_id?: string | null;
  pending_billing_cycle?: string | null;
}

export interface InvoiceRow {
  id: string;
  amount_cents: number;
  currency: string;
  status: string;
  description: string | null;
  stripe_invoice_id: string | null;
  invoice_number: string | null;
  invoice_pdf_url: string | null;
  invoice_url: string | null;
  paddle_receipt_url: string | null;
  paid_at: string | null;
  created_at: string;
}
