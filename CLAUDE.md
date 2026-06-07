# CLAUDE.md — Guía de desarrollo de Alcurro

> Contexto automático para Claude Code. Léelo antes de tocar cualquier fichero.

---

## Stack principal

| Capa | Tecnología |
|---|---|
| Frontend | React 19 · TypeScript · Vite · React Router 7 · Tabulator 6 |
| Backend | FastAPI 0.115 · SQLModel · Pydantic v2 · Uvicorn |
| Base de datos | PostgreSQL 16 (psycopg3) |
| WhatsApp | goWA (multi-device REST API) |
| PDFs | reportlab · pypdf · Pillow |
| IA | Ollama (local, llama3.2 por defecto) |
| Pagos | Stripe (modo simulación por defecto) |
| Correo | SMTP (`smtplib`) |
| Runtime frontend | Bun (`/root/.bun/bin/bun run build`) — **no `npm`** |
| Infraestructura | Docker Compose + Traefik (producción) |

---

## Arranque de desarrollo

```bash
# Todos los servicios
docker compose up -d

# Solo reconstruir backend
docker restart hrm-backend

# Build frontend (desde /var/www/alcurro/frontend)
/root/.bun/bin/bun run build    # → dist/ servido por Nginx
```

Servicios locales:

| Servicio | URL |
|---|---|
| App | http://localhost:5174 |
| API + Swagger | http://localhost:8000/docs |
| goWA | http://localhost:3000 |

---

## Convenciones críticas

### Backend

- **Nunca modificar ClockIn una vez creado** — es registro inmutable (normativa española). Las correcciones van por `Incident`.
- **Modelos en `app/models/`** — al añadir un modelo o campo nuevo, importarlo en `database.py` para que `create_all` lo cree. Los campos nuevos en tablas existentes requieren `ALTER TABLE` manual (SQLModel no migra columnas).
- **Todos los endpoints protegidos van dentro de `protected = APIRouter()`** en `api.py`. Los públicos se añaden directamente a `api_router`.
- **Servicio → Router, nunca al revés** — la lógica de negocio va en `app/services/`, los routers solo validan entrada y devuelven respuesta.
- **`session.flush()` para obtener ID antes de commit** — usar cuando se necesita el ID generado para crear relaciones en la misma transacción.
- **Migraciones de esquema**: usar scripts en `scripts/` o `ALTER TABLE` directo. No confiar en Alembic (no está activo).
- **Gestión de errores**: el handler de `IntegrityError` en `main.py` devuelve 409 con mensajes en español — aprovechar constraints de BD en vez de validar a mano.

### Frontend

- **`api/client.ts`** es el único cliente HTTP — usar siempre `api.get`, `api.post`, `api.download`, etc. Nunca `fetch` directo excepto en páginas públicas sin auth.
- **Tablas → `DataTable`** con columnas `DataTableColumn[]`. Los formatters devuelven HTML string.
- **Modales** solo se cierran con el botón X o botones de acción — NO con click en overlay.
- **Permisos** — comprobar siempre con `canModule()` / `hasPerm()` de `lib/permissions.ts` antes de mostrar acciones.
- **Toast** — usar `useToast()` de `ToastContext`. No usar `alert()`.
- **Rutas protegidas** — añadir dentro del bloque `ProtectedRoute` en `App.tsx`. Rutas públicas fuera.
- **Build** — siempre con Bun: `/root/.bun/bin/bun run build` desde `frontend/`.

---

## Estructura del proyecto

```
/var/www/alcurro/
├── backend/
│   └── app/
│       ├── main.py           ← Startup, CORS, error handlers, mounts
│       ├── config.py         ← Settings (env vars, public_app_url…)
│       ├── database.py       ← Engine, create_db_and_tables, imports de modelos
│       ├── core/             ← Auth, RBAC, contexto org
│       ├── models/           ← SQLModel (tablas)
│       ├── schemas/          ← Pydantic (request/response)
│       ├── routers/          ← FastAPI endpoints
│       │   └── api.py        ← Router aggregator (protected + public)
│       └── services/         ← Lógica de negocio
├── frontend/
│   └── src/
│       ├── App.tsx           ← Router tree
│       ├── api/client.ts     ← HTTP client + auth headers
│       ├── context/          ← AuthContext, ToastContext
│       ├── components/       ← Componentes reutilizables
│       ├── pages/            ← Páginas (1 por ruta)
│       ├── hooks/            ← Custom hooks
│       └── lib/              ← Utilidades (permisos, formatters…)
├── docs/                     ← Documentación
│   ├── arquitectura.md       ← Mapa estructural completo (este fichero)
│   ├── legal.md              ← Sistema de textos legales
│   ├── api.md                ← Referencia de endpoints
│   └── …
├── scripts/                  ← Migraciones manuales
├── docker-compose.yml
└── CLAUDE.md                 ← Este fichero
```

---

## Jerarquía organizativa (multi-tenant)

```
Tenant  (cuenta de facturación, branding, WhatsApp)
 └── Company  (empresa → X-Company-Id header)
      └── WorkCenter  (centro → X-Work-Center-Id)
           └── Department  (depto → X-Department-Id)
                └── Employee  (usuario de la app)
```

El contexto activo se envía en cabeceras HTTP y se resuelve en `core/org_context.py`.

---

## Sistema de permisos (RBAC)

- **Roles**: `employee`, `supervisor`, `manager`, `tenant_admin`, `labor_inspector`, `admin`
- **Grupos**: plantillas de permisos asignables a empleados (`UserGroup` / `GroupTemplate`)
- **Permisos granulares**: `employees.read`, `clock_ins.write`, `leave.approve`, etc.
- **Coarse**: `read` / `write` / `admin` por módulo (compatibilidad)
- Dependencias FastAPI: `require_permission(Permission.READ, "employees")`

---

## Flujo WhatsApp (goWA + webhook)

```
Mensaje WA entrante
  → POST /webhook/whatsapp/{tenant_slug}
  → WebhookService.process()
      ├── Resolver empleado por teléfono
      ├── Check legales pendientes → token 5min → link WA
      ├── Bienvenida si es primera vez
      ├── NLU / intent classification (Ollama)
      └── Ejecutar acción (fichar, permisos, consulta…)
          └── Responder vía goWA REST API
```

---

## Generación de PDFs

| Servicio | Qué genera |
|---|---|
| `signature_pdf.py` | PDF firmado + certificado de firma |
| `legal_pdf_service.py` | Certificado de aceptación legal (todos los docs en uno) |

Patrón: `reportlab Canvas → BytesIO → store_upload_file() → create_delivery()`

---

## Puntos de entrada importantes

| Fichero | Para qué |
|---|---|
| `backend/app/main.py` | Ver startup, migraciones, CORS, mounts |
| `backend/app/routers/api.py` | Ver qué routers están registrados y con qué auth |
| `backend/app/services/webhook_service.py` | Lógica completa de WhatsApp (~800 líneas) |
| `backend/app/services/legal_service.py` | Aceptación de legales, tokens, PDF |
| `frontend/src/App.tsx` | Árbol de rutas completo |
| `frontend/src/api/client.ts` | Cliente HTTP, gestión de token JWT |
| `frontend/src/lib/permissions.ts` | Checks de permisos en frontend |

---

## Variables de entorno clave

```env
DATABASE_URL=postgresql+psycopg://hrm:hrm@postgres:5432/hrm
JWT_SECRET=cambia-esto-en-produccion
PUBLIC_APP_URL=https://alcurro.es        # Para links en emails/WhatsApp
STRIPE_SIMULATION_MODE=true              # false para Stripe real
PLATFORM_SETUP_KEY=clave-admin-inicial
GOWA_BASIC_AUTH=user:pass               # Auth HTTP goWA
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2
```

---

## Patrones de código frecuentes

### Endpoint protegido con permiso

```python
@router.get("/resource", response_model=list[ResourceRead])
def list_resources(
    ctx: OrgContext = Depends(get_org_context),
    session: Session = Depends(get_session),
    _: object = Depends(require_permission(Permission.READ, "resource")),
) -> list[Resource]:
    ...
```

### Crear entidad y hacer flush (para relaciones inmediatas)

```python
row = MyModel(tenant_id=tenant_id, **data.model_dump())
session.add(row)
session.flush()   # row.id disponible sin commit
# ... crear relaciones usando row.id ...
session.commit()
```

### Añadir columna nueva a tabla existente

```bash
docker exec hrm-postgres psql -U hrm hrm \
  -c "ALTER TABLE my_table ADD COLUMN IF NOT EXISTS new_col VARCHAR(50) DEFAULT 'valor';"
```

### Importar modelo nuevo (auto-create tabla)

```python
# En database.py — añadir import:
from app.models.my_module import MyNewModel  # noqa: F401
```

### Acción de tabla con FilePreviewModal

```tsx
// En columna de acciones:
{ id: "preview", label: "Ver" }

// En handler:
if (action === "preview") setPreviewPath({ path: `/resource/${row.id}/file`, name: row.file_name });

// En render:
<FilePreviewModal apiPath={previewPath?.path ?? null} filename={previewPath?.name} onClose={() => setPreviewPath(null)} />
```
