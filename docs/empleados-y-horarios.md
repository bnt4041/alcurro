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

## Bloques de horario (`work_schedule_blocks`)

Permite varios tramos con días distintos, por ejemplo:

| Bloque | Días | Horario | Descanso |
|--------|------|---------|----------|
| 1 | Lun–Jue (0–3) | 09:00–18:00 | 60 min |
| 2 | Vie (4) | 08:00–15:00 | 0 min |

### Reglas

- Cada día de la semana (0=lunes … 6=domingo) solo puede aparecer en **un** bloque.
- Cada bloque necesita al menos un día, hora inicio &lt; hora fin.
- `break_minutes`: 0–480.

### Modelo de datos

Tabla `employees`:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `work_schedule_blocks` | JSONB | Lista de bloques (fuente de verdad) |
| `work_start_time`, `work_end_time`, `work_days` | legacy | Sincronizados con el **primer bloque** al guardar |
| `shift_configuration_id` | UUID opcional | Turno complejo alternativo |

Ejemplo JSON:

```json
[
  {
    "work_days": [0, 1, 2, 3],
    "work_start_time": "09:00:00",
    "work_end_time": "18:00:00",
    "break_minutes": 60
  },
  {
    "work_days": [4],
    "work_start_time": "08:00:00",
    "work_end_time": "15:00:00",
    "break_minutes": 0
  }
]
```

### UI

Componente `WorkScheduleEditor` (`frontend/src/components/WorkScheduleEditor.tsx`):

- Añadir / quitar bloques
- Chips de días (deshabilitados si ya están en otro bloque)
- Turno opcional (configuraciones en `/app/turnos`)

### Backend

Validación en `app/services/work_schedule.py` → `normalize_employee_schedule()` llamado en create/update de empleados.

Migración: `scripts/migrate_work_schedule_blocks.py`

## Listado

La columna **Horario** usa `formatWorkSchedule()` (`frontend/src/lib/workSchedule.ts`) y muestra todos los bloques resumidos.

## Aceptación legal (edición)

Si el usuario tiene permiso `legal.read`, al editar un empleado se muestra el estado de aceptación de textos obligatorios (`GET /api/legal/employees/{id}/status`).
