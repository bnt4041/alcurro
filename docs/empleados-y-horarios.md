# Empleados y horarios

Ruta panel: `/app/empleados`  
API: `/api/employees`

## Alta y edición

El modal **Nuevo empleado** / **Editar empleado** incluye:

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| DNI/NIE | Sí | Validación y unicidad por empresa |
| Nombre, teléfono | Sí | Teléfono = WhatsApp |
| Email | No | |
| Rol | Sí | Define permisos por defecto |
| **Centro de trabajo** | Sí | Selector en cascada |
| **Departamento** | Sí | Depende del centro elegido |
| Horario (bloques) | Sí (≥1 bloque) | Ver abajo |
| Grupos de permisos | Si hay módulo grupos | |
| Contraseña panel | No en alta | Opcional para acceso web |
| Días vacaciones, activo | Sí | |

El **código de empleado** (`EMP-001`, …) se genera automáticamente.

### Centro y departamento

Antes solo se podía asignar departamento vía el selector global de la cabecera (`X-Department-Id`). Ahora el formulario envía `department_id` explícitamente.

Al crear, se preseleccionan centro/departamento del contexto activo si existen.

API valida que el departamento pertenezca al tenant:

```http
POST /api/employees
{ "department_id": "uuid", "work_schedule_blocks": [...], ... }
```

## Horarios (`work_schedule_periods`)

Estructura en tres niveles:

1. **Periodo** — vigencia por fechas (`valid_from`, `valid_to` opcional).
2. **Bloque de días** — qué días de la semana (0=lunes … 6=domingo).
3. **Franjas horarias** — una o varias por bloque (turno partido).

Ejemplo: del 01/01/2026 al 31/07/2026, lun–jue 09:00–14:00 y 16:00–18:00, viernes 08:00–15:00.

### Reglas

- Varios **periodos** sin solaparse en fechas.
- En cada periodo, cada **día** solo en un bloque.
- Cada bloque tiene al menos una **franja**; inicio &lt; fin.
- `break_minutes` por franja (0–480).

### Modelo de datos

| Columna | Descripción |
|---------|-------------|
| `work_schedule_periods` | JSONB — fuente de verdad |
| `work_schedule_blocks` | Resumen legacy del primer periodo |
| `work_start_time`, `work_end_time`, `work_days` | Legacy (primer bloque / primera franja) |

```json
[
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
      },
      {
        "work_days": [4],
        "slots": [
          { "work_start_time": "08:00:00", "work_end_time": "15:00:00", "break_minutes": 0 }
        ]
      }
    ]
  }
]
```

### Turno rotativo

Si el empleado usa un **turno complejo** (rotativo, partido, nocturno, etc.), marca **Turno rotativo** en el formulario:

- No se guardan franjas ni periodos en la ficha.
- Debes elegir un turno de `/app/turnos`.
- Campo `rotating_shift` en base de datos.

### UI

Componente `WorkScheduleEditor` (`frontend/src/components/WorkScheduleEditor.tsx`):

- Añadir / quitar bloques
- Chips de días (deshabilitados si ya están en otro bloque)
- Turno opcional (configuraciones en `/app/turnos`)

### Backend

Validación en `app/services/work_schedule.py` → `normalize_employee_schedule()` llamado en create/update de empleados.

Migraciones: `migrate_work_schedule_blocks.py`, `migrate_work_schedule_periods.py`

## Listado

La columna **Horario** usa `formatWorkSchedule()` (`frontend/src/lib/workSchedule.ts`) y muestra todos los bloques resumidos.

## Aceptación legal (edición)

Si el usuario tiene permiso `legal.read`, al editar un empleado se muestra el estado de aceptación de textos obligatorios (`GET /api/legal/employees/{id}/status`).
