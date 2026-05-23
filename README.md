# alcurro — HRM multi-tenant por WhatsApp

## Arranque

```bash
docker compose up -d --build
docker exec hrm-backend python -m scripts.migrate_multitenant
docker exec hrm-backend python -m scripts.migrate_rbac_billing
docker exec hrm-backend python -m scripts.migrate_org_hierarchy
docker exec hrm-ollama ollama pull llama3.2
```

| Servicio | URL |
|----------|-----|
| **Panel** | http://localhost:5174/login |
| **API** | http://localhost:8000/docs |

## Login

En `/login` elige pestaña **Plataforma** o **Cliente**:

| Pestaña | Quién | Demo |
|---------|-------|------|
| **Plataforma** | Tú (admin app) | `platform@hrm.local` / `platform123` |
| **Cliente** | Tenant / responsables / empleados con panel | cuenta `demo` · `ADM001` / `admin123` |

## Jerarquía organizativa (monetización)

```
Tenant (cuenta de facturación)
 └── Empresa
      └── Centro de trabajo
           └── Departamento
                └── Empleado
```

- **Grupos de usuarios**: permisos personalizables por tenant.
- **Plantillas de grupos**: al crear un cliente desde plataforma se clonan los grupos por defecto.

## Tipos de usuario y grupos

| Tipo | Descripción |
|------|-------------|
| **Administrador plataforma** | Gestiona todas las cuentas (`/plataforma`) |
| **Administrador de cuenta** | Control total dentro de su tenant |
| **Responsable** | Supervisión de equipos (permisos por defecto vía grupo) |
| **Inspector de Trabajo** | Solo lectura |
| **Empleado** | WhatsApp; panel solo si tiene grupo con permisos |

Los **grupos** (`/grupos`) permiten personalizar permisos (empleados, fichajes, vacaciones, facturación, goWA, etc.). Cada cuenta incluye grupos predefinidos del sistema.

## Facturación de cuentas

En **Cuenta → Datos de facturación**: razón social, CIF/NIF, email, dirección, ciudad, CP, provincia y país (mínimos para facturar).

## Arquitectura multi-tenant

```
Tenant (cuenta)
 ├── Empresa A, Empresa B, …
 ├── White-label (logo, colores)
 └── Contenedor goWA dedicado (WhatsApp propio)
      └── Webhook: POST /webhook/whatsapp/{slug}
```

- Cada **tenant** = una cuenta cliente con varias **empresas**.
- Cada tenant tiene su **propio contenedor goWA** (se crea desde **Cuenta → Crear contenedor goWA**).
- **White-label**: logo URL + colores primario/sidebar/acento (página login y panel).

## Crear nueva cuenta (plataforma)

```bash
curl -X POST http://localhost:8000/api/tenants \
  -H "Content-Type: application/json" \
  -H "X-Platform-Key: hrm-platform-setup" \
  -d '{"slug":"mi-cliente","name":"Mi Cliente S.L."}'
```

Luego login con `mi-cliente` / usuario admin creado en esa cuenta.

## goWA por tenant

1. Admin entra en **Cuenta** en el panel.
2. Pulsa **Crear / reiniciar contenedor goWA**.
3. Abre el enlace del panel QR (puerto 3010, 3011, …).
4. Escanea QR con el móvil del tenant.

Requisito: el backend monta `/var/run/docker.sock` (Docker Desktop en Windows).

## Cambiar empresa activa

Si el tenant tiene varias empresas, el admin ve un selector en la barra lateral (`X-Company-Id`).

## Login falla con "Internal Server Error"

Suele ser el proxy de Vite sin conexión al backend (contenedores en redes distintas tras cambios en `docker-compose`):

```bash
docker compose down
docker compose up -d --build
```

En el login usa los **tres** campos: cuenta `demo`, usuario `ADM001`, contraseña `admin123`.
