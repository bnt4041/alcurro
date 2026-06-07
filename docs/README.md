# Documentación alcurro (HRM)

Índice de la documentación del proyecto. La aplicación es un **HRM multi-tenant** con panel web, WhatsApp (goWA), fichajes, vacaciones, documentos y **firma electrónica**.

## Guías

| Documento | Contenido |
|-----------|-----------|
| [Instalación y arranque](instalacion.md) | Docker, variables de entorno, migraciones, credenciales demo |
| [Despliegue en servidor](deploy.md) | Producción: Nginx, HTTPS, backups, goWA, actualizaciones |
| [Arquitectura](arquitectura.md) | Stack, multi-tenant, jerarquía org, servicios |
| [Admin plataforma](admin-plataforma.md) | Cuentas, usuarios, tarifas, Stripe, WhatsApp, correo |
| [Panel cliente](panel-cliente.md) | Rutas `/app`, permisos, módulos del tenant |
| [Empleados y horarios](empleados-y-horarios.md) | Alta/edición, centro/departamento, bloques de horario |
| [Firmas electrónicas](firmas-electronicas.md) | Envelopes, OTP, PDF firmado, firmantes externos |
| [Correo SMTP](correo-smtp.md) | Configuración global y logs de envío |
| [Legal](legal.md) | Textos legales y aceptación por empleado |
| [Stripe](stripe.md) | Claves, webhook, productos, checkout, producción |
| [API](api.md) | Prefijos, autenticación, endpoints principales |

## Referencia rápida

### URLs (desarrollo)

| Recurso | URL |
|---------|-----|
| Web | http://localhost:5174 |
| Registro | http://localhost:5174/registro |
| Acceso unificado | http://localhost:5174/acceso |
| Admin plataforma | http://localhost:5174/admin |
| API OpenAPI | http://localhost:8000/docs |
| goWA (QR) | http://localhost:3000 |

### Credenciales demo

| Rol | Cuenta / usuario | Contraseña |
|-----|------------------|------------|
| Admin plataforma | `platform@hrm.local` | `platform123` |
| Tenant demo | cuenta `demo`, usuario `ADM001` | `admin123` |

### Estructura del repositorio

```
hrm/
├── backend/          # FastAPI + SQLModel + PostgreSQL
│   ├── app/
│   │   ├── models/   # SQLModel (empleados, firmas, legal, mail…)
│   │   ├── routers/  # API REST
│   │   ├── services/ # Lógica de negocio
│   │   └── schemas/  # Pydantic
│   └── scripts/      # Migraciones idempotentes
├── frontend/         # React + Vite + TypeScript
├── docs/             # Esta documentación
├── docker-compose.yml
└── firmas.md         # Especificación original (Laravel); ver docs/firmas-electronicas.md
```
