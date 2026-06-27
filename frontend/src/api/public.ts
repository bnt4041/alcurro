const BASE = "/api/public";

async function publicRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      "No se puede contactar con la API. Comprueba que el backend está en marcha."
    );
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail ?? res.statusText;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(". ")
          : JSON.stringify(detail);
    throw new Error(msg || `Error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface PublicPricingPlan {
  id: string;
  code: string;
  name: string;
  description: string | null;
  monthly_price_cents: number;
  annual_price_cents: number;
  max_active_users: number;
  currency: string;
}

export interface PublicSignupBody {
  company_name: string;
  legal_name: string;
  tax_id: string;
  billing_email: string;
  billing_phone: string;
  billing_address?: string;
  billing_city?: string;
  billing_postal_code?: string;
  billing_province?: string;
  billing_country?: string;
  account_code?: string;
  pricing_plan_id: string;
  billing_cycle: "monthly" | "annual";
  discount_code?: string;
  admin_name: string;
  admin_email: string;
  admin_phone: string;
  admin_password: string;
  accept_terms: boolean;
}

export interface PublicSignupResponse {
  tenant_id: string | null;
  tenant_slug: string | null;
  company_name: string | null;
  checkout_url: string | null;
  admin_login_hint: string | null;
  pending_signup_id: string | null;
  // Parámetros para el overlay de Paddle.js (cuando hay que pagar)
  paddle_price_id: string | null;
  paddle_client_token: string | null;
  paddle_env: string | null;
  paddle_discount_code: string | null;
  customer_email: string | null;
  success_url: string | null;
}

export interface PendingSignupStatus {
  status: "pending" | "active" | "failed";
  tenant_slug: string | null;
  admin_login_hint: string | null;
  error_message: string | null;
}

export interface PublicDiscountPreview {
  valid: boolean;
  discount_code: string;
  discount_type: "percent" | "fixed";
  discount_value: number;
  base_amount_cents: number;
  final_amount_cents: number;
  currency: string;
}

export const publicApi = {
  getPlans: () => publicRequest<PublicPricingPlan[]>("/pricing-plans"),
  signup: (body: PublicSignupBody) =>
    publicRequest<PublicSignupResponse>("/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  discountPreview: (planId: string, cycle: string, code: string) =>
    publicRequest<PublicDiscountPreview>(
      `/discount-preview?plan_id=${planId}&billing_cycle=${cycle}&code=${encodeURIComponent(code)}`
    ),
  getPendingSignup: (id: string) =>
    publicRequest<PendingSignupStatus>(`/pending-signup/${id}`),
  getSiteConfig: () =>
    publicRequest<{ whatsapp_number: string | null }>("/site-config"),
};
