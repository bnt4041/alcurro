const BASE = "/api";
const TOKEN_KEY = "hrm_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function buildQuery(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") q.set(k, v);
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const companyId = localStorage.getItem("hrm_company_id");
  if (companyId) headers["X-Company-Id"] = companyId;
  const workCenterId = localStorage.getItem("hrm_work_center_id");
  if (workCenterId) headers["X-Work-Center-Id"] = workCenterId;
  const departmentId = localStorage.getItem("hrm_department_id");
  if (departmentId) headers["X-Department-Id"] = departmentId;
  return headers;
}

const FIELD_LABELS: Record<string, string> = {
  slug: "Código de cuenta",
  name: "Nombre comercial",
  legal_name: "Razón social",
  tax_id: "CIF/NIF",
  billing_email: "Email de facturación",
  billing_phone: "Teléfono",
};

function formatValidationDetail(detail: unknown): string | null {
  if (!Array.isArray(detail)) return null;
  const lines = detail
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const e = item as { loc?: unknown[]; msg?: string };
      const key = Array.isArray(e.loc)
        ? String(e.loc[e.loc.length - 1] ?? "")
        : "";
      const label = FIELD_LABELS[key] ?? key;
      let msg = e.msg ?? "Valor no válido";
      if (msg.includes("string_pattern_mismatch") || key === "slug") {
        msg =
          "solo letras minúsculas, números y guiones (ej. jjac-es, no uses puntos ni dominios)";
      }
      return label ? `${label}: ${msg}` : msg;
    })
    .filter(Boolean);
  return lines.length ? lines.join(". ") : null;
}

function formatApiError(status: number, detail: unknown): string {
  const validation = formatValidationDetail(detail);
  if (validation) return validation;
  const text =
    typeof detail === "string"
      ? detail
      : detail != null
        ? JSON.stringify(detail)
        : "";
  if (status >= 500 && text && text !== "Internal Server Error") {
    return text;
  }
  if (
    status >= 500 &&
    (!text || text === "Internal Server Error" || text.includes("ECONNREFUSED"))
  ) {
    return "Error del servidor. Si acabas de actualizar, reinicia: docker compose restart backend";
  }
  return text || `Error ${status}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isForm = options.body instanceof FormData;
  const headers = authHeaders(
    isForm ? {} : { "Content-Type": "application/json", ...(options.headers as Record<string, string>) }
  );

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      "No se puede contactar con la API. Comprueba que backend y frontend están en marcha (docker compose up -d)."
    );
  }
  if (res.status === 401 && !path.includes("/auth/login")) {
    setToken(null);
    window.location.href = "/acceso";
    throw new Error("Sesión expirada");
  }
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail ?? err.message ?? res.statusText;
    throw new Error(formatApiError(res.status, detail));
  }
  return res.json().catch(() => {
    throw new Error("El servidor no responde correctamente. Comprueba que el backend esté en marcha.");
  }) as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  download: async (path: string, filename: string) => {
    const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
    if (res.status === 401) {
      setToken(null);
      window.location.href = "/acceso";
      throw new Error("Sesión expirada");
    }
    if (!res.ok) throw new Error(`No se pudo descargar (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
  upload: async <T>(path: string, form: FormData) => {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      body: form,
      headers: authHeaders(),
    });
    if (res.status === 401) {
      setToken(null);
      window.location.href = "/acceso";
      throw new Error("Sesión expirada");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? res.statusText);
    }
    return res.json() as Promise<T>;
  },
};
