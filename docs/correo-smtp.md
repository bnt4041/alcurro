# Correo SMTP (plataforma)

Configuración **global** para toda la instalación: firmas, notificaciones y pruebas. No es por tenant.

Ruta admin: `/admin/mail`  
API: `/api/platform/mail/*` (solo usuario plataforma)

## Configuración

Tabla `system_settings` (fila `id=1`):

| Campo | Descripción |
|-------|-------------|
| `smtp_host` | Servidor SMTP |
| `smtp_port` | Por defecto 587 |
| `smtp_user` | Usuario (opcional) |
| `smtp_password` | No se devuelve al leer; solo flag `smtp_password_configured` |
| `smtp_use_tls` | STARTTLS (587) o SSL (465) |
| `mail_from_address` | Remitente obligatorio para enviar |
| `mail_from_name` | Nombre visible (p. ej. «alcurro») |

### Puertos habituales

| Puerto | Modo |
|--------|------|
| 587 | STARTTLS (`smtp_use_tls=true`) |
| 465 | SSL directo (`smtp_use_tls=true`, puerto 465) |

## Endpoints

| Método | Ruta | Función |
|--------|------|---------|
| GET | `/api/platform/mail/settings` | Leer configuración |
| PUT | `/api/platform/mail/settings` | Actualizar (password solo si se envía) |
| GET | `/api/platform/mail/logs` | Historial (`limit`, `success_only`) |
| POST | `/api/platform/mail/test` | `{ "to_email": "..." }` |

## Logs (`mail_logs`)

Cada intento de envío registra:

| Campo | Descripción |
|-------|-------------|
| `to_address`, `subject` | Destino y asunto |
| `event_type` | `test`, `firma_solicitud`, `firma_otp`, `generic`, … |
| `success` | OK / error |
| `detail` | Mensaje de error SMTP |
| `tenant_id`, `envelope_id` | Contexto opcional |

La UI permite filtrar: todos / enviados / fallidos.

## Uso en firmas

`signature_notify.py` llama a `MailService.send()` cuando el firmante tiene email:

- Invitación a firmar (`firma_solicitud`, etc.)
- Código OTP (`firma_otp`)

Si SMTP no está configurado, el envío falla, se registra en `mail_logs` y en `signature_notifications` con `success=false`.

## Servicio

`backend/app/services/mail_service.py`:

- `send()` — envío + log + commit
- `send_test()` — correo de prueba desde admin
- `read_settings()` / `update_settings()`

Migración columnas SMTP + tabla logs: `scripts/migrate_mail.py`
