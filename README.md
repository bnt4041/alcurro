# alcurro — HRM multi-tenant por WhatsApp

Gestión de RRHH: fichajes, vacaciones, documentos, **firma electrónica**, textos legales y panel multi-empresa. Integración WhatsApp vía **goWA**.

## Documentación

**Índice completo:** [docs/README.md](docs/README.md)

| Tema | Enlace |
|------|--------|
| Instalación, Docker, migraciones | [docs/instalacion.md](docs/instalacion.md) |
| Arquitectura y multi-tenant | [docs/arquitectura.md](docs/arquitectura.md) |
| Admin plataforma (cuentas, mail, WhatsApp, Stripe) | [docs/admin-plataforma.md](docs/admin-plataforma.md) |
| Panel cliente `/app` | [docs/panel-cliente.md](docs/panel-cliente.md) |
| Empleados y horarios múltiples | [docs/empleados-y-horarios.md](docs/empleados-y-horarios.md) |
| Firmas electrónicas | [docs/firmas-electronicas.md](docs/firmas-electronicas.md) |
| Correo SMTP | [docs/correo-smtp.md](docs/correo-smtp.md) |
| Textos legales | [docs/legal.md](docs/legal.md) |
| API REST | [docs/api.md](docs/api.md) |

## Arranque rápido

```bash
docker compose up -d --build
```

| Servicio | URL |
|----------|-----|
| Web | http://localhost:5174 |
| Alta cliente | http://localhost:5174/registro |
| Acceso (plataforma + tenant) | http://localhost:5174/acceso |
| Admin plataforma | http://localhost:5174/admin |
| API (OpenAPI) | http://localhost:8000/docs |
| goWA (QR) | http://localhost:3000 |

### Credenciales demo

| Rol | Acceso |
|-----|--------|
| **Admin plataforma** | `/acceso` → `platform@hrm.local` / `platform123` |
| **Tenant demo** | `/acceso` → cuenta `demo`, usuario `ADM001`, contraseña `admin123` |

### Migraciones iniciales (primera instalación)

Además de las migraciones automáticas al arrancar el backend, ejecuta una vez:

```bash
docker exec hrm-backend python -m scripts.migrate_multitenant
docker exec hrm-backend python -m scripts.migrate_rbac_billing
docker exec hrm-backend python -m scripts.migrate_org_hierarchy
docker exec hrm-backend python -m scripts.migrate_company_billing
docker exec hrm-backend python -m scripts.migrate_pricing_catalog
docker exec hrm-backend python -m scripts.migrate_stripe
docker exec hrm-backend python -m scripts.migrate_employee_constraints
```

## Jerarquía organizativa

```
Tenant (cuenta)
 └── Empresa
      └── Centro de trabajo
           └── Departamento
                └── Empleado
```

## Funcionalidades principales

- **Fichajes y paradas** — Registro inalterable (normativa española).
- **Vacaciones** — Solicitudes y aprobación.
- **Turnos** — Configuraciones complejas (opcional por empleado).
- **Empleados** — DNI/NIE, centro/departamento, **bloques de horario** (varios tramos por semana).
- **Documentos** — Biblioteca y envío por WhatsApp.
- **Firmas** — OTP, firma manuscrita, PDF firmado y certificado; firmantes externos sin ser empleados.
- **Legal** — Textos versionados y aceptación obligatoria.
- **Admin plataforma** — Cuentas, tarifas, Stripe, goWA compartido, **SMTP global** y logs de correo.
- **RBAC** — Grupos de permisos personalizables por tenant.

## Variables de entorno

Ver [.env.example](.env.example). Destacadas:

- `PUBLIC_APP_URL` — Enlaces públicos (firmas, Stripe).
- `STRIPE_SIMULATION_MODE` — `true` por defecto (alta sin Stripe real).
- `JWT_SECRET` — Cambiar en producción.

## Stripe (opcional)

Con claves reales y `STRIPE_SIMULATION_MODE=false`: checkout y webhooks en `/api/webhooks/stripe`.  
En simulación: `/registro/pago-simulado` y **Cobros** en `/admin/cobros`.

## goWA

- **Compartido**: configurar en `/admin/whatsapp` (URL interna `http://gowa:3000/...` en Docker).
- **Por tenant**: desde `/app/cuenta` (requiere Docker socket en el backend).

## Especificación de firmas (legacy)

El documento [`firmas.md`](firmas.md) describe el diseño original (Laravel). La implementación actual en este repo está documentada en [docs/firmas-electronicas.md](docs/firmas-electronicas.md).

## Stack

React + Vite · FastAPI · PostgreSQL · goWA · (Ollama opcional)

Desarrollo frontend local: `cd frontend && bun install && bun run dev`
