# Panel cliente (tenant)

Acceso: http://localhost:5174/acceso → tras autenticación, `/app`.

## Rutas

| Ruta | Módulo | Permiso típico |
|------|--------|----------------|
| `/app` | Dashboard | — |
| `/app/empleados` | Empleados | `employees` |
| `/app/fichajes` | Fichajes (entrada/salida) | `clock_ins` |
| `/app/paradas` | Paradas / descansos | `breaks` |
| `/app/vacaciones` | Vacaciones | `leave_requests` |
| `/app/turnos` | Configuración de turnos | `shifts` |
| `/app/organizacion` | Empresas, centros, departamentos | `companies` |
| `/app/documentos` | Biblioteca de documentos | `documents` |
| `/app/firmas` | Solicitudes de firma electrónica | `documents` (write) |
| `/app/legal` | Textos legales y aceptaciones | `legal` |
| `/app/grupos` | Grupos de permisos | `groups` |
| `/app/cuenta` | Datos de cuenta, facturación, goWA tenant | — |

## Selector de organización

En la barra lateral, si el usuario tiene permiso `companies.read`:

- **Empresa** (si hay varias)
- **Centro de trabajo**
- **Departamento**

Filtra listados (empleados, fichajes, etc.) según el alcance. Las cabeceras se envían automáticamente en cada petición API.

## Tipos de usuario

| Rol | Descripción |
|-----|-------------|
| `tenant_admin` | Control total en el tenant |
| `admin` | Administración de empresa |
| `manager` / `supervisor` | Supervisión de equipos |
| `labor_inspector` | Solo lectura |
| `employee` | Uso principal por WhatsApp; panel si tiene grupo con permisos |

## Grupos de permisos (`/app/grupos`)

Cada grupo define permisos por módulo. Al crear un empleado con rol `employee`, por defecto se asigna el grupo **«Empleados con panel»** si existe.

## Cuenta (`/app/cuenta`)

- Datos de facturación (razón social, CIF, dirección…).
- Branding (logo, colores).
- Crear/reiniciar contenedor goWA dedicado del tenant (requiere socket Docker en el backend).

## WhatsApp para empleados

Los empleados interactúan por WhatsApp con la línea configurada (compartida o dedicada). El webhook interpreta mensajes para fichajes, vacaciones y consultas según la implementación en `webhook_service`.
