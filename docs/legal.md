# Textos legales

Ruta panel: `/app/legal`  
Permisos: `legal.read`, `legal.write`

## Función

Permite publicar textos que los empleados deben **aceptar** (política de privacidad, condiciones, etc.) con control de versión.

## Modelos

| Tabla | Descripción |
|-------|-------------|
| `legal_documents` | Por tenant: `code`, `title`, `body`, `version`, `is_required`, `is_active` |
| `legal_acceptances` | Registro por empleado + documento + versión aceptada |

## API (resumen)

| Método | Ruta |
|--------|------|
| GET | `/api/legal/documents` |
| POST | `/api/legal/documents` |
| PATCH | `/api/legal/documents/{id}` |
| GET | `/api/legal/employees/{id}/status` | Estado de aceptación de un empleado |
| POST | `/api/legal/accept` | Aceptar documento (panel o flujo modal) |

## UI empleados

- En **Empleados → Editar**, bloque «Aceptación legal» con estado por documento.
- Modal `LegalAcceptanceModal` puede forzar re-aceptación si cambia la versión obligatoria.

## Seed

Al migrar (`migrate_legal_and_schedule`), se crean documentos por defecto para cada tenant existente vía `legal_service.seed_default_legal_documents`.

## Migración

`scripts/migrate_legal_and_schedule.py` — tablas legales + columnas de horario en `employees`.
