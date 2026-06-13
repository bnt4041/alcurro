# Lemon Squeezy — Integración de pagos

Alcurro usa Lemon Squeezy como proveedor principal de suscripciones. Stripe se mantiene como alternativa (modo simulación por defecto).

---

## Variables de entorno

```env
LEMON_SQUEEZY_API_KEY=live_...         # clave API (panel LS → Settings → API)
LEMON_SQUEEZY_STORE_ID=12345           # ID de la tienda (panel LS → Stores)
LEMON_SQUEEZY_WEBHOOK_SECRET=whsec_... # secret para verificar firma de webhooks
```

Añadir al `.env` y reiniciar el backend:

```bash
docker compose up -d --force-recreate backend
```

---

## Campos en base de datos

### `pricing_plans`

| Campo | Tipo | Descripción |
|---|---|---|
| `ls_product_id` | `VARCHAR` | ID del producto en LS |
| `ls_variant_id_monthly` | `VARCHAR` | ID de la variante mensual |
| `ls_variant_id_annual` | `VARCHAR` | ID de la variante anual |

### `subscriptions`

| Campo | Tipo | Descripción |
|---|---|---|
| `ls_subscription_id` | `VARCHAR` | ID de la suscripción en LS |
| `payment_failure_count` | `INT` | Contador de cobros fallidos consecutivos |
| `last_payment_failure_at` | `TIMESTAMP` | Último fallo de cobro |

### `tenants`

| Campo | Tipo | Descripción |
|---|---|---|
| `ls_customer_id` | `VARCHAR` | ID de cliente en LS |
| `ls_customer_portal_url` | `VARCHAR` | URL del portal de cliente (actualizada por webhook) |

### `lemon_squeezy_payments`

Tabla de registro de pagos LS (análoga a `stripe_payments`):

| Campo | Descripción |
|---|---|
| `ls_invoice_id` | ID de la factura en LS (deduplica webhooks) |
| `ls_subscription_id` | ID de la suscripción LS |
| `ls_order_id` | ID del pedido LS |
| `amount_cents` | Importe en céntimos |
| `currency` | Moneda (p. ej. `EUR`) |
| `status` | `paid` / `failed` / `refunded` |
| `description` | Texto libre |
| `receipt_url` | URL de la factura LS |
| `paid_at` | Timestamp del pago |

---

## Sincronización de planes

Antes de que un cliente pueda suscribirse, cada plan debe estar sincronizado con Lemon Squeezy:

```
Admin → /admin/tarifas → [botón "Sync LS" en el plan]
  → POST /api/platform/ls/sync-plan/{plan_id}
      → lemon_squeezy_service.sync_plan_to_ls()
           1. Crea Product en LS (solo si ls_product_id vacío)
           2. Crea Variant mensual (si ls_variant_id_monthly vacío)
           3. Crea Variant anual (si ls_variant_id_annual vacío)
           4. Guarda IDs en pricing_plans
```

La función es idempotente: si algún campo ya existe, no vuelve a crear el recurso en LS.

---

## Flujo de alta (checkout)

```
POST /api/public/signup
  → signup_service.create_checkout_with_ls()
       │
       ├── Calcular precio con descuento si aplica
       │     (custom_price_cents si hay descuento activo)
       │
       └── lemon_squeezy_service.create_checkout(
               tenant, subscription, variant_id,
               customer_email, success_url,
               custom_price_cents=...
           )
           → POST https://api.lemonsqueezy.com/v1/checkouts
               checkout_data.custom = {
                 tenant_id: "...",
                 subscription_id: "..."
               }
           ← URL de checkout de LS

  → Redirige al navegador → checkout LS
  → Cliente paga
  → Webhook subscription_created → activa tenant
  → Redirige a /registro/ok
```

Los `custom_data` (`tenant_id`, `subscription_id`) se envían en el checkout y llegan de vuelta en todos los webhooks, permitiendo identificar el tenant y la suscripción sin depender del email.

---

## Webhook

### Configurar en Lemon Squeezy

1. Panel LS → **Settings → Webhooks → Add webhook**
2. URL: `https://alcurro.es/api/webhooks/lemon-squeezy`
3. Secret: cualquier cadena segura → guardar en `LEMON_SQUEEZY_WEBHOOK_SECRET`
4. Eventos a activar:
   - `subscription_created`
   - `subscription_updated`
   - `subscription_cancelled`
   - `subscription_expired`
   - `subscription_payment_success`
   - `subscription_payment_failed`
   - `subscription_payment_recovered`

### Verificación de firma

```python
# lemon_squeezy_service.verify_webhook_signature(body, signature)
expected = hmac.new(secret.encode(), body, sha256).hexdigest()
hmac.compare_digest(expected, signature_from_header)
```

La cabecera se llama `X-Signature`.

### Handlers de eventos

| Evento LS | Acción en alcurro |
|---|---|
| `subscription_created` | Activa suscripción, guarda `ls_subscription_id`, `ls_customer_id`, `ls_customer_portal_url` |
| `subscription_updated` | Sincroniza estado y fecha de renovación |
| `subscription_cancelled` / `subscription_expired` | Marca suscripción como `CANCELLED` |
| `subscription_payment_success` | `payment_failure_count=0`, genera `LemonSqueezyPayment` PAID, genera factura PDF, notifica por email + WA |
| `subscription_payment_failed` | Incrementa `payment_failure_count`; si ≥3 suspende cuenta (`is_active=False`) y notifica |
| `subscription_payment_recovered` | Resetea contador, reactiva cuenta, genera pago PAID, notifica |

---

## Descuentos en checkout

Los descuentos de Alcurro (`discounts` tabla, asociados a un tenant) se aplican calculando `custom_price_cents` antes de llamar a LS:

```python
# En signup_service.py:
discounted_cents = apply_discount(plan.monthly_price_cents, discount)
create_checkout(..., custom_price_cents=discounted_cents)
```

LS permite sobrescribir el precio de la variante mediante `checkout.custom_price` (en céntimos).

---

## Notificaciones automáticas de pago

| Evento | Notificación email | Notificación WhatsApp |
|---|---|---|
| Pago exitoso | Confirmación + link factura | ✅ Si hay `billing_phone` |
| Pago fallido (1–2 intentos) | Alerta con intentos restantes | ✅ |
| Pago fallido (3er intento) | Cuenta suspendida | ✅ |
| Pago recuperado | Cuenta reactivada | — |

Los datos de contacto vienen de `tenant.billing_email` y `tenant.billing_phone`.

---

## Referencia de endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/platform/ls/sync-plan/{plan_id}` | Sincronizar plan con LS |
| `GET` | `/api/platform/ls/payments` | Historial de pagos LS |
| `POST` | `/api/webhooks/lemon-squeezy` | Webhook LS (firma HMAC-SHA256) |

---

## Archivos principales

```
backend/app/services/lemon_squeezy_service.py   # Toda la lógica LS
backend/app/models/billing.py                    # LemonSqueezyPayment, PricingPlan (campos LS)
backend/app/models/tenant.py                     # Tenant (ls_customer_id, ls_customer_portal_url)
backend/app/routers/platform_ls.py               # Endpoints admin LS
backend/app/routers/webhook.py                   # POST /webhooks/lemon-squeezy
backend/scripts/migrate_lemon_squeezy_v1.py      # Migración inicial campos LS
backend/scripts/migrate_lemon_squeezy_v2.py      # ls_product_id, ls_variant_id_monthly/annual
frontend/src/pages/PlatformPricingPage.tsx        # Botón "Sync LS" por plan
frontend/src/pages/PlatformStripePage.tsx         # Vista de cobros (Stripe + LS)
```

---

## Coexistencia con Stripe

Ambos proveedores pueden estar activos simultáneamente:

- `STRIPE_SIMULATION_MODE=true` → el flujo de registro usa checkout simulado (sin Stripe real)
- `LEMON_SQUEEZY_API_KEY` configurado → el flujo de registro usa LS real
- Si ambos están activos, el checkout LS tiene prioridad (se llama primero en `signup_service`)

Los pagos de cada proveedor se registran en tablas separadas (`stripe_payments` y `lemon_squeezy_payments`) y ambos son visibles en `/admin/cobros`.
