# Stripe — Configuración e integración

## Variables de entorno

```env
STRIPE_SECRET_KEY=sk_test_...          # clave secreta (test) o sk_live_... (producción)
STRIPE_PUBLISHABLE_KEY=pk_test_...     # clave pública (usada en el frontend)
STRIPE_WEBHOOK_SECRET=whsec_...        # signing secret del webhook (ver sección 3)
STRIPE_SIMULATION_MODE=false           # true = sin Stripe real, false = Stripe activo
```

Añadir al fichero `.env` y reiniciar:

```bash
docker compose up -d --force-recreate backend
```

---

## Modos de operación

| `STRIPE_SIMULATION_MODE` | Comportamiento |
|---|---|
| `true` (defecto) | El alta en `/registro` va por `/registro/pago-simulado`. No se llama a Stripe. Útil en desarrollo. |
| `false` | Checkout real con Stripe. Requiere `STRIPE_SECRET_KEY` y `STRIPE_PUBLISHABLE_KEY` válidos. |

---

## 1. Claves de API

Obtenerlas en **Stripe Dashboard → Desarrolladores → Claves de API**.

| Clave | Variable | Prefijo test | Prefijo producción |
|---|---|---|---|
| Secreta | `STRIPE_SECRET_KEY` | `sk_test_` | `sk_live_` |
| Publicable | `STRIPE_PUBLISHABLE_KEY` | `pk_test_` | `pk_live_` |

> Las claves de test solo procesan pagos de prueba. No afectan a dinero real.

---

## 2. Webhook

El webhook permite que Stripe notifique a la app cuando ocurre un evento (pago completado, suscripción cancelada, factura fallida…).

### Configurar en Stripe Dashboard

1. Ir a **Desarrolladores → Webhooks → Añadir endpoint**
2. URL del endpoint:
   ```
   https://alcurro.es/api/webhooks/stripe
   ```
3. Eventos a escuchar (seleccionar todos):
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `invoice.upcoming`
4. Guardar y copiar el **Signing secret** (`whsec_...`)
5. Añadirlo al `.env`:
   ```env
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
6. Reiniciar backend:
   ```bash
   docker compose up -d --force-recreate backend
   ```

### Probar en local (Stripe CLI)

Para recibir webhooks en desarrollo sin dominio público:

```bash
stripe listen --forward-to http://localhost:8000/api/webhooks/stripe
# Muestra un whsec_... local → añadir a .env como STRIPE_WEBHOOK_SECRET
```

---

## 3. Productos y precios

Los planes de suscripción de la app se sincronizan con los productos de Stripe.

### Flujo

```
Admin crea plan en /admin/tarifas
  → PricingPlan guardado en BD (con stripe_price_id vacío)
  → Admin va a /admin/cobros → botón "Sincronizar con Stripe"
      → stripe_service.sync_plan() crea Product + Price en Stripe
      → guarda stripe_price_id en PricingPlan
```

### Crear productos manualmente (alternativa)

1. Stripe Dashboard → **Productos → Añadir producto**
2. Crear un precio recurrente (mensual/anual)
3. Copiar el `price_id` (formato `price_...`)
4. En la app: `/admin/tarifas` → editar plan → campo `stripe_price_id`

---

## 4. Alta de clientes (checkout)

Con `STRIPE_SIMULATION_MODE=false`, el flujo de alta es:

```
/registro (formulario datos tenant)
  → POST /api/public/signup
      → stripe_service.create_checkout_session()
          → redirige a Stripe Hosted Checkout
  → Stripe procesa pago
  → Webhook checkout.session.completed
      → stripe_service.handle_webhook_event()
          → activa suscripción del tenant
  → Redirige a /registro/ok
```

---

## 5. Panel de administración (`/admin/cobros`)

Desde `/admin/cobros` se puede:

- Ver historial de pagos (`StripePayment`)
- Ver estado de cada suscripción
- Sincronizar planes con Stripe (`POST /api/platform/stripe/sync-plan/{id}`)
- Ver estado de la integración (`GET /api/platform/stripe/status`)

---

## 6. Pasar a producción

1. En Stripe Dashboard cambiar a modo **Live**
2. Obtener claves de producción (`sk_live_`, `pk_live_`)
3. Crear un nuevo webhook con la URL de producción y obtener su `whsec_live_...`
4. Actualizar `.env`:
   ```env
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_PUBLISHABLE_KEY=pk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_live_...
   STRIPE_SIMULATION_MODE=false
   ```
5. Reiniciar backend

> Nunca usar claves `sk_live_` en el entorno de desarrollo — las transacciones son reales.

---

## 7. Referencia de endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/platform/stripe/status` | Estado de la integración |
| `POST` | `/api/platform/stripe/sync-plan/{id}` | Sincronizar plan con Stripe |
| `GET` | `/api/platform/stripe/payments` | Historial de pagos |
| `POST` | `/api/webhooks/stripe` | Webhook Stripe (público, firmado) |
| `GET` | `/api/public/stripe-config` | Clave pública para el frontend |
| `GET` | `/api/public/simulate-checkout/{token}` | Checkout simulado (solo modo test) |
| `POST` | `/api/public/simulate-payment` | Pago simulado (solo modo test) |
