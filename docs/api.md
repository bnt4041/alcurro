# API REST

Base: `http://localhost:8000/api`  
Documentación interactiva: http://localhost:8000/docs

## Autenticación

### Login unificado

`POST /api/auth/login`

Body según tipo:

```json
// Plataforma
{ "email": "platform@hrm.local", "password": "..." }

// Tenant
{ "account": "demo", "username": "ADM001", "password": "..." }
```

Respuesta: `{ "access_token": "...", "token_type": "bearer", ... }`

Cabecera en peticiones protegidas:

```http
Authorization: Bearer <token>
```

### Contexto organizativo (tenant)

```http
X-Company-Id: <uuid>
X-Work-Center-Id: <uuid>
X-Department-Id: <uuid>
```

## Prefijos principales

| Prefijo | Auth | Descripción |
|---------|------|-------------|
| `/api/auth` | Público | Login, refresh |
| `/api/public` | Público | Registro, branding |
| `/api/public/firma` | Token URL | Firma electrónica |
| `/api/platform` | Plataforma | Tenants, usuarios plataforma |
| `/api/platform/mail` | Plataforma | SMTP y logs |
| `/api/platform/whatsapp` | Plataforma | goWA global |
| `/api/platform/stripe` | Plataforma | Cobros |
| `/api/webhooks/stripe` | Firma Stripe | Eventos Stripe |
| `/webhook/whatsapp` | goWA | Mensajes entrantes |
| `/api/employees` | Tenant + permiso | CRUD empleados |
| `/api/org` | Tenant | Árbol organizativo |
| `/api/clock-ins` | Tenant | Fichajes |
| `/api/breaks` | Tenant | Paradas |
| `/api/leave-requests` | Tenant | Vacaciones |
| `/api/shifts` | Tenant | Turnos |
| `/api/documents` | Tenant | Documentos |
| `/api/signatures` | Tenant | Firmas |
| `/api/legal` | Tenant | Legal |
| `/api/groups` | Tenant | Grupos RBAC |

## Empleados

```http
GET    /api/employees?q=&role=&active_only=
POST   /api/employees
GET    /api/employees/{id}
PATCH  /api/employees/{id}
DELETE /api/employees/{id}    # requiere permiso admin
```

Body create (extracto):

```json
{
  "department_id": "uuid",
  "full_name": "...",
  "id_document": "12345678Z",
  "phone": "...",
  "work_schedule_periods": [
    {
      "valid_from": "2026-01-01",
      "valid_to": "2026-07-31",
      "blocks": [
        {
          "work_days": [0, 1, 2, 3],
          "slots": [
            { "work_start_time": "09:00:00", "work_end_time": "14:00:00", "break_minutes": 0 },
            { "work_start_time": "16:00:00", "work_end_time": "18:00:00", "break_minutes": 0 }
          ]
        }
      ]
    }
  ]
}
```

## Organización

```http
GET  /api/org/tree
GET  /api/org/work-centers
POST /api/org/work-centers
GET  /api/org/departments?work_center_id=
POST /api/org/departments
```

## Firmas

```http
GET  /api/signatures
POST /api/signatures
POST /api/signatures/from-upload   # multipart
POST /api/signatures/{id}/cancel
GET  /api/signatures/{id}/signed
```

Público:

```http
GET  /api/public/firma/{token}
POST /api/public/firma/{token}/start
POST /api/public/firma/{token}/verify-otp
POST /api/public/firma/{token}/sign
```

## Correo (plataforma)

```http
GET  /api/platform/mail/settings
PUT  /api/platform/mail/settings
GET  /api/platform/mail/logs?limit=100&success_only=
POST /api/platform/mail/test
```

## Códigos de error habituales

| HTTP | Causa |
|------|--------|
| 400 | Validación (horario, departamento, firmante) |
| 401 | Token ausente o inválido |
| 403 | Sin permiso o fuera de alcance org |
| 404 | Recurso no encontrado |
| 409 | DNI o código duplicado |
| 502 | goWA / servicio externo |
