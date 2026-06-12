# Administración de plataforma

Acceso: http://localhost:5174/admin (tras login como administrador de plataforma en `/acceso`).

## Menú

| Ruta | Función |
|------|---------|
| `/admin` | Cuentas cliente (tenants): listado, alta, detalle, facturación, goWA por tenant |
| `/admin/usuarios` | Usuarios administradores de la plataforma (CRUD) |
| `/admin/tarifas` | Catálogo de precios / planes |
| `/admin/descuentos` | Descuentos sobre tarifas |
| `/admin/cobros` | Historial Stripe y simulación de cobros |
| `/admin/whatsapp` | goWA compartido: URL API, QR, prueba de conexión |
| `/admin/mail` | SMTP global y logs de correo |

## Cuentas cliente (`/admin`)

Desde el listado puedes:

- Crear tenant (slug, nombre, datos iniciales).
- Abrir ficha de cuenta: empresas, usuarios del tenant, facturación, simular pago, reiniciar goWA dedicado.
- En la pestaña **Facturación**: gestionar la suscripción única de la cuenta, métodos de pago, y elegir qué empresa es la titular de las facturas.

API principal: `GET/POST /api/platform/tenants`, detalle por id.

## Usuarios plataforma (`/admin/usuarios`)

Administradores que gestionan todas las cuentas (no pertenecen a un tenant concreto).

- `GET /api/platform/users`
- `POST /api/platform/users`
- `PATCH /api/platform/users/{id}`

## Tarifas y descuentos

Gestión del catálogo comercial usado en el registro y facturación:

- `/api/platform/catalog/...` (planes, precios)
- Descuentos asociados a tenants o promociones

## Cobros Stripe (`/admin/cobros`)

Con `STRIPE_SIMULATION_MODE=true` (por defecto):

- El registro en `/registro` pasa por pago simulado.
- Puedes simular cobro + activación goWA para un tenant existente.

Con Stripe real: configura `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` y `STRIPE_SIMULATION_MODE=false`.

Webhook: `POST /api/webhooks/stripe`

## WhatsApp compartido (`/admin/whatsapp`)

Configuración en `system_settings` (fila única `id=1`):

| Campo | Uso |
|-------|-----|
| `gowa_send_url` | API de envío (Docker: `http://gowa:3000/send/message`) |
| `gowa_ui_url` | Interfaz web en el navegador (`http://localhost:3000`) |
| `gowa_webhook_url` | goWA → backend (`http://backend:8000/webhook/whatsapp`) |
| `gowa_basic_auth` | `usuario:contraseña` |

La página muestra estado de vinculación y código QR para escanear con el móvil de la línea oficial.

## Correo (`/admin/mail`)

Ver [Correo SMTP](correo-smtp.md).

## Alta de tenant vía API

```bash
curl -X POST http://localhost:8000/api/tenants \
  -H "Content-Type: application/json" \
  -H "X-Platform-Key: hrm-platform-setup" \
  -d '{"slug":"mi-cliente","name":"Mi Cliente S.L."}'
```

Variable `PLATFORM_SETUP_KEY` en el backend (por defecto `hrm-platform-setup`).
