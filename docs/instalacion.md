# Instalación y arranque

## Requisitos

- Docker y Docker Compose
- (Opcional) [Bun](https://bun.sh) para desarrollo frontend local sin Docker

## Arranque con Docker

```bash
docker compose up -d --build
```

Servicios levantados:

| Contenedor | Puerto | Función |
|------------|--------|---------|
| `hrm-postgres` | 5432 | Base de datos |
| `hrm-backend` | 8000 | API FastAPI |
| `hrm-frontend` | 5174 | React (Vite) |
| `hrm-gowa` | 3000 | WhatsApp (goWA) |
| `hrm-ollama` | 11434 | LLM local (opcional) |

### Migraciones

Al arrancar, el backend ejecuta migraciones idempotentes en `lifespan` (`backend/app/main.py`):

- `migrate_gowa_device`, `migrate_system_gowa`
- `migrate_employee_id_document`, `migrate_work_breaks`
- `migrate_legal_and_schedule`
- `migrate_signatures`, `migrate_mail`
- `migrate_work_schedule_blocks`

Para bases de datos nuevas o tras clonar el repo, ejecuta también las migraciones históricas una vez:

```bash
docker exec hrm-backend python -m scripts.migrate_multitenant
docker exec hrm-backend python -m scripts.migrate_rbac_billing
docker exec hrm-backend python -m scripts.migrate_org_hierarchy
docker exec hrm-backend python -m scripts.migrate_company_billing
docker exec hrm-backend python -m scripts.migrate_pricing_catalog
docker exec hrm-backend python -m scripts.migrate_stripe
docker exec hrm-backend python -m scripts.migrate_employee_constraints
```

### Ollama (opcional)

```bash
docker exec hrm-ollama ollama pull llama3.2
```

## Variables de entorno

Copia `.env.example` a `.env` y ajusta:

| Variable | Descripción |
|----------|-------------|
| `POSTGRES_*` | Credenciales PostgreSQL |
| `JWT_SECRET` | Firma de tokens JWT (producción: valor largo aleatorio) |
| `PUBLIC_APP_URL` | URL pública del frontend (enlaces de firma, Stripe) |
| `GOWA_BASIC_AUTH` | Basic auth goWA (`usuario:contraseña`) |
| `STRIPE_*` | Claves Stripe (vacías = solo simulación) |
| `STRIPE_SIMULATION_MODE` | `true` por defecto: alta sin Stripe real |

En `docker-compose.yml` el backend recibe `DATABASE_URL`, `PUBLIC_APP_URL`, etc.

## Desarrollo local (frontend)

```bash
cd frontend
bun install
bun run dev
```

El proxy de Vite apunta al backend en `http://localhost:8000`.

## Desarrollo local (backend)

Requiere PostgreSQL accesible y dependencias Python del `requirements.txt`:

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://hrm:hrm_secret@localhost:5432/hrm
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Problemas frecuentes

### Login devuelve error de red

Reconstruye la pila para alinear redes Docker:

```bash
docker compose down
docker compose up -d --build
```

### Crear empleado: «Selecciona departamento»

Indica **centro** y **departamento** en el modal de empleado, o selecciona departamento en el selector de la barra lateral antes de crear.

### goWA no envía desde Docker

En admin → WhatsApp, la URL de envío debe ser `http://gowa:3000/send/message` (nombre del servicio en la red Docker), no `localhost`.

### Reiniciar solo el backend

```bash
docker compose restart backend
```
