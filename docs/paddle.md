# Paddle — Integración de pagos

Alcurro usa **Paddle (Billing API v2)** como proveedor de suscripciones. El checkout se
realiza en el navegador con **Paddle.js (overlay)**; el backend da de alta productos/precios,
gestiona suscripciones por API y procesa los webhooks. Stripe se mantiene como alternativa
(modo simulación por defecto).

---

## Variables de entorno

```env
PADDLE_ENV=sandbox                       # "sandbox" | "production"
PADDLE_API_KEY=pdl_sdbx_apikey_...        # clave server-side (Paddle → Authentication → API keys)
PADDLE_CLIENT_TOKEN=test_...              # token client-side para Paddle.js (Authentication → client-side tokens)
PADDLE_WEBHOOK_SECRET=pdl_ntfset_...      # secret del destino de notificaciones (Notifications)
```

La base de la API se deriva de `PADDLE_ENV`:
- `sandbox` → `https://sandbox-api.paddle.com`
- `production` → `https://api.paddle.com`

Añadir al `.env` y reiniciar el backend:

```bash
docker compose up -d --force-recreate backend
```

---

## Campos en base de datos

### `pricing_plans`

| Campo | Descripción |
|---|---|
| `paddle_product_id` | ID del producto en Paddle (`pro_…`) |
| `paddle_price_id_monthly` | ID del precio mensual (`pri_…`) |
| `paddle_price_id_annual` | ID del precio anual (`pri_…`) |

### `subscriptions`

| Campo | Descripción |
|---|---|
| `paddle_subscription_id` | ID de la suscripción en Paddle (`sub_…`) |
| `payment_failure_count` | Contador de cobros fallidos consecutivos |
| `last_payment_failure_at` | Último fallo de cobro |

### `discounts`

| Campo | Descripción |
|---|---|
| `paddle_discount_id` | ID del descuento en Paddle (`dsc_…`) |

### `tenants`

| Campo | Descripción |
|---|---|
| `paddle_customer_id` | ID de cliente en Paddle (`ctm_…`) |
| `paddle_customer_portal_url` | URL del portal de cliente (sesión generada al crear la suscripción) |

### `paddle_payments`

Tabla de registro de pagos (análoga a `stripe_payments`):

| Campo | Descripción |
|---|---|
| `paddle_transaction_id` | ID de la transacción (`txn_…`) — deduplica webhooks |
| `paddle_subscription_id` | ID de la suscripción Paddle |
| `paddle_invoice_id` | ID/numeración de factura asociada |
| `amount_cents` | Importe en céntimos |
| `currency` | Moneda (p. ej. `EUR`) |
| `status` | `paid` / `failed` / `refunded` / `pending` |
| `description` | Texto libre |
| `receipt_url` | URL de la factura PDF (transaction invoice) |
| `paid_at` | Timestamp del pago |

---

## Sincronización de planes

Antes de que un cliente pueda suscribirse, cada plan debe tener producto y precios en Paddle:

```
Admin → /admin/tarifas → [Editar plan] → botón "Sync Paddle"
  → POST /api/platform/paddle/sync-plan/{plan_id}
      → paddle_service.sync_plan_to_paddle()
           1. Crea Product (solo si paddle_product_id vacío)
           2. Crea Price mensual (si paddle_price_id_monthly vacío)
           3. Crea Price anual (si paddle_price_id_annual vacío)
           4. Guarda IDs en pricing_plans
```

La función es idempotente: si algún campo ya existe, no vuelve a crear el recurso en Paddle.
También se pueden pegar manualmente los Price IDs (`pri_…`) en el formulario de la tarifa.

---

## Flujo de alta (checkout overlay)

```
POST /api/public/signup
  → signup_service.initiate_signup()
       ├── Crea PendingSignup (estado PENDING)
       └── Devuelve parámetros del overlay:
             paddle_price_id, paddle_client_token, paddle_env,
             paddle_discount_code, customer_email, success_url,
             pending_signup_id

  → Frontend (SignupPage) → lib/paddle.ts → Paddle.Checkout.open({
        items: [{ priceId, quantity: 1 }],
        customData: { pending_signup_id },
        customer: { email },
        discountCode,
        settings: { displayMode: "overlay", successUrl }
     })

  → Cliente paga en el overlay
  → Webhook subscription.created → crea el tenant desde el PendingSignup
  → Paddle redirige a success_url (/registro/ok?pending=…)
  → La página de éxito hace polling de /public/pending-signup/{id}
```

El `customData.pending_signup_id` viaja con la suscripción y la transacción, permitiendo
identificar el alta en los webhooks sin depender del email.

---

## Webhook

### Configurar en Paddle

1. Panel Paddle → **Developer Tools → Notifications → New destination**
2. URL: `https://alcurro.es/api/webhooks/paddle`
3. Al guardar, Paddle genera el **secret** → guardar en `PADDLE_WEBHOOK_SECRET`
4. Eventos a activar:
   - `subscription.created`
   - `subscription.updated`
   - `subscription.canceled`
   - `transaction.completed`
   - `transaction.payment_failed`
   - `adjustment.created`

### Verificación de firma

```python
# paddle_service.verify_webhook_signature(body, signature_header)
# Cabecera Paddle-Signature: "ts=...;h1=..."
expected = hmac.new(secret, f"{ts}:".encode() + body, sha256).hexdigest()
hmac.compare_digest(expected, h1)
```

### Handlers de eventos

| Evento Paddle | Acción en alcurro |
|---|---|
| `subscription.created` | Crea tenant (PendingSignup) o activa suscripción; guarda `paddle_subscription_id`, `paddle_customer_id`, `paddle_customer_portal_url` |
| `subscription.updated` | Sincroniza estado, fecha de renovación y cambio de precio/plan |
| `subscription.canceled` / `subscription.paused` | Marca suscripción como `CANCELLED` |
| `transaction.completed` | `payment_failure_count=0`, genera `PaddlePayment` PAID, factura PDF, notifica email + WA |
| `transaction.payment_failed` | Incrementa `payment_failure_count`; si ≥3 suspende cuenta (`is_active=False`) y notifica |
| `adjustment.created` (action=refund) | Marca el pago como `REFUNDED` y genera la factura rectificativa |

---

## Descuentos

Los descuentos de Alcurro (`discounts`) se sincronizan a Paddle con `sync_discount_to_paddle()`
(crea/actualiza un `dsc_…`). En el checkout se pasan vía `discountCode`. Para una suscripción
existente se aplican con `apply_paddle_discount_to_subscription()`
(`PATCH /subscriptions/{id}` con `discount.effective_from = next_billing_period`).

---

## Reembolsos

`POST /api/platform/paddle/refund/{payment_id}` → `issue_refund_credit_note()`:
1. Crea un `adjustment` (`action: refund`, `type: full`) sobre la transacción en Paddle.
2. Marca el `PaddlePayment` como `REFUNDED`.
3. Genera la factura rectificativa (abono) en Alcurro.

El webhook `adjustment.created` también puede disparar el abono si el reembolso se hace
desde el panel de Paddle.

---

## Notificaciones automáticas de pago

| Evento | Email | WhatsApp |
|---|---|---|
| Pago exitoso | Confirmación + link factura | ✅ Si hay `billing_phone` |
| Pago fallido (1–2 intentos) | Alerta con intentos restantes | ✅ |
| Pago fallido (3er intento) | Cuenta suspendida | ✅ |

Los datos de contacto vienen de `tenant.billing_email` y `tenant.billing_phone`.

---

## Referencia de endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/public/paddle-config` | Config pública (enabled, client_token, env) |
| `POST` | `/api/platform/paddle/sync-plan/{plan_id}` | Sincronizar plan con Paddle |
| `GET` | `/api/platform/paddle/status` | Estado de la integración |
| `GET` | `/api/platform/paddle/payments` | Historial de pagos |
| `POST` | `/api/platform/paddle/refund/{payment_id}` | Reembolso + factura rectificativa |
| `POST` | `/api/webhooks/paddle` | Webhook Paddle (firma HMAC-SHA256) |

---

## Archivos principales

```
backend/app/services/paddle_service.py     # Toda la lógica Paddle
backend/app/models/billing.py              # PaddlePayment, PricingPlan (campos paddle_*)
backend/app/models/tenant.py               # Tenant (paddle_customer_id, paddle_customer_portal_url)
backend/app/routers/platform_paddle.py     # Endpoints admin Paddle
backend/app/routers/paddle_webhook.py      # POST /webhooks/paddle
backend/scripts/migrate_paddle_v1.py       # Migración rename ls_* → paddle_*
frontend/src/lib/paddle.ts                 # Carga Paddle.js + openPaddleCheckout()
frontend/src/pages/SignupPage.tsx          # Abre el overlay de checkout
frontend/src/pages/PlatformPaddlePage.tsx  # Vista de cobros + estado
frontend/src/pages/PlatformPricingPage.tsx # Botón "Sync Paddle" por plan
```

---

## Migración desde Lemon Squeezy

La integración anterior (Lemon Squeezy) fue reemplazada por completo. El script
`migrate_paddle_v1.py` renombra de forma idempotente todos los campos/tablas `ls_*` a
`paddle_*` (incluida la tabla `ls_payments` → `paddle_payments`). Se conserva un snapshot
previo en el tag git `pre-paddle-migration` y en `backups/`.
```

> Nota: `create_all()` corre antes que las migraciones, así que en una BD con datos puede
> crear una tabla `paddle_payments` vacía junto a la `ls_payments` real; el script descarta
> la vacía y renombra la real conservando el histórico.
