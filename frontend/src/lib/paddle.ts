// Carga e inicialización de Paddle.js (Billing) vía CDN.
// Evita añadir dependencias npm: se inyecta el script una sola vez.

const PADDLE_JS_URL = "https://cdn.paddle.com/paddle/v2/paddle.js";

interface PaddleCheckoutItem {
  priceId: string;
  quantity: number;
}

interface OpenCheckoutOptions {
  clientToken: string;
  env: string; // "sandbox" | "production"
  priceId: string;
  customData?: Record<string, string>;
  customerEmail?: string;
  discountCode?: string | null;
  successUrl?: string | null;
}

declare global {
  interface Window {
    Paddle?: {
      Environment: { set: (env: string) => void };
      Initialize: (opts: { token: string }) => void;
      Checkout: { open: (opts: Record<string, unknown>) => void };
    };
  }
}

let scriptPromise: Promise<void> | null = null;
let initializedToken: string | null = null;

function loadScript(): Promise<void> {
  if (window.Paddle) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${PADDLE_JS_URL}"]`
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("No se pudo cargar Paddle.js")));
      return;
    }
    const script = document.createElement("script");
    script.src = PADDLE_JS_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("No se pudo cargar Paddle.js"));
    document.head.appendChild(script);
  });
  return scriptPromise;
}

/** Abre el overlay de checkout de Paddle para una suscripción. */
export async function openPaddleCheckout(opts: OpenCheckoutOptions): Promise<void> {
  await loadScript();
  const paddle = window.Paddle;
  if (!paddle) throw new Error("Paddle.js no disponible");

  if (initializedToken !== opts.clientToken) {
    paddle.Environment.set(opts.env === "production" ? "production" : "sandbox");
    paddle.Initialize({ token: opts.clientToken });
    initializedToken = opts.clientToken;
  }

  const checkout: Record<string, unknown> = {
    items: [{ priceId: opts.priceId, quantity: 1 } as PaddleCheckoutItem],
    settings: {
      displayMode: "overlay",
      ...(opts.successUrl ? { successUrl: opts.successUrl } : {}),
    },
  };
  if (opts.customData) checkout.customData = opts.customData;
  if (opts.customerEmail) checkout.customer = { email: opts.customerEmail };
  if (opts.discountCode) checkout.discountCode = opts.discountCode;

  paddle.Checkout.open(checkout);
}
