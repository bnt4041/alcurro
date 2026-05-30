import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";

interface TenantRow {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
}

interface PurgeCategory {
  key: string;
  label: string;
}

interface PurgeResultEntry {
  tenant_id: string;
  tenant_name: string;
  purged: Record<string, number>;
}

const PURGE_ICONS: Record<string, string> = {
  clock_ins: "⏱️",
  work_breaks: "☕",
  leave_requests: "🏖️",
  incidents: "⚠️",
  employees: "👤",
  accounts: "🏢",
};

const PURGE_WARNINGS: Record<string, string> = {
  clock_ins: "Se eliminarán todos los registros de fichaje. Esta acción es irreversible.",
  work_breaks: "Se eliminarán todos los registros de paradas y descansos.",
  leave_requests: "Se eliminarán todas las solicitudes de vacaciones y permisos.",
  incidents: "Se eliminarán todas las incidencias registradas.",
  employees:
    "Se eliminarán TODOS los empleados y sus datos asociados (fichajes, paradas, vacaciones, incidencias, documentos, firmas).",
  accounts:
    "⚠️ ELIMINACIÓN TOTAL de la cuenta, empresas, empleados y todos los datos. ¡IRREVERSIBLE!",
};

export default function PlatformPurgePage() {
  const toast = useToast();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [categories, setCategories] = useState<PurgeCategory[]>([]);
  const [selectedTenant, setSelectedTenant] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
    new Set()
  );
  const [loading, setLoading] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [lastResult, setLastResult] = useState<PurgeResultEntry | null>(null);

  const activeTenants = useMemo(
    () => tenants.filter((t) => t.is_active),
    [tenants]
  );

  const tenantName = useMemo(() => {
    const t = tenants.find((t) => t.id === selectedTenant);
    return t ? `${t.name} (${t.slug})` : "";
  }, [tenants, selectedTenant]);

  useEffect(() => {
    void loadData();
  }, []);

  const loadData = async () => {
    try {
      const [t, c] = await Promise.all([
        api.get<TenantRow[]>("/platform/tenants"),
        api.get<PurgeCategory[]>("/platform/purge-categories"),
      ]);
      setTenants(t);
      setCategories(c);
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    }
  };

  const toggleCategory = (key: string) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      // Si se marca "accounts", desmarcar el resto
      if (key === "accounts" && next.has("accounts")) {
        return new Set(["accounts"]);
      }
      // Si se marca otra categoría teniendo "accounts", quitar "accounts"
      if (key !== "accounts" && next.has("accounts")) {
        next.delete("accounts");
      }
      return next;
    });
  };

  const needsConfirmation = selectedCategories.has("accounts");
  const confirmKeyword = needsConfirmation ? "ELIMINAR" : "PURGAR";

  const canExecute =
    selectedTenant &&
    selectedCategories.size > 0 &&
    confirmText.trim().toUpperCase() === confirmKeyword;

  const executePurge = async () => {
    if (!canExecute) return;
    setLoading(true);
    setLastResult(null);
    try {
      const result = await api.post<PurgeResultEntry>(
        `/platform/purge/${selectedTenant}`,
        { categories: [...selectedCategories] }
      );
      setLastResult(result);
      toast.success("Purga completada correctamente");
      setSelectedCategories(new Set());
      setConfirmText("");
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Purga de datos"
        subtitle="Elimina datos de cuentas de forma selectiva. Todas las operaciones son irreversibles."
      />

      <div className="card" style={{ maxWidth: 720 }}>
        {/* Selección de cuenta */}
        <div className="form-group">
          <label htmlFor="purge-tenant">Cuenta</label>
          <select
            id="purge-tenant"
            className="input"
            value={selectedTenant}
            onChange={(e) => {
              setSelectedTenant(e.target.value);
              setSelectedCategories(new Set());
              setConfirmText("");
              setLastResult(null);
            }}
          >
            <option value="">Selecciona una cuenta…</option>
            {activeTenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.slug})
              </option>
            ))}
          </select>
        </div>

        {/* Selección de categorías */}
        {selectedTenant && (
          <>
            <hr />
            <p className="muted" style={{ marginBottom: 12 }}>
              Selecciona los datos que quieres eliminar de{" "}
              <strong>{tenantName}</strong>:
            </p>

            <div className="form-group">
              {categories.map((cat) => {
                const checked = selectedCategories.has(cat.key);
                const isAccounts = cat.key === "accounts";
                const disabled =
                  !checked && selectedCategories.has("accounts");

                return (
                  <label
                    key={cat.key}
                    className={`checkbox-card${checked ? " checkbox-card--checked" : ""}${disabled ? " checkbox-card--disabled" : ""}`}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                      padding: "12px 16px",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      marginBottom: 8,
                      cursor: disabled ? "not-allowed" : "pointer",
                      opacity: disabled ? 0.5 : 1,
                      background: checked
                        ? isAccounts
                          ? "var(--danger-light, #fef2f2)"
                          : "var(--primary-light, #eff6ff)"
                        : "var(--bg)",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggleCategory(cat.key)}
                      style={{ marginTop: 2 }}
                    />
                    <div style={{ flex: 1 }}>
                      <strong>
                        {PURGE_ICONS[cat.key] || "📦"} {cat.label}
                      </strong>
                      <p
                        className="muted"
                        style={{
                          margin: "4px 0 0",
                          fontSize: 13,
                          color: isAccounts ? "var(--danger)" : undefined,
                        }}
                      >
                        {PURGE_WARNINGS[cat.key] || ""}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          </>
        )}

        {/* Confirmación */}
        {selectedCategories.size > 0 && (
          <>
            <hr />
            <div
              className={
                needsConfirmation ? "card card--danger" : "card card--warning"
              }
              style={{
                background: needsConfirmation
                  ? "var(--danger-light, #fef2f2)"
                  : "var(--warning-light, #fffbeb)",
                border: `1px solid ${needsConfirmation ? "var(--danger, #ef4444)" : "var(--warning, #f59e0b)"}`,
                padding: 16,
                borderRadius: 8,
                marginBottom: 16,
              }}
            >
              <p style={{ margin: 0 }}>
                {needsConfirmation
                  ? "⚠️ Vas a eliminar la cuenta por completo. Esta acción NO se puede deshacer."
                  : "⚠️ Vas a eliminar datos de esta cuenta. Esta acción NO se puede deshacer."}
              </p>
            </div>

            <div className="form-group">
              <label htmlFor="purge-confirm">
                Escribe <code>{confirmKeyword}</code> para confirmar:
              </label>
              <input
                id="purge-confirm"
                className="input"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder={confirmKeyword}
                autoComplete="off"
              />
            </div>

            <button
              type="button"
              className={`btn ${needsConfirmation ? "btn--danger" : "btn--warning"}`}
              disabled={!canExecute || loading}
              onClick={executePurge}
            >
              {loading
                ? "Purgando…"
                : needsConfirmation
                  ? "Eliminar cuenta permanentemente"
                  : `Purgar ${selectedCategories.size} categoría(s)`}
            </button>
          </>
        )}

        {/* Resultado */}
        {lastResult && (
          <>
            <hr />
            <div
              className="card"
              style={{
                background: "var(--success-light, #f0fdf4)",
                border: "1px solid var(--success, #22c55e)",
                padding: 16,
                borderRadius: 8,
              }}
            >
              <p style={{ margin: "0 0 8px", fontWeight: 600 }}>
                ✅ Purga completada — {lastResult.tenant_name}
              </p>
              <table style={{ width: "100%", fontSize: 14 }}>
                <tbody>
                  {Object.entries(lastResult.purged).map(([key, count]) => {
                    const label =
                      categories.find((c) => c.key === key)?.label ?? key;
                    return (
                      <tr key={key}>
                        <td style={{ padding: "4px 8px" }}>
                          {PURGE_ICONS[key] || "📦"} {label}
                        </td>
                        <td style={{ padding: "4px 8px", textAlign: "right" }}>
                          {key === "accounts"
                            ? "Eliminada"
                            : `${count} registro(s)`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
