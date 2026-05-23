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
  annual_price_per_month_cents: number;
  max_active_users: number;
  currency: string;
}

export interface PublicStripeConfig {
  enabled: boolean;
  publishable_key: string | null;
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
  tenant_id: string;
  tenant_slug: string;
  company_name: string;
  checkout_url: string | null;
  stripe_enabled: boolean;
  admin_login_hint: string;
}

export const publicApi = {
  getPlans: () => publicRequest<PublicPricingPlan[]>("/pricing-plans"),
  getStripeConfig: () => publicRequest<PublicStripeConfig>("/stripe-config"),
  signup: (body: PublicSignupBody) =>
    publicRequest<PublicSignupResponse>("/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
