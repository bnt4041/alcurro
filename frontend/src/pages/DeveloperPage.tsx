import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

interface ApiKeyCreated extends ApiKey {
  full_key: string;
}

interface Webhook {
  id: string;
  url: string;
  description: string | null;
  events: string[];
  secret: string;
  is_active: boolean;
  created_at: string;
  last_triggered_at: string | null;
  failure_count: number;
}

interface WebhookDelivery {
  id: string;
  event_type: string;
  status: string;
  response_status: number | null;
  attempts: number;
  created_at: string;
  delivered_at: string | null;
}

const ALL_EVENTS = [
  { group: "Empleados",   events: ["employee.created", "employee.updated", "employee.deactivated"] },
  { group: "Fichajes",    events: ["clockin.created", "clockin.updated", "break.created"] },
  { group: "Permisos",    events: ["leave.requested", "leave.approved", "leave.rejected"] },
  { group: "Incidencias", events: ["incident.created", "incident.managed"] },
  { group: "Documentos",  events: ["document.delivered", "document.signed", "signature.completed"] },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtDateTime(iso: string) {
  return new Date(iso).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function CopyBtn({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button type="button" className="dev-copy-btn" onClick={copy} title="Copiar">
      <span className="material-symbols-outlined">{copied ? "check" : "content_copy"}</span>
    </button>
  );
}

function SecretReveal({ secret }: { secret: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="dev-secret-row">
      <code className="dev-code">{visible ? secret : "••••••••••••••••••••••••"}</code>
      <button type="button" className="dev-copy-btn" onClick={() => setVisible(v => !v)} title={visible ? "Ocultar" : "Mostrar"}>
        <span className="material-symbols-outlined">{visible ? "visibility_off" : "visibility"}</span>
      </button>
      <CopyBtn value={secret} />
    </span>
  );
}

// ─── API Keys tab ─────────────────────────────────────────────────────────────

function ApiKeysTab() {
  const { notify } = useToast();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [revealed, setRevealed] = useState<ApiKeyCreated | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setKeys(await api.get<ApiKey[]>("/developer/api-keys")); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const created = await api.post<ApiKeyCreated>("/developer/api-keys", { name: newName.trim() });
      setNewName("");
      setRevealed(created);
      load();
    } catch (err) {
      notify(String(err), "error");
    } finally {
      setCreating(false);
    }
  };

  const revoke = async (id: string, name: string) => {
    if (!confirm(`¿Revocar la clave "${name}"? Esta acción no se puede deshacer.`)) return;
    try {
      await api.delete(`/developer/api-keys/${id}`);
      notify("Clave revocada", "success");
      load();
    } catch (err) {
      notify(String(err), "error");
    }
  };

  return (
    <div className="dev-section">
      <div className="dev-section__intro">
        <p>
          Las claves de API permiten acceso programático a los endpoints de alcurro.
          Tratalas como contraseñas: no las expongas en código cliente ni repositorios.
        </p>
        <div className="dev-callout dev-callout--info">
          <span className="material-symbols-outlined">info</span>
          <span>
            URL base de la API:{" "}
            <code className="dev-code">https://alcurro.es/api</code> — incluye la clave en{" "}
            <code className="dev-code">Authorization: Bearer ak_…</code> en cada petición.
          </span>
        </div>
      </div>

      <form className="dev-create-form" onSubmit={create}>
        <input
          placeholder="Nombre descriptivo — ej: Integración ERP"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          required
          className="dev-input"
        />
        <button type="submit" className="btn btn-primary" disabled={creating}>
          {creating ? "Creando…" : "Crear clave"}
        </button>
      </form>

      {loading ? (
        <p className="muted">Cargando…</p>
      ) : keys.length === 0 ? (
        <p className="muted">Aún no hay claves de API. Crea una arriba.</p>
      ) : (
        <div className="dev-table-wrap">
          <table className="dev-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Prefijo</th>
                <th>Creada</th>
                <th>Último uso</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.map(k => (
                <tr key={k.id}>
                  <td><strong>{k.name}</strong></td>
                  <td><code className="dev-code">{k.key_prefix}</code></td>
                  <td className="muted small">{fmtDate(k.created_at)}</td>
                  <td className="muted small">{k.last_used_at ? fmtDateTime(k.last_used_at) : "—"}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm dev-revoke-btn"
                      onClick={() => revoke(k.id, k.name)}
                    >
                      Revocar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal title="Clave de API creada" open={!!revealed} onClose={() => setRevealed(null)}>
        {revealed && (
          <div className="dev-reveal">
            <div className="dev-callout dev-callout--warn">
              <span className="material-symbols-outlined">warning</span>
              <span>Esta es la única vez que verás la clave completa. Cópiala ahora.</span>
            </div>
            <p className="muted small" style={{ marginTop: "0.75rem" }}>Clave para <strong>{revealed.name}</strong>:</p>
            <div className="dev-key-box">
              <code>{revealed.full_key}</code>
              <CopyBtn value={revealed.full_key} />
            </div>
            <div className="form-actions" style={{ marginTop: "1.25rem" }}>
              <button type="button" className="btn btn-primary" onClick={() => setRevealed(null)}>
                Entendido, ya la guardé
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ─── Webhooks tab ─────────────────────────────────────────────────────────────

function WebhooksTab() {
  const { notify } = useToast();
  const [hooks, setHooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [editTarget, setEditTarget] = useState<Webhook | "new" | null>(null);
  const [deliveryTarget, setDeliveryTarget] = useState<Webhook | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [testing, setTesting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setHooks(await api.get<Webhook[]>("/developer/webhooks")); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openDeliveries = async (wh: Webhook) => {
    setDeliveryTarget(wh);
    const rows = await api.get<WebhookDelivery[]>(`/developer/webhooks/${wh.id}/deliveries`);
    setDeliveries(rows);
  };

  const test = async (wh: Webhook) => {
    setTesting(wh.id);
    try {
      const r = await api.post<{ status: string; response_status: number | null }>(
        `/developer/webhooks/${wh.id}/test`, {}
      );
      if (r.status === "success") notify(`Test enviado correctamente (HTTP ${r.response_status})`, "success");
      else notify(`Test fallido (HTTP ${r.response_status ?? "sin respuesta"})`, "error");
      load();
    } catch (err) {
      notify(String(err), "error");
    } finally {
      setTesting(null);
    }
  };

  const del = async (wh: Webhook) => {
    if (!confirm(`¿Eliminar el webhook "${wh.url}"?`)) return;
    try {
      await api.delete(`/developer/webhooks/${wh.id}`);
      notify("Webhook eliminado", "success");
      load();
    } catch (err) { notify(String(err), "error"); }
  };

  return (
    <div className="dev-section">
      <div className="dev-section__intro">
        <p>
          alcurro enviará un POST a tu URL cada vez que ocurra un evento. El payload viene
          firmado con HMAC-SHA256 para que puedas verificar su autenticidad.
        </p>
        <div className="dev-callout dev-callout--info">
          <span className="material-symbols-outlined">info</span>
          <span>
            Verifica la firma con la cabecera{" "}
            <code className="dev-code">X-Alcurro-Signature: sha256=…</code> usando el secreto del webhook.
          </span>
        </div>
      </div>

      <button type="button" className="btn btn-primary" onClick={() => setEditTarget("new")}>
        <span className="material-symbols-outlined">add</span>
        Nuevo webhook
      </button>

      {loading ? (
        <p className="muted" style={{ marginTop: "1rem" }}>Cargando…</p>
      ) : hooks.length === 0 ? (
        <p className="muted" style={{ marginTop: "1rem" }}>Aún no hay webhooks.</p>
      ) : (
        <div className="dev-hook-list" style={{ marginTop: "1rem" }}>
          {hooks.map(wh => (
            <div key={wh.id} className={`dev-hook-card${wh.failure_count > 2 ? " dev-hook-card--warn" : ""}`}>
              <div className="dev-hook-card__top">
                <div className="dev-hook-card__url">
                  <span className="dev-status-dot dev-status-dot--ok" />
                  <code className="dev-code">{wh.url}</code>
                </div>
                <div className="dev-hook-card__actions">
                  <button type="button" className="btn btn-sm" disabled={testing === wh.id} onClick={() => test(wh)}>
                    {testing === wh.id ? "Enviando…" : "Test"}
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => openDeliveries(wh)}>
                    Historial
                  </button>
                  <button type="button" className="btn btn-sm" onClick={() => setEditTarget(wh)}>
                    Editar
                  </button>
                  <button type="button" className="btn btn-sm dev-revoke-btn" onClick={() => del(wh)}>
                    Eliminar
                  </button>
                </div>
              </div>
              {wh.description && <p className="dev-hook-card__desc muted small">{wh.description}</p>}
              <div className="dev-hook-card__meta">
                <div className="dev-event-chips">
                  {wh.events.map(e => <span key={e} className="dev-event-chip">{e}</span>)}
                </div>
                <span className="muted small">
                  {wh.last_triggered_at ? `Último envío ${fmtDateTime(wh.last_triggered_at)}` : "Sin envíos"}
                  {wh.failure_count > 0 && <span className="dev-fail-badge">{wh.failure_count} fallos</span>}
                </span>
              </div>
              <div className="dev-hook-card__secret">
                <span className="muted small">Secreto:</span>
                <SecretReveal secret={wh.secret} />
              </div>
            </div>
          ))}
        </div>
      )}

      {editTarget !== null && (
        <WebhookModal
          initial={editTarget === "new" ? null : editTarget}
          onSave={() => { load(); setEditTarget(null); }}
          onClose={() => setEditTarget(null)}
        />
      )}

      <Modal
        title={`Historial de entregas — ${deliveryTarget?.url ?? ""}`}
        open={!!deliveryTarget}
        onClose={() => setDeliveryTarget(null)}
      >
        {deliveries.length === 0 ? (
          <p className="muted">Sin entregas registradas.</p>
        ) : (
          <div className="dev-table-wrap">
            <table className="dev-table">
              <thead>
                <tr><th>Evento</th><th>Estado</th><th>HTTP</th><th>Fecha</th></tr>
              </thead>
              <tbody>
                {deliveries.map(d => (
                  <tr key={d.id}>
                    <td><code className="dev-code">{d.event_type}</code></td>
                    <td>
                      <span className={`dev-delivery-badge dev-delivery-badge--${d.status}`}>
                        {d.status}
                      </span>
                    </td>
                    <td className="muted small">{d.response_status ?? "—"}</td>
                    <td className="muted small">{fmtDateTime(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Modal>
    </div>
  );
}

function WebhookModal({
  initial,
  onSave,
  onClose,
}: {
  initial: Webhook | null;
  onSave: () => void;
  onClose: () => void;
}) {
  const { notify } = useToast();
  const [url, setUrl] = useState(initial?.url ?? "");
  const [desc, setDesc] = useState(initial?.description ?? "");
  const [events, setEvents] = useState<string[]>(initial?.events ?? []);
  const [saving, setSaving] = useState(false);

  const toggleEvent = (e: string) =>
    setEvents(prev => prev.includes(e) ? prev.filter(x => x !== e) : [...prev, e]);

  const toggleAll = () => {
    const all = ALL_EVENTS.flatMap(g => g.events);
    setEvents(events.length === all.length ? [] : all);
  };

  const save = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!url || events.length === 0) {
      notify("Indica una URL y al menos un evento", "error");
      return;
    }
    setSaving(true);
    try {
      const body = { url, description: desc || null, events };
      if (initial) await api.patch(`/developer/webhooks/${initial.id}`, body);
      else await api.post("/developer/webhooks", body);
      notify(initial ? "Webhook actualizado" : "Webhook creado", "success");
      onSave();
    } catch (err) {
      notify(String(err), "error");
    } finally {
      setSaving(false);
    }
  };

  const allSelected = events.length === ALL_EVENTS.flatMap(g => g.events).length;

  return (
    <Modal title={initial ? "Editar webhook" : "Nuevo webhook"} open onClose={onClose}>
      <form onSubmit={save} className="dev-wh-form">
        <label className="dev-label">
          URL de destino
          <input
            className="dev-input"
            type="url"
            placeholder="https://mi-app.com/webhooks/alcurro"
            value={url}
            onChange={e => setUrl(e.target.value)}
            required
          />
        </label>
        <label className="dev-label">
          Descripción (opcional)
          <input
            className="dev-input"
            placeholder="Para qué se usa este webhook"
            value={desc}
            onChange={e => setDesc(e.target.value)}
          />
        </label>

        <div className="dev-label">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Eventos a escuchar</span>
            <button type="button" className="btn btn-sm" onClick={toggleAll}>
              {allSelected ? "Desmarcar todos" : "Seleccionar todos"}
            </button>
          </div>
          <div className="dev-events-grid">
            {ALL_EVENTS.map(group => (
              <div key={group.group} className="dev-events-group">
                <span className="dev-events-group__title">{group.group}</span>
                {group.events.map(ev => (
                  <label key={ev} className="dev-event-check">
                    <input
                      type="checkbox"
                      checked={events.includes(ev)}
                      onChange={() => toggleEvent(ev)}
                    />
                    <code>{ev}</code>
                  </label>
                ))}
              </div>
            ))}
          </div>
        </div>

        <div className="form-actions" style={{ marginTop: "1.5rem" }}>
          <button type="button" className="btn" onClick={onClose}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Guardando…" : initial ? "Guardar cambios" : "Crear webhook"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ─── Docs tab ─────────────────────────────────────────────────────────────────

interface EndpointDef {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  description: string;
  query?: string;
}

interface SchemaDef {
  label: string;
  method: "GET" | "POST" | "PATCH" | "DELETE";
  description?: string;
  queryParams?: { name: string; type: string; required: boolean; description: string }[];
  request?: string;
  response: string;
  status?: string;
}

interface DocSectionDef {
  id: string;
  title: string;
  icon: string;
  endpoints: EndpointDef[];
  schemas: SchemaDef[];
}

function SchemaBlock({ schema }: { schema: SchemaDef }) {
  const [tab, setTab] = useState<"request" | "response">(schema.request ? "request" : "response");
  const methodClass = `dev-method dev-method--${schema.method.toLowerCase()}`;
  return (
    <div className="dev-schema-block">
      <div className="dev-schema-block__head">
        <span className={methodClass}>{schema.method}</span>
        <code className="dev-schema-block__path">{schema.label.split(" — ")[0].replace(schema.method + " ", "")}</code>
        {schema.description && <span className="dev-schema-block__desc muted small">{schema.description}</span>}
      </div>

      {schema.queryParams && schema.queryParams.length > 0 && (
        <div className="dev-schema-block__params">
          <span className="dev-schema-label">Query params</span>
          <table className="dev-table dev-table--compact">
            <thead><tr><th>Param</th><th>Tipo</th><th>Req.</th><th>Descripción</th></tr></thead>
            <tbody>
              {schema.queryParams.map(p => (
                <tr key={p.name}>
                  <td><code className="dev-code">{p.name}</code></td>
                  <td><span className="dev-type-badge">{p.type}</span></td>
                  <td>{p.required ? <span className="dev-required">✓</span> : <span className="muted">—</span>}</td>
                  <td className="muted small">{p.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {schema.request ? (
        <>
          <div className="dev-schema-tabs">
            <button
              type="button"
              className={`dev-schema-tab${tab === "request" ? " is-active" : ""}`}
              onClick={() => setTab("request")}
            >
              Request body
            </button>
            <button
              type="button"
              className={`dev-schema-tab${tab === "response" ? " is-active" : ""}`}
              onClick={() => setTab("response")}
            >
              Response <span className="dev-status-chip">{schema.status ?? "200"}</span>
            </button>
          </div>
          <pre className="dev-pre dev-pre--schema">
            {tab === "request" ? schema.request : schema.response}
          </pre>
        </>
      ) : (
        <>
          <div className="dev-schema-tabs">
            <span className="dev-schema-tab is-active is-solo">
              Response <span className="dev-status-chip">{schema.status ?? "200"}</span>
            </span>
          </div>
          <pre className="dev-pre dev-pre--schema">{schema.response}</pre>
        </>
      )}
    </div>
  );
}

const DOC_SECTIONS: DocSectionDef[] = [
  {
    id: "auth",
    title: "URL base y autenticación",
    icon: "lock",
    endpoints: [],
    schemas: [
      {
        label: "URL base",
        method: "GET",
        description: "Todos los endpoints se sirven bajo esta URL",
        response: `https://alcurro.es/api

// Swagger interactivo (requiere sesión de administrador):
https://alcurro.es/api/docs`,
      },
      {
        label: "Cabeceras requeridas",
        method: "GET",
        description: "Incluir en cada petición",
        response: `Authorization: Bearer ak_TU_CLAVE_API
X-Company-Id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
Content-Type: application/json

// Opcionales — filtran el scope de datos devuelto
X-Work-Center-Id: <uuid>
X-Department-Id: <uuid>`,
      },
      {
        label: "Ejemplo completo (curl)",
        method: "GET",
        description: "Petición real lista para copiar",
        response: `curl https://alcurro.es/api/employees/lookup?ref=EMP001 \\
  -H "Authorization: Bearer ak_XXXXXXXXXXXXXX" \\
  -H "X-Company-Id: 3fa85f64-5717-4562-b3fc-2c963f66afa6"`,
      },
    ],
  },
  {
    id: "refs",
    title: "Referencias naturales (sin UUIDs)",
    icon: "link",
    endpoints: [
      { method: "GET", path: "/employees/lookup",  description: "Empleado por código, teléfono o email" },
      { method: "GET", path: "/leave-types",        description: "Listar tipos de permiso (para obtener IDs o nombres)" },
      { method: "GET", path: "/org/departments",    description: "Listar departamentos" },
      { method: "GET", path: "/documents/types",    description: "Listar tipos de documento" },
    ],
    schemas: [
      {
        label: "Concepto — employee_ref",
        method: "POST",
        description: "En fichajes, permisos e incidencias puedes identificar al empleado sin UUID",
        response: `// En lugar de buscar el UUID primero:
//   GET /employees?code=EMP001  →  obtienes el UUID
//   POST /clock-ins { "employee_id": "3fa85..." }
//
// Puedes usar directamente employee_ref:
POST /clock-ins
{
  "employee_ref": "EMP001",            // código de empleado
  "entrada_at": "2024-11-01T08:55:00"
}

// También acepta teléfono o email:
{ "employee_ref": "+34600000000" }
{ "employee_ref": "ana@empresa.com" }

// El mismo patrón existe en:
//   POST /leave-requests  →  employee_ref + leave_type_name
//   POST /incidents       →  employee_ref`,
      },
      {
        label: "GET /leave-types",
        method: "GET",
        description: "Catálogo de tipos de permiso — usa el 'name' en leave_type_name",
        response: `[
  { "id": "uuid-1", "name": "Vacaciones",   "paid": true,  "max_days": 22 },
  { "id": "uuid-2", "name": "Baja médica",  "paid": false, "max_days": null },
  { "id": "uuid-3", "name": "Permiso ERTE", "paid": true,  "max_days": 5 }
]

// Uso en POST /leave-requests:
{ "leave_type_name": "Vacaciones", ... }  // sin buscar el UUID`,
      },
      {
        label: "GET /org/departments",
        method: "GET",
        description: "Catálogo de departamentos de la empresa",
        response: `[
  { "id": "uuid-dept-1", "name": "Desarrollo",    "company_id": "..." },
  { "id": "uuid-dept-2", "name": "Administración","company_id": "..." },
  { "id": "uuid-dept-3", "name": "Ventas",        "company_id": "..." }
]`,
      },
      {
        label: "GET /documents/types",
        method: "GET",
        description: "Catálogo de tipos de documento",
        response: `[
  { "id": "uuid-dt-1", "name": "Nómina",    "sort_order": 1 },
  { "id": "uuid-dt-2", "name": "Contrato",  "sort_order": 2 },
  { "id": "uuid-dt-3", "name": "Formación", "sort_order": 3 }
]`,
      },
    ],
  },
  {
    id: "employees",
    title: "Empleados",
    icon: "group",
    endpoints: [
      { method: "GET",   path: "/employees/lookup",  description: "Buscar empleado por código, teléfono o email" },
      { method: "GET",   path: "/employees",         description: "Listar empleados" },
      { method: "GET",   path: "/employees/{id}",    description: "Obtener empleado por ID" },
      { method: "POST",  path: "/employees",         description: "Crear empleado" },
      { method: "PATCH", path: "/employees/{id}",    description: "Actualizar datos" },
    ],
    schemas: [
      {
        label: "GET /employees/lookup",
        method: "GET",
        description: "Encuentra un empleado por referencia natural — devuelve el objeto completo con su id",
        queryParams: [
          { name: "ref", type: "string", required: true, description: "employee_code (EMP001), teléfono (+34600…), email o UUID" },
        ],
        response: `// GET /employees/lookup?ref=EMP001
// GET /employees/lookup?ref=ana@empresa.com
// GET /employees/lookup?ref=+34600000000
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "full_name": "Ana García López",
  "employee_code": "EMP001",
  "phone": "+34600000000",
  "email": "ana@empresa.com",
  "role": "employee",
  ...
}`,
      },
      {
        label: "GET /employees",
        method: "GET",
        description: "Devuelve array de empleados. Combina filtros exactos y búsqueda libre.",
        queryParams: [
          { name: "q",        type: "string",  required: false, description: "Búsqueda libre (nombre, código, DNI, teléfono, email)" },
          { name: "phone",    type: "string",  required: false, description: "Teléfono exacto (+34600000000)" },
          { name: "code",     type: "string",  required: false, description: "Código exacto (EMP001, insensible a mayúsculas)" },
          { name: "email",    type: "string",  required: false, description: "Email exacto (insensible a mayúsculas)" },
          { name: "role",     type: "string",  required: false, description: "employee | supervisor | manager | tenant_admin" },
          { name: "active_only", type: "boolean", required: false, description: "Solo empleados activos" },
        ],
        response: `[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "company_id": "1e7c3d91-...",
    "department_id": null,
    "phone": "+34600000000",
    "email": "ana@empresa.com",
    "full_name": "Ana García López",
    "id_document": "12345678A",
    "employee_code": "EMP001",
    "role": "employee",
    "job_title": "Técnico",
    "supervisor_id": null,
    "vacation_days_balance": 22.0,
    "is_active": true,
    "avatar_url": "/api/employees/3fa8.../avatar",
    "work_start_time": "09:00",
    "work_end_time": "18:00",
    "work_days": [0, 1, 2, 3, 4],
    "weekly_hours": 40.0,
    "rotating_shift": false,
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-11-01T09:30:00"
  }
]`,
      },
      {
        label: "POST /employees",
        method: "POST",
        description: "Crear un empleado nuevo en la empresa activa",
        status: "201",
        request: `{
  "phone": "+34600000000",          // requerido, único por empresa
  "full_name": "Ana García López",  // requerido
  "id_document": "12345678A",       // requerido
  "email": "ana@empresa.com",       // opcional
  "employee_code": "EMP001",        // opcional, autogenerado si vacío
  "role": "employee",               // employee | supervisor | manager | tenant_admin
  "department_id": null,            // uuid del departamento
  "supervisor_id": null,            // uuid del supervisor
  "job_title": "Técnico",           // cargo
  "vacation_days_balance": 22.0,    // días de vacaciones asignados
  "work_start_time": "09:00",       // hora de entrada esperada
  "work_end_time": "18:00",         // hora de salida esperada
  "work_days": [0, 1, 2, 3, 4],    // 0=Lun, 1=Mar, ..., 6=Dom
  "weekly_hours": 40.0              // horas semanales contractuales
}`,
        response: `{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "company_id": "1e7c3d91-...",
  "phone": "+34600000000",
  "full_name": "Ana García López",
  "id_document": "12345678A",
  "employee_code": "EMP001",
  "role": "employee",
  "is_active": true,
  "vacation_days_balance": 22.0,
  "work_start_time": "09:00",
  "work_end_time": "18:00",
  "work_days": [0, 1, 2, 3, 4],
  "weekly_hours": 40.0,
  "created_at": "2024-11-01T10:00:00",
  "updated_at": "2024-11-01T10:00:00"
}`,
      },
      {
        label: "PATCH /employees/{id}",
        method: "PATCH",
        description: "Actualización parcial — solo los campos enviados se modifican",
        request: `{
  "job_title": "Senior Técnico",
  "department_id": "uuid-departamento",
  "vacation_days_balance": 25.0,
  "is_active": true
}`,
        response: `// Mismo objeto que POST /employees (EmployeeRead)
{
  "id": "3fa85f64-...",
  "full_name": "Ana García López",
  "job_title": "Senior Técnico",
  "vacation_days_balance": 25.0,
  ...
}`,
      },
    ],
  },
  {
    id: "clockins",
    title: "Fichajes",
    icon: "schedule",
    endpoints: [
      { method: "GET",   path: "/clock-ins",      description: "Listar fichajes", query: "?employee_id=&from=&to=" },
      { method: "POST",  path: "/clock-ins",      description: "Registrar entrada" },
      { method: "PATCH", path: "/clock-ins/{id}", description: "Registrar salida o corregir" },
    ],
    schemas: [
      {
        label: "GET /clock-ins",
        method: "GET",
        description: "Devuelve fichajes del scope activo (empresa, centro, depto)",
        queryParams: [
          { name: "employee_id", type: "uuid",   required: false, description: "Filtrar por empleado" },
          { name: "from",        type: "date",   required: false, description: "Desde fecha (YYYY-MM-DD)" },
          { name: "to",          type: "date",   required: false, description: "Hasta fecha (YYYY-MM-DD)" },
          { name: "limit",       type: "integer",required: false, description: "Máximo de resultados (default 100)" },
        ],
        response: `[
  {
    "id": "c7e3a1b2-...",
    "employee_id": "3fa85f64-...",
    "entrada_at": "2024-11-01T08:55:00",
    "salida_at": "2024-11-01T18:02:00",
    "latitude": 40.4168,
    "longitude": -3.7038,
    "address": "Calle Gran Vía 1, Madrid",
    "latitude_out": 40.4168,
    "longitude_out": -3.7038,
    "address_out": "Calle Gran Vía 1, Madrid",
    "source": "panel",
    "notes": null,
    "work_summary": "Reunión con cliente y desarrollo",
    "project_id": null,
    "project_name": null
  }
]`,
      },
      {
        label: "POST /clock-ins",
        method: "POST",
        description: "Registra una jornada. Usa employee_ref para evitar buscar el UUID.",
        status: "201",
        request: `{
  // Identificar al empleado — una de las dos opciones:
  "employee_id": "3fa85f64-...",      // opción A: UUID interno
  "employee_ref": "EMP001",           // opción B: código, teléfono o email

  "entrada_at": "2024-11-01T08:55:00",// requerido — ISO 8601
  "salida_at": null,                  // null si aún no ha salido
  "latitude": 40.4168,                // opcional — geolocalización entrada
  "longitude": -3.7038,
  "address": "Calle Gran Vía 1, Madrid",
  "source": "api",                    // panel | api | whatsapp
  "notes": "Entrada normal",          // texto libre
  "project_id": null                  // uuid del proyecto asociado
}`,
        response: `{
  "id": "c7e3a1b2-...",
  "employee_id": "3fa85f64-...",
  "entrada_at": "2024-11-01T08:55:00",
  "salida_at": null,
  "source": "api",
  "latitude": 40.4168,
  "longitude": -3.7038,
  "address": "Calle Gran Vía 1, Madrid",
  "latitude_out": null,
  "longitude_out": null,
  "address_out": null,
  "notes": "Entrada normal",
  "work_summary": null,
  "project_id": null,
  "project_name": null
}`,
      },
      {
        label: "PATCH /clock-ins/{id}",
        method: "PATCH",
        description: "Registra salida o corrige datos. Genera incidencia automáticamente.",
        request: `{
  "salida_at": "2024-11-01T18:02:00", // registrar salida
  "latitude_out": 40.4168,
  "longitude_out": -3.7038,
  "address_out": "Calle Gran Vía 1, Madrid",
  "work_summary": "Reunión con cliente y desarrollo de funcionalidades",
  "notes": "Salida normal"
}`,
        response: `// ClockInRead completo con los nuevos valores
{
  "id": "c7e3a1b2-...",
  "employee_id": "3fa85f64-...",
  "entrada_at": "2024-11-01T08:55:00",
  "salida_at": "2024-11-01T18:02:00",
  "work_summary": "Reunión con cliente y desarrollo de funcionalidades",
  ...
}`,
      },
    ],
  },
  {
    id: "leaves",
    title: "Permisos y vacaciones",
    icon: "beach_access",
    endpoints: [
      { method: "GET",  path: "/leave-requests",            description: "Listar solicitudes" },
      { method: "POST", path: "/leave-requests",            description: "Crear solicitud" },
      { method: "POST", path: "/leave-requests/{id}/approve", description: "Aprobar" },
      { method: "POST", path: "/leave-requests/{id}/reject",  description: "Rechazar" },
    ],
    schemas: [
      {
        label: "GET /leave-requests",
        method: "GET",
        queryParams: [
          { name: "status",      type: "string", required: false, description: "pending | approved | rejected" },
          { name: "employee_id", type: "uuid",   required: false, description: "Filtrar por empleado" },
          { name: "from",        type: "date",   required: false, description: "Fecha inicio desde (YYYY-MM-DD)" },
          { name: "to",          type: "date",   required: false, description: "Fecha inicio hasta (YYYY-MM-DD)" },
        ],
        response: `[
  {
    "id": "d9f2c4e1-...",
    "employee_id": "3fa85f64-...",
    "start_date": "2024-12-23",
    "end_date": "2025-01-03",
    "days_requested": 8.0,
    "status": "pending",            // pending | approved | rejected
    "leave_type_id": "uuid",
    "leave_type_name": "Vacaciones",
    "reason": "Vacaciones de Navidad",
    "supervisor_id": null,
    "reviewed_at": null,
    "review_notes": null,
    "created_at": "2024-11-01T10:00:00"
  }
]`,
      },
      {
        label: "POST /leave-requests",
        method: "POST",
        description: "Crear solicitud. Usa employee_ref y leave_type_name para evitar buscar UUIDs.",
        status: "201",
        request: `{
  // Identificar al empleado — una de las dos opciones:
  "employee_id": "3fa85f64-...",    // opción A: UUID interno
  "employee_ref": "+34600000000",   // opción B: código, teléfono o email

  "start_date": "2024-12-23",       // requerido — YYYY-MM-DD
  "end_date": "2025-01-03",         // requerido — YYYY-MM-DD
  "days_requested": 8.0,            // requerido — mínimo 0.5 (medio día)

  // Tipo de permiso — una de las dos opciones:
  "leave_type_id": "uuid",          // opción A: UUID del tipo
  "leave_type_name": "Vacaciones",  // opción B: nombre exacto del tipo

  "reason": "Vacaciones de Navidad",// motivo opcional
  "supervisor_id": null             // uuid del aprobador (usa el supervisor del empleado si null)
}`,
        response: `{
  "id": "d9f2c4e1-...",
  "employee_id": "3fa85f64-...",
  "start_date": "2024-12-23",
  "end_date": "2025-01-03",
  "days_requested": 8.0,
  "status": "pending",
  "leave_type_name": "Vacaciones",
  "reason": "Vacaciones de Navidad",
  "reviewed_at": null,
  "created_at": "2024-11-01T10:00:00"
}`,
      },
      {
        label: "POST /leave-requests/{id}/approve",
        method: "POST",
        description: "Aprobar una solicitud pendiente",
        request: `{
  "review_notes": "Aprobado. Disfrutad las fiestas."  // opcional
}`,
        response: `{
  "id": "d9f2c4e1-...",
  "status": "approved",
  "reviewed_at": "2024-11-05T11:30:00",
  "review_notes": "Aprobado. Disfrutad las fiestas.",
  ...
}`,
      },
    ],
  },
  {
    id: "incidents",
    title: "Incidencias",
    icon: "warning",
    endpoints: [
      { method: "GET",  path: "/incidents",      description: "Listar incidencias" },
      { method: "POST", path: "/incidents",      description: "Crear incidencia manual" },
    ],
    schemas: [
      {
        label: "GET /incidents",
        method: "GET",
        queryParams: [
          { name: "managed",     type: "boolean", required: false, description: "Filtrar por estado de gestión (false = sin gestionar)" },
          { name: "employee_id", type: "uuid",    required: false, description: "Filtrar por empleado" },
          { name: "category",    type: "string",  required: false, description: "fichaje | vacaciones | permiso" },
          { name: "from",        type: "date",    required: false, description: "Desde fecha incidencia" },
        ],
        response: `[
  {
    "id": "a1b2c3d4-...",
    "employee_id": "3fa85f64-...",
    "employee_name": "Ana García López",
    "category": "fichaje",
    "incident_type": "manual",       // late_clock_in | manual | other
    "status": "open",                // pending_justification | open | resolved | dismissed
    "source": "panel",               // auto | panel | api | whatsapp
    "title": "Olvido de fichaje de salida",
    "description": "El empleado olvidó fichar la salida del día 31",
    "incident_date": "2024-10-31",
    "clock_in_id": "uuid-del-fichaje",
    "leave_request_id": null,
    "minutes_late": null,
    "managed": false,
    "employee_justification": null,
    "internal_notes": null,
    "public_token": "abc123...",     // token para justificación pública
    "created_at": "2024-11-01T10:00:00"
  }
]`,
      },
      {
        label: "POST /incidents",
        method: "POST",
        description: "Crear incidencia manual. Usa employee_ref para evitar buscar el UUID.",
        status: "201",
        request: `{
  // Identificar al empleado — una de las dos opciones:
  "employee_id": "3fa85f64-...",    // opción A: UUID interno
  "employee_ref": "EMP001",         // opción B: código, teléfono o email

  "category": "fichaje",            // requerido: fichaje | vacaciones | permiso
  "title": "Olvido de fichaje",     // requerido
  "description": "Descripción detallada de la incidencia",
  "incident_date": "2024-10-31",    // fecha a la que hace referencia
  "clock_in_id": "uuid",            // vincular a un fichaje existente
  "leave_request_id": null,         // vincular a una solicitud de permiso
  "require_justification": false,   // enviar solicitud de justificación al empleado
  "notify_whatsapp": true           // notificar al empleado por WhatsApp
}`,
        response: `{
  "id": "a1b2c3d4-...",
  "employee_id": "3fa85f64-...",
  "employee_name": "Ana García López",
  "category": "fichaje",
  "incident_type": "manual",
  "status": "open",
  "title": "Olvido de fichaje",
  "managed": false,
  "public_token": "abc123...",
  "created_at": "2024-11-01T10:00:00"
}`,
      },
    ],
  },
  {
    id: "documents",
    title: "Documentos",
    icon: "folder",
    endpoints: [
      { method: "GET",  path: "/documents",      description: "Listar documentos entregados" },
      { method: "POST", path: "/documents",      description: "Subir y entregar documento (multipart)" },
    ],
    schemas: [
      {
        label: "GET /documents",
        method: "GET",
        queryParams: [
          { name: "employee_id",    type: "uuid",   required: false, description: "Filtrar por empleado" },
          { name: "document_type",  type: "string", required: false, description: "Tipo de documento" },
          { name: "signed",         type: "boolean",required: false, description: "Filtrar por estado de firma" },
        ],
        response: `[
  {
    "id": "e4f5a6b7-...",
    "employee_id": "3fa85f64-...",
    "employee_name": "Ana García López",
    "document_type_name": "Nómina",
    "file_name": "nomina_octubre_2024.pdf",
    "file_size": 245120,
    "mime_type": "application/pdf",
    "signed": false,
    "created_at": "2024-11-01T10:00:00",
    "file_url": "/api/documents/e4f5.../download"
  }
]`,
      },
      {
        label: "POST /documents",
        method: "POST",
        description: "Sube un fichero y lo entrega a un empleado. Content-Type: multipart/form-data",
        status: "201",
        request: `// multipart/form-data — NO application/json
file:             <binary>             // requerido — el fichero a entregar
employee_id:      3fa85f64-...         // requerido — uuid del empleado
document_type_id: uuid-del-tipo        // uuid del tipo de documento
description:      Nómina octubre 2024  // opcional`,
        response: `{
  "id": "e4f5a6b7-...",
  "employee_id": "3fa85f64-...",
  "file_name": "nomina_octubre_2024.pdf",
  "file_size": 245120,
  "mime_type": "application/pdf",
  "signed": false,
  "created_at": "2024-11-01T10:00:00"
}`,
      },
    ],
  },
  {
    id: "signatures",
    title: "Firmas electrónicas",
    icon: "draw",
    endpoints: [
      { method: "GET",  path: "/signatures",      description: "Listar sobres de firma" },
      { method: "POST", path: "/signatures",      description: "Crear sobre de firma" },
    ],
    schemas: [
      {
        label: "GET /signatures",
        method: "GET",
        queryParams: [
          { name: "status", type: "string", required: false, description: "draft | pending | completed | cancelled" },
        ],
        response: `[
  {
    "id": "f1a2b3c4-...",
    "reference": "ALK-2024-001",
    "title": "Contrato indefinido — Ana García",
    "status": "pending",             // draft | pending | completed | cancelled
    "document_delivery_id": "uuid",
    "expires_at": "2024-11-15T10:00:00",
    "completed_at": null,
    "created_at": "2024-11-01T10:00:00",
    "signers": [
      {
        "id": "g2h3i4j5-...",
        "employee_id": "3fa85f64-...",
        "order": 1,
        "status": "pendiente",       // pendiente | firmado | rechazado
        "signed_at": null
      }
    ]
  }
]`,
      },
      {
        label: "POST /signatures",
        method: "POST",
        description: "Crea un sobre de firma y notifica a los firmantes por WhatsApp/email",
        status: "201",
        request: `{
  "title": "Contrato indefinido — Ana García",  // requerido
  "document_delivery_id": "e4f5a6b7-...",        // uuid del documento a firmar
  "signers": [                                    // requerido — al menos 1
    {
      "employee_id": "3fa85f64-...",             // requerido
      "order": 1                                  // orden de firma (1 = primero)
    }
  ],
  "expires_in_days": 14,                          // días hasta expiración (1-90)
  "send_notifications": true                      // enviar aviso por WhatsApp/email
}`,
        response: `{
  "id": "f1a2b3c4-...",
  "reference": "ALK-2024-001",
  "title": "Contrato indefinido — Ana García",
  "status": "pending",
  "expires_at": "2024-11-15T10:00:00",
  "created_at": "2024-11-01T10:00:00",
  "signers": [
    {
      "id": "g2h3i4j5-...",
      "employee_id": "3fa85f64-...",
      "order": 1,
      "status": "pendiente",
      "signed_at": null
    }
  ]
}`,
      },
    ],
  },
  {
    id: "webhooks-doc",
    title: "Estructura de webhooks",
    icon: "webhook",
    endpoints: [],
    schemas: [
      {
        label: "Envelope — payload base",
        method: "POST",
        description: "Estructura común a todos los eventos. El campo data varía según el tipo.",
        response: `{
  "event": "employee.created",         // tipo de evento
  "timestamp": "2024-11-01T10:23:45Z", // ISO 8601 UTC
  "data": { ... }                       // objeto específico del evento (ver abajo)
}`,
      },
      {
        label: "employee.created / employee.updated",
        method: "POST",
        response: `{
  "event": "employee.created",
  "timestamp": "2024-11-01T10:23:45Z",
  "data": {
    "id": "3fa85f64-...",
    "full_name": "Ana García López",
    "phone": "+34600000000",
    "email": "ana@empresa.com",
    "employee_code": "EMP001",
    "role": "employee",
    "company_id": "uuid",
    "is_active": true
  }
}`,
      },
      {
        label: "clockin.created / clockin.updated",
        method: "POST",
        response: `{
  "event": "clockin.created",
  "timestamp": "2024-11-01T08:55:10Z",
  "data": {
    "id": "c7e3a1b2-...",
    "employee_id": "3fa85f64-...",
    "employee_name": "Ana García López",
    "entrada_at": "2024-11-01T08:55:00",
    "salida_at": null,
    "source": "whatsapp"
  }
}`,
      },
      {
        label: "leave.requested / leave.approved / leave.rejected",
        method: "POST",
        response: `{
  "event": "leave.approved",
  "timestamp": "2024-11-05T11:30:00Z",
  "data": {
    "id": "d9f2c4e1-...",
    "employee_id": "3fa85f64-...",
    "employee_name": "Ana García López",
    "start_date": "2024-12-23",
    "end_date": "2025-01-03",
    "days_requested": 8.0,
    "status": "approved",
    "leave_type_name": "Vacaciones",
    "review_notes": "Aprobado. Buen descanso."
  }
}`,
      },
      {
        label: "incident.created / incident.managed",
        method: "POST",
        response: `{
  "event": "incident.managed",
  "timestamp": "2024-11-01T15:00:00Z",
  "data": {
    "id": "a1b2c3d4-...",
    "employee_id": "3fa85f64-...",
    "employee_name": "Ana García López",
    "category": "fichaje",
    "title": "Olvido de fichaje de salida",
    "status": "resolved",
    "managed": true
  }
}`,
      },
      {
        label: "signature.completed",
        method: "POST",
        response: `{
  "event": "signature.completed",
  "timestamp": "2024-11-08T16:42:00Z",
  "data": {
    "envelope_id": "f1a2b3c4-...",
    "reference": "ALK-2024-001",
    "title": "Contrato indefinido — Ana García",
    "completed_at": "2024-11-08T16:42:00Z",
    "signers": [
      {
        "employee_id": "3fa85f64-...",
        "employee_name": "Ana García López",
        "signed_at": "2024-11-08T16:42:00Z"
      }
    ],
    "signed_document_url": "/api/signatures/f1a2.../download"
  }
}`,
      },
      {
        label: "Verificación de firma HMAC (Node.js)",
        method: "POST",
        description: "Verifica que el webhook procede de alcurro usando el secreto",
        response: `// Express.js — verificar X-Alcurro-Signature
const crypto = require('crypto');

app.post('/webhook', express.raw({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-alcurro-signature'];
  const expected = 'sha256=' + crypto
    .createHmac('sha256', process.env.WEBHOOK_SECRET)
    .update(req.body)  // body como Buffer, no parseado
    .digest('hex');

  if (signature !== expected) {
    return res.status(401).json({ error: 'Firma inválida' });
  }

  const event = JSON.parse(req.body);
  console.log('Evento recibido:', event.event);
  res.status(200).send('OK');
});`,
      },
    ],
  },
  {
    id: "errors",
    title: "Errores y paginación",
    icon: "error",
    endpoints: [],
    schemas: [
      {
        label: "Formato de error estándar",
        method: "GET",
        response: `// 400 — Validación fallida
{
  "detail": [
    {
      "loc": ["body", "phone"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 409 — Conflicto (duplicado, constraint de BD)
{
  "detail": "Ya existe un empleado con ese teléfono en la empresa"
}

// 403 — Sin permisos
{
  "detail": "No tienes permisos suficientes para esta operación"
}`,
      },
      {
        label: "Tabla de códigos HTTP",
        method: "GET",
        response: `200 OK          → Operación completada con éxito
201 Created     → Recurso creado correctamente
204 No Content  → Eliminación exitosa (sin cuerpo de respuesta)
400 Bad Request → Datos de entrada inválidos
401 Unauthorized→ Clave de API ausente o inválida
403 Forbidden   → Sin permisos para este recurso
404 Not Found   → Recurso no encontrado
409 Conflict    → Violación de unicidad (duplicado)
422 Unprocessable → Errores de validación de tipos/formato`,
      },
    ],
  },
];

function DocSection({ section }: { section: DocSectionDef }) {
  const [open, setOpen] = useState(section.id === "auth");
  return (
    <div className={`dev-doc-section${open ? " is-open" : ""}`}>
      <button type="button" className="dev-doc-section__head" onClick={() => setOpen(v => !v)}>
        <span className="material-symbols-outlined">{section.icon}</span>
        <span>{section.title}</span>
        {section.endpoints.length > 0 && (
          <span className="dev-endpoint-count">{section.endpoints.length}</span>
        )}
        <span className="material-symbols-outlined dev-doc-section__chevron">expand_more</span>
      </button>
      {open && (
        <div className="dev-doc-section__body">
          {section.endpoints.length > 0 && (
            <div className="dev-table-wrap" style={{ marginBottom: "1.25rem" }}>
              <table className="dev-table">
                <thead><tr><th>Método</th><th>Ruta</th><th>Descripción</th></tr></thead>
                <tbody>
                  {section.endpoints.map((ep, i) => (
                    <tr key={i}>
                      <td><span className={`dev-method dev-method--${ep.method.toLowerCase()}`}>{ep.method}</span></td>
                      <td><code className="dev-code">{ep.path}{ep.query ?? ""}</code></td>
                      <td className="muted small">{ep.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="dev-schema-list">
            {section.schemas.map((s, i) => <SchemaBlock key={i} schema={s} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function DocsTab() {
  return (
    <div className="dev-section">
      <div className="dev-section__intro">
        <p>
          Referencia de la API de alcurro con schemas de request y response reales.
          URL base: <code className="dev-code">https://alcurro.es/api</code> — Swagger interactivo:{" "}
          <a href="https://alcurro.es/api/docs" target="_blank" rel="noreferrer" className="dev-code" style={{ color: "var(--primary)" }}>
            alcurro.es/api/docs
          </a>
        </p>
      </div>
      <div className="dev-doc-list">
        {DOC_SECTIONS.map(s => <DocSection key={s.id} section={s} />)}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "keys",     label: "Claves de API",  icon: "key" },
  { id: "webhooks", label: "Webhooks",        icon: "webhook" },
  { id: "docs",     label: "Documentación",   icon: "menu_book" },
] as const;

type TabId = typeof TABS[number]["id"];

export default function DeveloperPage() {
  const [tab, setTab] = useState<TabId>("keys");

  return (
    <>
      <PageHeader
        title="APIs y Webhooks"
        subtitle="Integra alcurro con tus sistemas mediante la API REST y webhooks de eventos"
      />

      <div className="dev-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            className={`dev-tab-btn${tab === t.id ? " is-active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <span className="material-symbols-outlined">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      <div className="card">
        {tab === "keys"     && <ApiKeysTab />}
        {tab === "webhooks" && <WebhooksTab />}
        {tab === "docs"     && <DocsTab />}
      </div>
    </>
  );
}
