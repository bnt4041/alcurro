# Arquitectura y mapa estructural — Alcurro HRM

> Última revisión: junio 2026

---

## 1. Visión general del sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ALCURRO HRM                                    │
│                    Plataforma multi-tenant de RRHH                          │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
   │   BROWSER   │  │  WHATSAPP   │  │ LEMON SQUEEZY│
   │  React SPA  │  │  (empleado) │  │  (pagos)     │
   └──────┬──────┘  └──────┬──────┘  └──────┬───────┘
          │                │                 │
          │ HTTPS          │ Webhook         │ Webhook
          ▼                ▼                 ▼
   ┌─────────────────────────────────────────────────┐
   │              TRAEFIK (reverse proxy / SSL)       │
   └──────────────────────┬──────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌────────────┐ ┌────────────────┐
   │   NGINX     │ │  FASTAPI   │ │     goWA       │
   │  (React SPA)│ │  (API)     │ │ (WhatsApp API) │
   │  :80        │ │  :8000     │ │  :3000         │
   └─────────────┘ └─────┬──────┘ └───────┬────────┘
                         │                │
                    ┌────┴────┐      ┌────┴────┐
                    │PostgreSQL│     │  Ollama  │
                    │  :5432   │     │  :11434  │
                    └──────────┘     └──────────┘
```

---

## 2. Jerarquía multi-tenant

```
┌─────────────────────────────────────────────────────┐
│  PLATFORM ADMIN  (PlatformUser)                     │
│  /admin → gestiona cuentas, tarifas, Stripe, goWA   │
└──────────────────────┬──────────────────────────────┘
                       │ crea / gestiona
                       ▼
┌─────────────────────────────────────────────────────┐
│  TENANT  (cuenta de facturación + branding)         │
│  nombre, logo, colores primarios, config WhatsApp   │
│  billing_company_id → empresa titular de facturas    │
└──────────┬──────────────────────────────────────────┘
           │ 1..N
           ▼
┌────────────────────────────────┐
│  COMPANY  (empresa)            │
│  X-Company-Id header           │
└──────┬─────────────────────────┘
       │ 1..N
       ▼
┌───────────────────────────────┐
│  WORK CENTER  (centro trabajo) │
│  X-Work-Center-Id header       │
└──────┬────────────────────────┘
       │ 1..N
       ▼
┌───────────────────────────────┐
│  DEPARTMENT  (departamento)    │
│  X-Department-Id header        │
└──────┬────────────────────────┘
       │ 1..N
       ▼
┌──────────────────────────────────────────────────┐
│  EMPLOYEE  (empleado / usuario)                  │
│  email, phone, role, weekly_hours, schedule_type │
└──────────────────────────────────────────────────┘
```

---

## 3. Mapa de módulos del backend

```
backend/app/
│
├── main.py ──────────────────── FastAPI app, CORS, startup, error handlers
├── config.py ────────────────── Settings (env vars: DATABASE_URL, JWT_SECRET…)
├── database.py ──────────────── Engine, session factory, todos los model imports
│
├── core/ ────────────────────── Infraestructura transversal
│   ├── deps.py ──────────────── get_current_user() / get_session()
│   ├── security.py ──────────── JWT create/decode, bcrypt hash/verify
│   ├── permissions.py ───────── RBAC: Permission enum, require_permission()
│   ├── org_context.py ───────── OrgContext (tenant+company+wc+dept resolver)
│   ├── tenant_context.py ────── TenantContext
│   └── platform_deps.py ─────── Platform-level auth dependency
│
├── models/ ──────────────────── SQLModel tables (auto-created vía create_all)
│   ├── models.py ────────────── Employee, ClockIn, LeaveRequest, WorkBreak…
│   ├── tenant.py ────────────── Tenant, Company, Subscription, BillingMethod
│   ├── organization.py ──────── WorkCenter, Department, GroupTemplate
│   ├── documents.py ─────────── DocumentDelivery, DocumentType, DocumentTag
│   ├── signature.py ─────────── SignatureEnvelope, SignatureSigner, SignatureOtp
│   ├── legal.py ─────────────── LegalDocument, LegalAcceptance, LegalToken
│   ├── incident.py ──────────── Incident, IncidentAutoRule
│   ├── ai.py ────────────────── AiAction, AiConversationRule, AiUsageRecord
│   ├── rbac.py ──────────────── PlatformUser, UserGroup, EmployeeGroup
│   ├── billing.py ───────────── PricingPlan, Discount, StripePayment
│   ├── notification.py ──────── Notification, NotificationPreference
│   ├── settings.py ──────────── SystemSettings
│   ├── mail.py ──────────────── MailLog
│   ├── project.py ───────────── Project, ClockPendingFichaje
│   └── clock_settings.py ────── ClockSettings, EmployeeInboundDocument
│
├── schemas/ ─────────────────── Pydantic request/response (≠ tablas)
│   ├── auth.py / models.py ──── Login, UserMe, EmployeeRead…
│   ├── documents.py ─────────── DocumentDeliveryRead, DocumentTypeRead…
│   ├── signature.py ─────────── SignatureEnvelopeRead, PublicSignerMeta…
│   ├── legal.py ─────────────── LegalDocumentRead, EmployeeLegalStatusRead…
│   └── [resto: tenant, ai, billing, incident, reports, whatsapp…]
│
├── routers/ ─────────────────── FastAPI endpoints
│   ├── api.py ───────────────── Aggregator: public + protected routers
│   └── [ver sección 4]
│
└── services/ ────────────────── Lógica de negocio
    └── [ver sección 5]
```

---

## 4. Mapa de routers y rutas

```
POST /api/auth/login
GET  /api/auth/me

                    ┌── SIN AUTH ─────────────────────────────────────────────┐
GET  /api/public/pricing-plans
POST /api/public/signup
GET  /api/documents/{id}/preview                  ← imágenes públicas
GET  /api/employees/{id}/avatar                   ← avatar público
GET  /api/tenants/public/{slug}/branding          ← branding sin login
GET  /api/public/firma/{token}                    ← firma pública
POST /api/public/firma/{token}/start|verify|sign  ← flujo firma
GET  /api/public/incidencia/{token}               ← incidencia pública
POST /api/public/incidencia/{token}/justify
GET  /api/legal/public/token/{token}              ← legal por WhatsApp
POST /api/legal/public/token/{token}/accept/{doc}
POST /api/webhook/whatsapp/{slug}                 ← webhook goWA
POST /api/webhooks/stripe                         ← webhook Stripe
POST /api/webhooks/lemon-squeezy                  ← webhook Lemon Squeezy
                    └─────────────────────────────────────────────────────────┘

                    ┌── CON AUTH (JWT) ────────────────────────────────────────┐
GET/POST/PATCH/DELETE /api/employees/…
GET/POST/PATCH        /api/clock-ins/…
GET/PUT               /api/clock-settings/…
GET/POST/PATCH        /api/breaks/…
GET/POST/PATCH        /api/incidents/…
GET/POST/PATCH/DELETE /api/leave-requests/…
GET/POST/PATCH/DELETE /api/leave-types/…
GET/PUT               /api/employees/{id}/leave-balances/…
GET/POST/PATCH/DELETE /api/shifts/…
GET/POST/PATCH/DELETE /api/documents/…
GET/POST/PATCH        /api/signatures/…
GET/POST/PATCH/DELETE /api/legal/…
GET/POST/PATCH/DELETE /api/groups/…
GET/POST              /api/org/…
GET/POST/PATCH/DELETE /api/projects/…
GET                   /api/reports/…
GET/PUT               /api/settings/…
GET/POST/PATCH/DELETE /api/tenants/…
GET/POST/PATCH        /api/notifications/…
                    └─────────────────────────────────────────────────────────┘

                    ┌── PLATFORM ADMIN (/api/platform/…) ─────────────────────┐
POST /api/platform/auth/login
GET  /api/platform/auth/me
GET/POST/PATCH/DELETE /api/platform/tenants/…
GET/POST/PATCH        /api/platform/users/…
GET/POST/PATCH        /api/platform/pricing-plans/…
GET/POST/PATCH        /api/platform/discounts/…
GET/POST/PATCH/DELETE /api/platform/ai/…
GET/PUT/POST          /api/platform/whatsapp/…
GET/PUT/POST          /api/platform/mail/…
GET/POST              /api/platform/stripe/…
POST                  /api/platform/ls/sync-plan/{plan_id}
GET                   /api/platform/ls/payments
POST                  /api/platform/purge/{tenant_id}
                    └─────────────────────────────────────────────────────────┘
```

---

## 5. Mapa de servicios (lógica de negocio)

```
services/
│
├── FICHAJES & ASISTENCIA
│   ├── clock_service.py ─────────── register_clock(), get_day_clock()
│   ├── clock_settings_service.py ── get_or_create_settings(), inbound_name()
│   ├── clock_reminder_service.py ── run_clock_reminders(), run_incident_reminders()
│   ├── clock_report_service.py ──── generate_day_report()
│   ├── clock_pending_service.py ──── get_pending(), set_pending(), clear_pending()
│   └── clock_incident_hook.py ────── trigger_incident(), should_notify_whatsapp()
│
├── PERMISOS & PARADAS
│   ├── leave_service.py ─────────── create_leave_request(), get_remaining_days()
│   ├── break_service.py ─────────── register_break(), get_breaks()
│   └── daily_summary_service.py ──── build_daily_summary()
│
├── INCIDENCIAS
│   └── incident_service.py ──────── create_incident(), apply_clock_correction()
│                                    check_missing_clock_in(), check_missing_clock_out()
│                                    submit_employee_justification(), add_note()
│                                    get_pending_justification_incidents()
│                                    build_whatsapp_incident_message()
│
├── DOCUMENTOS
│   ├── document_service.py ──────── create_delivery(), store_upload_file()
│   ├── document_zip_service.py ───── create_zip()
│   └── document_expiry_notify_service.py ─ check_expiry(), send_notifications()
│
├── FIRMAS ELECTRÓNICAS
│   ├── signature_service.py ─────── create_envelope(), public_sign()
│   ├── signature_pdf.py ─────────── generate_signature_pdf(), embed_signature()
│   ├── signature_tokens.py ──────── create_signer_token(), verify_signer_token()
│   ├── signature_notify.py ──────── notify_signers(), send_invitation()
│   └── signature_audit.py ───────── log_event()
│
├── TEXTOS LEGALES
│   ├── legal_service.py ─────────── employee_legal_status(), accept_document()
│   │                                create_whatsapp_token(), validate_token()
│   │                                generate_acceptance_certificate()
│   └── legal_pdf_service.py ─────── generate_combined_acceptance_pdf()
│                                    store_combined_acceptance_pdf()
│
├── EMPLEADOS & ORGANIZACIÓN
│   ├── employee_bulk_import_service.py ─ bulk_import_employees()
│   ├── employee_onboarding_service.py ── onboard_employee(), build_welcome_message()
│   ├── org_service.py ────────────────── employee_ids_in_scope(), get_org_tree()
│   ├── scope_service.py ───────────────── is_read_own_only()
│   ├── work_schedule.py ───────────────── normalize_employee_schedule()
│   └── payroll_bulk_service.py ─────────── bulk_upload_payrolls()
│
├── NOTIFICACIONES
│   └── notification_service.py ──── create_notification(), notify_supervisor()
│
├── WHATSAPP / goWA
│   ├── gowa_client.py ───────────── GoWAClient (REST calls a :3000)
│   ├── gowa_service.py ──────────── send_text(), send_link(), send_text_sync()
│   ├── gowa_provisioner.py ──────── create_account(), link_tenant()
│   ├── webhook_service.py ───────── WebhookService.process() ← punto central
│   ├── whatsapp_nlu.py ──────────── classify_intent(), is_affirmative_reply()
│   ├── whatsapp_format.py ───────── Mensajes WA formateados
│   └── whatsapp_permission_service.py ─ check_whatsapp_access()
│
├── IA & OLLAMA
│   ├── ollama_service.py ────────── OllamaService.generate(), classify_intent()
│   ├── ai_conversation_service.py ── route_intent(), execute_rule()
│   ├── ai_config_service.py ─────── create_rule(), get_rules(), reorder_rules()
│   └── ai_usage_service.py ──────── record_usage(), get_usage_stats()
│
├── FACTURACIÓN
│   ├── billing_service.py ───────── calculate_amount(), create_invoice()
│   ├── billing_read.py ──────────── get_tenant_billing()
│   ├── stripe_service.py ────────── create_payment_intent(), sync_subscription()
│   ├── stripe_simulation.py ─────── simulate_payment()
│   ├── lemon_squeezy_service.py ─── sync_plan_to_ls(), create_checkout()
│   │                                handle_webhook_event(), verify_webhook_signature()
│   ├── invoice_service.py ───────── generate_invoice_for_ls_payment()
│   └── pricing_service.py ───────── calculate_tenant_price()
│
├── RBAC & ACCESO
│   └── rbac_service.py ──────────── create_group(), update_group_permissions()
│
├── INFORMES
│   └── reports_service.py ───────── get_chronological_report(), get_summary_report()
│
└── PLATAFORMA & UTILIDADES
    ├── mail_service.py ──────────── send_email()
    ├── settings_service.py ──────── get_settings(), test_ollama(), test_gowa()
    ├── unified_login.py ─────────── unified_login() (cross-tenant)
    ├── signup_service.py ────────── create_tenant_signup()
    ├── tenant_delete.py / tenant_purge.py
    ├── slug.py / code_generator.py / geocoding.py / id_document.py
    └── inbound_pending_service.py
```

---

## 6. Árbol de rutas del frontend

```
/  [MarketingLayout]
├── /                   → HomePage          (landing)
├── /registro           → SignupPage         (alta tenant)
├── /registro/pago-*    → SignupSimulatePage
└── /registro/ok        → SignupSuccessPage

/firmar/:token          → SignDocumentPage   (firma pública, sin login)
/legal/:token           → LegalTokenPage     (legales vía WhatsApp, sin login)
/justificar-incidencia/:token → JustifyIncidentPage (sin login)

/acceso                 → LoginPage          (login unificado)

/admin  [PlatformProtectedRoute] [PlatformLayout]
├── /                   → PlatformPage       (dashboard plataforma)
├── /usuarios           → PlatformUsersPage
├── /tarifas            → PlatformPricingPage
├── /descuentos         → PlatformDiscountsPage
├── /cobros             → PlatformStripePage
├── /whatsapp           → PlatformWhatsAppPage
├── /mail               → PlatformMailPage
├── /ia                 → PlatformAIPage
└── /purgar             → PlatformPurgePage

/app  [ProtectedRoute] [Layout] ← sidebar + topbar
├── /                   → Dashboard
├── /fichajes           → ClockInsPage       (registro de jornada)
├── /fichajes/config    → ClockSettingsPage  (reglas de validación)
├── /paradas            → BreaksPage         (descansos)
├── /incidencias        → IncidentsPage      (faltas, retrasos…)
├── /permisos           → LeaveRequestsPage  (vacaciones, permisos)
├── /turnos             → ShiftsPage         (configuración de turnos)
├── /empleados          → EmployeesPage      (ficha empleado, CRUD)
├── /organizacion       → OrganizationPage   (empresas, centros, deptos)
├── /organigrama        → OrgChartPage
├── /proyectos          → ProjectsPage
├── /informes           → ReportsPage        (cronológico + resumen)
├── /documentos         → DocumentsPage      (nóminas, contratos…)
├── /firmas             → SignaturesPage      (sobres de firma)
├── /legal              → LegalPage          (textos legales)
├── /grupos             → GroupsPage         (RBAC)
└── /cuenta             → AccountPage        (perfil + configuración)
```

---

## 7. Mapa de componentes frontend

```
src/components/
│
├── LAYOUT
│   ├── Layout.tsx ──────────────── Sidebar + topbar + OrgSelector
│   ├── PlatformLayout.tsx ──────── Layout del panel admin
│   ├── MarketingLayout.tsx ─────── Layout de la landing page
│   └── ProtectedRoute.tsx ──────── Guard: redirige a /acceso si no hay JWT
│
├── TABLAS DE DATOS
│   ├── DataTable.tsx ───────────── Wrapper de Tabulator (columnas, paginación)
│   ├── TableToolbar.tsx ────────── Búsqueda + filtros sobre DataTable
│   └── TableBulkImport.tsx ─────── Modal importación CSV masiva
│
├── MODALES & OVERLAYS
│   ├── Modal.tsx ───────────────── Modal genérico (wide / xlarge / tall)
│   ├── FilePreviewModal.tsx ─────── Visor PDF/imagen con auth (blob URL)
│   ├── LegalAcceptanceModal.tsx ─── Aceptación de textos legales obligatorios
│   └── TenantAccountSheet.tsx ───── Panel configuración tenant (slide-over)
│
├── EMPLEADOS
│   └── EmployeeProfileTabs.tsx ──── Pestañas ficha: datos / fichajes / permisos
│                                    / incidencias / documentos / firmas
│
├── FIRMA ELECTRÓNICA
│   └── SignatureCanvas.tsx ──────── Canvas de firma manuscrita
│
├── FICHEROS & UPLOAD
│   └── FileDropzone.tsx ─────────── Drag-and-drop upload
│
├── NOTIFICACIONES
│   ├── NotificationBell.tsx ──────── Campana + badge con count
│   └── ToastContainer.tsx ─────────── Toasts (éxito / error / info)
│
├── ORGANIZACIÓN
│   └── OrgSelector.tsx ─────────────── Selector empresa / centro / depto
│
├── CONFIGURACIÓN & TURNOS
│   └── WorkScheduleEditor.tsx ──────── Editor de horario semanal por tramos
│
├── FACTURACIÓN
│   ├── TenantBillingTab.tsx ─────────── Billing + suscripción
│   ├── SubscriptionSummaryCard.tsx ───── Tarjeta estado suscripción
│   └── InvoiceHistoryTable.tsx ────────── Tabla de facturas
│
├── IA & WHATSAPP
│   ├── TenantAIUsagePanel.tsx ──────────── Panel uso de IA
│   └── WhatsAppPanel.tsx ───────────────── QR + estado sesión goWA
│
└── MARCA
    ├── BrandLogo.tsx ──────────── Logo (tenant-customizable)
    └── PageHeader.tsx ─────────── Cabecera de página (título + acción)
```

---

## 8. Flujo de datos: fichaje por WhatsApp

```
Empleado escribe "entrada" en WA
           │
           ▼
    goWA :3000
    POST /webhook/whatsapp/{slug}
           │
           ▼
    webhook_service.py → WebhookService.process()
           │
           ├─ [1] ¿Empleado conocido? ──No──▶ "No estás registrado"
           │        (por teléfono)
           ├─ [2] ¿Legales pendientes? ──Sí──▶ Crear LegalToken (5min)
           │                                     Enviar link WA
           │                                     RETURN
           ├─ [3] ¿Primera vez? ──Sí──▶ Mensaje bienvenida
           │
           ├─ [1b] ¿Pending justificación activo?
           │         → _complete_whatsapp_justification()
           │         → submit_employee_justification()
           │         RETURN
           │
           ├─ [1c] Detectar "justificar [texto]"
           │         → _handle_whatsapp_justification()
           │         RETURN
           │
           ├─ [4] Clasificar intent (Ollama NLU)
           │        "entrada" → CLOCK_IN
           │
           └─ [5] Ejecutar acción
                    ClockService.register_clock(in/out)
                    → NotificationService (si hay incidencia)
                    → GoWAService.send_text("Fichaje registrado…")
```

### Flujo de justificación de incidencias por WhatsApp

```
_omission_incident_scheduler (cada 15 min)
  → check_missing_clock_in() / check_missing_clock_out()
  → Crea Incident(status="pending_justification", public_token=...)
  → GoWAService.send_text("⚠️ Incidencia... Responde justificar ...")

Empleado responde "justificar [texto]"
  → _handle_whatsapp_justification()
       ├─ 0 incidencias → "No tienes incidencias pendientes"
       ├─ 1 incidencia + texto → submit_employee_justification()
       ├─ 1 incidencia + sin texto → pending(awaiting_incident_justification=True)
       │     Siguiente mensaje → _complete_whatsapp_justification()
       └─ N incidencias → lista numerada
             "justificar 2: texto" → resuelve incidencia #2
```

---

## 9. Background schedulers (tareas periódicas)

Tres tareas `asyncio` arrancadas en el `lifespan` del servidor:

| Scheduler | Intervalo | Función |
|---|---|---|
| `_reminder_scheduler` | 5 min | Recordatorios de fichaje pendiente por WA (inicio: 60s) |
| `_omission_incident_scheduler` | 15 min | Detecta omisión de entrada/salida → crea incidencia + WA; lanza recordatorios de incidencias pendientes (inicio: 90s) |
| `_pending_cleanup_scheduler` | 60 seg | Limpia `ClockPendingFichaje` expirados: 3 min estándar, 60 min para `awaiting_incident_justification` |

El scheduler de omisión evalúa para cada tenant activo → cada empleado activo:
- `check_missing_clock_in()`: si no hay fichaje hoy y han pasado `missing_clock_in_hours` desde el inicio de jornada
- `check_missing_clock_out()`: si hay un fichaje de entrada sin cerrar de más de `missing_clock_out_hours`

Ambas funciones excluyen días de permiso aprobado (`LeaveRequest.APPROVED`) y deduplicamos por `(employee_id, incident_date, incident_type)` para no crear incidencias duplicadas.

---

## 10. Flujo de firma electrónica

```
Admin crea sobre (SignatureEnvelope)
  → POST /api/signatures/
  → signature_service.create_envelope()
       │ genera SignatureSigner por cada firmante
       │ genera SignatureOtp (token temporal)
       └─ signature_notify.send_invitation()
            → goWA.send_link() o mail_service.send_email()

Firmante recibe link /firmar/:token
  → SignDocumentPage (público, sin auth)
       │ GET /api/public/firma/:token  ← metadatos
       │ POST .../start                ← solicitar OTP
       │   → SMS/WA con código 6 dígitos
       │ POST .../verify-otp           ← validar código
       │ POST .../sign {signature_svg} ← firma + PDF
       │   → signature_pdf.embed_signature()
       │   → signature_audit.log_event()
       └── "Firmado correctamente"

GET /api/signatures/{id}/signed      ← descargar PDF firmado
GET /api/signatures/{id}/certificate ← descargar certificado
```

---

## 11. Flujo de textos legales

```
WhatsApp entrante (cualquier mensaje)
           │
           ▼
  legal_service.employee_legal_status()
           │
     ┌─────┴─────┐
   all_ok      pendientes
     │              │
     │         create_whatsapp_token() (TTL=5min)
     │         goWA.send_link( /legal/:token )
     │         RETURN (no procesar mensaje)
     │
     ▼ (flujo normal de fichaje/consulta)

Empleado abre /legal/:token
  → LegalTokenPage (pública)
       │ GET /api/legal/public/token/:token
       │   → validate_token() + employee_legal_status()
       │   Muestra docs pendientes uno a uno
       │ POST .../accept/:document_id  (por cada doc)
       │   → accept_document_with_pdf()
       │   Si remaining==0:
       │     → generate_acceptance_certificate()  ← PDF combinado (todos los docs)
       │     → DocumentDelivery creado en /documentos
       └────→ goWA.send_text("Has aceptado todos los textos…")

Aceptación desde la app web (LegalAcceptanceModal)
  → POST /api/legal/documents/:id/accept
       → accept_document_with_pdf()
       → generate_acceptance_certificate() si all_ok
```

---

## 12. Modelo de permisos (RBAC)

```
ROLES (jerarquía aproximada de acceso)
  admin / tenant_admin  ──▶ acceso total
  manager               ──▶ gestión de equipo
  supervisor            ──▶ supervisión de equipo (lectura extendida)
  labor_inspector       ──▶ solo lectura de fichajes y normativa
  employee              ──▶ solo sus propios datos

PERMISSION GROUPS (personalizables por tenant)
  GroupTemplate ──▶ define conjunto de permisos reutilizables
  UserGroup     ──▶ asigna GroupTemplate a un Employee

PERMISOS GRANULARES (ejemplos)
  employees.read / employees.write / employees.create_own
  clock_ins.read / clock_ins.write / clock_ins.create_own
  leave.read / leave.write / leave.approve / leave.create_own
  documents.read / documents.write / documents.bulk
  signatures.read / signatures.write
  legal.read / legal.write
  settings.read / settings.write
  tenant.billing

EVALUACIÓN (core/permissions.py)
  require_permission(Permission.READ, "employees")
    └─ get_employee_permissions(session, user_id, tenant_id)
         └─ roles + grupos → set de permisos → check
```

---

## 13. Esquema de base de datos (tablas principales)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MULTI-TENANT                                                            │
│                                                                          │
│  tenants ──┬── companies ──┬── work_centers ──┬── departments           │
│            │               │                  └── employees              │
│            │               └── employees                                 │
│            ├── pricing_plans (ls_product_id, ls_variant_id_monthly/annual)│
│            ├── subscriptions (ls_subscription_id, payment_failure_count) │
│            ├── billing_methods                                           │
│            ├── stripe_payments       (pagos vía Stripe)                  │
│            └── lemon_squeezy_payments (pagos vía Lemon Squeezy)         │
│                                                                          │
│  (tenants también tiene: ls_customer_id, ls_customer_portal_url)        │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  EMPLEADOS & ASISTENCIA                                                  │
│                                                                          │
│  employees ──┬── clock_ins (inmutables)                                  │
│              ├── work_breaks                                             │
│              ├── leave_requests ──── leave_types                         │
│              ├── employee_leave_balances ── leave_types                  │
│              ├── shift_assignments ──── shift_configurations             │
│              └── clock_pending_fichajes (pending_meta para justificación)│
│                                                                          │
│  (employees también tiene: last_incident_reminder_at)                   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  DOCUMENTOS & FIRMAS                                                     │
│                                                                          │
│  document_deliveries ──┬── document_types                               │
│                        └── document_tags (M2M: document_delivery_tags)  │
│                                                                          │
│  signature_envelopes ──┬── signature_signers ──── signature_otps        │
│                        ├── signature_events                             │
│                        └── signature_notifications                      │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  LEGALES                                                                 │
│                                                                          │
│  legal_documents ──── legal_acceptances (employee + doc + channel)      │
│  legal_tokens (TTL 5min, para WA)                                       │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  INCIDENCIAS                                                             │
│                                                                          │
│  incidents ──── incident_auto_rules                                      │
│                   (late_entrada: grace_minutes, enabled, notify_wa, ...)  │
│                   (missing_clock_in: hours, enabled, notify_wa, ...)     │
│                   (missing_clock_out: hours, enabled, notify_wa, ...)    │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  IA & WHATSAPP                                                           │
│                                                                          │
│  ai_conversation_rules ──── ai_profile_actions ──── ai_actions          │
│  ai_whatsapp_messages                                                   │
│  ai_usage_records                                                        │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  PLATAFORMA                                                              │
│                                                                          │
│  platform_users                                                          │
│  system_settings (Ollama URL, goWA URL, SMTP…)                         │
│  mail_logs                                                               │
│  notifications ──── notification_preferences                            │
│  projects                                                                │
│  group_templates ──┬── user_groups                                      │
│                    └── employee_groups                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Stack tecnológico completo

| Capa | Tecnología | Versión |
|---|---|---|
| Frontend framework | React | 19 |
| Frontend router | React Router | 7 |
| Frontend build | Vite + Bun | 6 / latest |
| Frontend tables | Tabulator | 6.3 |
| Frontend PDF export | jspdf + jspdf-autotable | 2.5 / 3.8 |
| Frontend Excel export | xlsx | 0.18 |
| Backend framework | FastAPI | 0.115 |
| Backend ORM | SQLModel (SQLAlchemy + Pydantic) | 0.0.22 |
| Backend validation | Pydantic v2 | 2.9 |
| Backend server | Uvicorn | 0.32 |
| Base de datos | PostgreSQL | 16 |
| DB driver | psycopg3 | 3.2 |
| Auth | JWT (python-jose) + bcrypt | — |
| PDF backend | reportlab + pypdf + Pillow | 4.2 / 5 / 10 |
| IA local | Ollama | llama3.2 |
| WhatsApp | goWA multidevice | latest |
| Pagos (alternativo) | Stripe | 11 |
| Pagos (principal) | Lemon Squeezy | v1 API |
| Proxy/SSL | Traefik | v2.11 |
| Contenedores | Docker Compose | — |
| Frontend server | Nginx | alpine |

---

## 15. Infraestructura Docker

```
docker-compose.yml
│
├── hrm-postgres  (postgres:16-alpine)
│     Puerto: 5432
│     Bind mount: ./data/postgres → /var/lib/postgresql/data
│
├── hrm-ollama  (ollama/ollama)
│     Puerto: 11434
│     Volumen nombrado: ollama_data (modelos grandes, re-descargables)
│
├── hrm-gowa  (go-whatsapp-web-multidevice)
│     Puerto: 3000
│     Bind mount: ./data/gowa → /app/storages (sesiones WhatsApp)
│
├── hrm-backend  (build local ./backend)
│     Puerto: 8000
│     Bind mount: ./data/uploads → /app/uploads (documentos PDF/img)
│
├── hrm-frontend  (nginx:alpine)
│     Puerto: 80 · Volumen: frontend/dist
│     nginx.conf: SPA fallback + proxy /api → backend:8000
│
└── hrm-traefik  (traefik:v2.11) [producción]
      Puertos: 80, 443 · SSL: Let's Encrypt

Red: hrm-net (bridge)
```

---

## 16. Persistencia y migración de datos

### Estructura en el host

```
data/                          ← excluido de git (.gitignore)
├── postgres/                  ← datos PostgreSQL (bind mount)
│     chown 70:70              ← uid del usuario postgres en alpine
├── uploads/                   ← documentos PDF, imágenes, firmas
├── gowa/                      ← sesiones WhatsApp (no perder en migración)
└── backups/                   ← dumps SQL + tarballs de uploads
      db_YYYYMMDD_HHMMSS.sql.gz
      uploads_YYYYMMDD_HHMMSS.tar.gz
```

### Backup manual

```bash
bash scripts/backup.sh
# Crea: data/backups/db_TIMESTAMP.sql.gz + uploads_TIMESTAMP.tar.gz
# Retención: 7 días (configurable con BACKUP_KEEP_DAYS=30)
```

### Backup automático (cron host)

```bash
# crontab -e
0 3 * * * cd /var/www/alcurro && bash scripts/backup.sh >> data/backups/backup.log 2>&1
```

### Restaurar desde backup

```bash
bash scripts/restore.sh data/backups/db_20260607_030000.sql.gz
```

### Migrar a otro servidor

```bash
# 1. En el servidor origen — backup
bash scripts/backup.sh

# 2. Copiar al nuevo servidor
rsync -avz data/ nuevo-servidor:/var/www/alcurro/data/
rsync -avz docker-compose.yml .env nuevo-servidor:/var/www/alcurro/

# 3. En el nuevo servidor — arrancar
chown 70:70 /var/www/alcurro/data/postgres
docker compose up -d

# 4. Verificar
curl http://localhost:8000/health
```

### Notas importantes

- **`data/postgres/`** requiere `chown 70:70` — uid del usuario `postgres` en Alpine Linux
- **goWA** (`data/gowa/`): contiene la sesión WhatsApp vinculada. Si se pierde, hay que escanear QR de nuevo
- **Ollama** usa volumen nombrado Docker (`ollama_data`) — los modelos son grandes y re-descargables; no necesitan backup
- **`data/` no se commitea a git** — contiene datos de producción. Hacer backup externo (S3, rsync, etc.)

---

## 17. Índice de documentación

| Documento | Contenido |
|---|---|
| `CLAUDE.md` | Guía de desarrollo para Claude Code (convenciones, patrones) |
| `docs/arquitectura.md` | **Este fichero** — mapa estructural completo |
| `docs/instalacion.md` | Instalación, Docker, migraciones iniciales |
| `docs/deploy.md` | Despliegue en producción (Traefik, SSL) |
| `docs/panel-cliente.md` | Manual del panel `/app` |
| `docs/admin-plataforma.md` | Manual del panel `/admin` |
| `docs/empleados-y-horarios.md` | Gestión de empleados y turnos |
| `docs/firmas-electronicas.md` | Firma electrónica: flujo completo |
| `docs/legal.md` | Sistema de textos legales y aceptación |
| `docs/correo-smtp.md` | Configuración de correo SMTP |
| `docs/stripe.md` | Stripe: claves, webhook, productos, checkout, producción |
| `docs/lemon-squeezy.md` | Lemon Squeezy: configuración, webhook, sincronización de planes |
| `docs/api.md` | Referencia de endpoints REST |
| `docs/AI_WHATSAPP.md` | IA, automatización WhatsApp e incidencias por WA |
| `scripts/backup.sh` | Backup PostgreSQL + uploads (manual o cron) |
| `scripts/restore.sh` | Restaurar BD desde archivo `.sql.gz` |
