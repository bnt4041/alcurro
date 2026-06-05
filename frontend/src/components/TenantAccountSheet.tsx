import { FormEvent, useMemo, useState } from "react";
import type { Role } from "../api/types";
import DataTable, { type DataTableColumn } from "./DataTable";
import InvoiceHistoryTable from "./InvoiceHistoryTable";
import SubscriptionSummaryCard from "./SubscriptionSummaryCard";
import TenantAIUsagePanel from "./TenantAIUsagePanel";
import TenantBillingTab, { TenantBillingOverview } from "./TenantBillingTab";
import { ROLE_LABELS } from "../lib/permissions";
import { normalizeAccountCode } from "../lib/slug";
import type { InvoiceRow, SubscriptionSummary } from "../lib/subscription";

export type TenantFormState = {
  accountCode: string;
  name: string;
  legal_name: string;
  tax_id: string;
  billing_email: string;
  billing_phone: string;
  billing_address: string;
  billing_city: string;
  billing_postal_code: string;
  billing_province: string;
  billing_country: string;
  is_active: boolean;
};

export type AccountSheetTab = "general" | "billing" | "users" | "ia";

export interface TenantUserRow {
  id: string;
  company_name: string;
  full_name: string;
  employee_code: string;
  phone: string;
  email: string | null;
  role: Role;
  is_active: boolean;
}

export interface TenantUserCreateForm {
  full_name: string;
  phone: string;
  email: string;
  id_document: string;
  role: Role;
  password: string;
}

interface Props {
  open: boolean;
  mode: "create" | "edit";
  tab: AccountSheetTab;
  tenantId: string | null;
  form: TenantFormState;
  accountCodeManual: boolean;
  saving: boolean;
  users: TenantUserRow[];
  usersLoading: boolean;
  billing: TenantBillingOverview | null;
  billingLoading: boolean;
  invoices: InvoiceRow[];
  invoicesLoading: boolean;
  subscription: SubscriptionSummary | null;
  onBillingReload: () => void;
  onTabChange: (tab: AccountSheetTab) => void;
  onClose: () => void;
  onSave: (e: FormEvent) => void;
  onNameChange: (name: string) => void;
  onLegalNameChange: (legalName: string) => void;
  onAccountCodeManual: (manual: boolean) => void;
  onRegenerateCode: () => void;
  onFormPatch: (patch: Partial<TenantFormState>) => void;
  onDeactivate?: () => void;
  onReactivate?: () => void;
  onDelete?: () => void;
  onCreateTenantUser?: (data: TenantUserCreateForm) => Promise<void>;
  onUpdateTenantUser?: (userId: string, data: Partial<TenantUserCreateForm> & { is_active?: boolean }) => Promise<void>;
  onDeleteTenantUser?: (userId: string, userName: string) => void;
  creatingUser?: boolean;
}

const TABS: { id: AccountSheetTab; label: string }[] = [
  { id: "general", label: "General" },
  { id: "billing", label: "Facturación" },
  { id: "users", label: "Usuarios" },
  { id: "ia", label: "IA" },
];

export default function TenantAccountSheet({
  open,
  mode,
  tab,
  tenantId,
  form,
  accountCodeManual,
  saving,
  users,
  usersLoading,
  billing,
  billingLoading,
  invoices,
  invoicesLoading,
  subscription,
  onBillingReload,
  onTabChange,
  onClose,
  onSave,
  onNameChange,
  onLegalNameChange,
  onAccountCodeManual,
  onRegenerateCode,
  onFormPatch,
  onDeactivate,
  onReactivate,
  onDelete,
  onCreateTenantUser,
  onUpdateTenantUser,
  onDeleteTenantUser,
  creatingUser = false,
}: Props) {
  const [userForm, setUserForm] = useState<TenantUserCreateForm>({
    full_name: "",
    phone: "",
    email: "",
    id_document: "",
    role: "tenant_admin",
    password: "",
  });
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editUserForm, setEditUserForm] = useState<TenantUserCreateForm & { is_active?: boolean }>({
    full_name: "",
    phone: "",
    email: "",
    id_document: "",
    role: "tenant_admin",
    password: "",
    is_active: true,
  });
  const [savingUser, setSavingUser] = useState(false);

  const submitNewUser = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!onCreateTenantUser) return;
    try {
      await onCreateTenantUser(userForm);
      setUserForm({
        full_name: "",
        phone: "",
        email: "",
        id_document: "",
        role: "tenant_admin",
        password: "",
      });
    } catch {
      // error ya se muestra en el padre
    }
  };

  type UserTableRow = TenantUserRow & { role_label: string; status_label: string };

  const userTableData = useMemo<UserTableRow[]>(
    () =>
      users.map((u) => ({
        ...u,
        role_label: ROLE_LABELS[u.role as Role] ?? u.role,
        status_label: u.is_active ? "Activo" : "Inactivo",
      })),
    [users]
  );

  const userColumns = useMemo<DataTableColumn<UserTableRow>[]>(
    () => [
      {
        title: "Usuario",
        field: "employee_code",
        headerFilter: "input",
        formatter: (c) => `<code>${String(c.getValue())}</code>`,
        width: 110,
      },
      { title: "Nombre", field: "full_name", headerFilter: "input", minWidth: 140 },
      { title: "Teléfono", field: "phone", headerFilter: "input", width: 120 },
      { title: "Rol", field: "role_label", headerFilter: "input", width: 120 },
      {
        title: "Empresa",
        field: "company_name",
        headerFilter: "input",
        formatter: (c) => `<span class="muted small">${String(c.getValue())}</span>`,
        minWidth: 120,
      },
      {
        title: "Estado",
        field: "status_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", Activo: "Activo", Inactivo: "Inactivo" } },
        width: 90,
      },
    ],
    []
  );

  const startEditUser = (u: TenantUserRow) => {
    setEditingUserId(u.id);
    setEditUserForm({
      full_name: u.full_name,
      phone: u.phone,
      email: u.email || "",
      id_document: "",
      role: u.role as Role,
      password: "",
      is_active: u.is_active,
    });
  };

  const cancelEditUser = () => {
    setEditingUserId(null);
  };

  const saveEditUser = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!onUpdateTenantUser || !editingUserId) return;
    setSavingUser(true);
    try {
      const payload: Record<string, unknown> = {
        full_name: editUserForm.full_name,
        phone: editUserForm.phone,
        email: editUserForm.email || undefined,
        role: editUserForm.role,
        is_active: editUserForm.is_active,
      };
      if (editUserForm.password) {
        payload.password = editUserForm.password;
      }
      if (editUserForm.id_document) {
        payload.id_document = editUserForm.id_document;
      }
      await onUpdateTenantUser(editingUserId, payload as any);
      setEditingUserId(null);
    } catch {
      // error ya mostrado
    } finally {
      setSavingUser(false);
    }
  };

  if (!open) return null;

  const isEdit = mode === "edit";
  const title = isEdit ? form.name || "Cuenta cliente" : "Nueva cuenta";
  const showFormHint = tab === "general" || tab === "billing";

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="modal-panel modal-panel--sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tenant-sheet-title"
      >
        <header className="sheet-header sheet-header--tabs">
          <div className="sheet-header__intro">
            <div className="sheet-header__top">
              <h3 id="tenant-sheet-title">{title}</h3>
              {isEdit && (
                <span
                  className={`badge ${form.is_active ? "badge--ok" : "badge--muted"}`}
                >
                  {form.is_active ? "Activa" : "Inactiva"}
                </span>
              )}
            </div>
            {isEdit && form.accountCode && (
              <p className="muted small sheet-subtitle">
                Código de acceso: <code>{form.accountCode}</code>
              </p>
            )}
          </div>
          <div
            className="tabs sheet-tabs"
            role="tablist"
            aria-label="Secciones de la cuenta"
          >
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={tab === t.id}
                className={tab === t.id ? "tab active" : "tab"}
                onClick={() => onTabChange(t.id)}
              >
                {t.label}
                {t.id === "users" && isEdit && users.length > 0 && (
                  <span className="tab-count">{users.length}</span>
                )}
              </button>
            ))}
          </div>
        </header>

        <form
          id="tenant-sheet-form"
          className="sheet-body"
          onSubmit={onSave}
          noValidate
        >
          {showFormHint && (
            <p className="muted small sheet-hint">
              Campos con <span className="required-mark">*</span> obligatorios.
            </p>
          )}

          {tab === "general" && (
            <div className="sheet-tab-panel form-grid">
              <label>
                <span>
                  Nombre comercial <span className="required-mark">*</span>
                </span>
                <input
                  value={form.name}
                  onChange={(e) => onNameChange(e.target.value)}
                />
              </label>
              <label>
                <span>
                  Razón social <span className="required-mark">*</span>
                </span>
                <input
                  value={form.legal_name}
                  onChange={(e) => onLegalNameChange(e.target.value)}
                />
              </label>
              <label className="form-span-2">
                <span className="label-row">
                  <span>Código de cuenta</span>
                  {!isEdit && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={onRegenerateCode}
                      disabled={!form.name.trim() && !form.legal_name.trim()}
                    >
                      Regenerar
                    </button>
                  )}
                </span>
                <input
                  readOnly={!isEdit && !accountCodeManual}
                  value={form.accountCode}
                  onChange={(e) => {
                    onAccountCodeManual(true);
                    onFormPatch({
                      accountCode: normalizeAccountCode(e.target.value),
                    });
                  }}
                  onFocus={() => onAccountCodeManual(true)}
                />
                <span className="field-hint muted small">
                  Se genera automáticamente. Los empleados lo usan en «Acceso a tu
                  cuenta».
                </span>
              </label>
              {isEdit && (
                <label className="form-span-2 checkbox-row">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) =>
                      onFormPatch({ is_active: e.target.checked })
                    }
                  />
                  Cuenta activa (permite acceso de usuarios)
                </label>
              )}
            </div>
          )}

          {tab === "billing" && (
            <>
              {isEdit && (
                <div className="sheet-tab-panel billing-overview-block">
                  <h4 className="billing-section-title">Suscripción y tarifa</h4>
                  <SubscriptionSummaryCard
                    subscription={subscription}
                    loading={billingLoading && !subscription}
                  />
                  <h4 className="billing-section-title" style={{ marginTop: "1.25rem" }}>
                    Histórico de facturas
                  </h4>
                  <InvoiceHistoryTable invoices={invoices} loading={invoicesLoading} />
                </div>
              )}
              <div className="sheet-tab-panel form-grid billing-account-fields">
                <p className="form-span-2 muted small billing-section-title">
                  Datos del contrato (cuenta) — referencia por defecto para nuevas
                  empresas.
                </p>
                <label>
                  <span>
                    CIF/NIF cuenta <span className="required-mark">*</span>
                  </span>
                  <input
                    value={form.tax_id}
                    onChange={(e) => onFormPatch({ tax_id: e.target.value })}
                  />
                </label>
                <label>
                  <span>
                    Email facturación <span className="required-mark">*</span>
                  </span>
                  <input
                    type="email"
                    value={form.billing_email}
                    onChange={(e) =>
                      onFormPatch({ billing_email: e.target.value })
                    }
                  />
                </label>
                <label>
                  <span>
                    Teléfono <span className="required-mark">*</span>
                  </span>
                  <input
                    type="tel"
                    value={form.billing_phone}
                    onChange={(e) =>
                      onFormPatch({ billing_phone: e.target.value })
                    }
                  />
                </label>
                <label>
                  País
                  <input
                    value={form.billing_country}
                    onChange={(e) =>
                      onFormPatch({ billing_country: e.target.value })
                    }
                  />
                </label>
                <label className="form-span-2">
                  Dirección
                  <input
                    value={form.billing_address}
                    onChange={(e) =>
                      onFormPatch({ billing_address: e.target.value })
                    }
                  />
                </label>
                <label>
                  Ciudad
                  <input
                    value={form.billing_city}
                    onChange={(e) =>
                      onFormPatch({ billing_city: e.target.value })
                    }
                  />
                </label>
                <label>
                  CP
                  <input
                    value={form.billing_postal_code}
                    onChange={(e) =>
                      onFormPatch({ billing_postal_code: e.target.value })
                    }
                  />
                </label>
                <label>
                  Provincia
                  <input
                    value={form.billing_province}
                    onChange={(e) =>
                      onFormPatch({ billing_province: e.target.value })
                    }
                  />
                </label>
              </div>
              {isEdit && tenantId && (
                <TenantBillingTab
                  tenantId={tenantId}
                  overview={billing}
                  loading={billingLoading}
                  onReload={onBillingReload}
                />
              )}
            </>
          )}

          {tab === "ia" && (
            <div className="sheet-tab-panel" role="tabpanel">
              {!isEdit || !tenantId ? (
                <div className="sheet-placeholder">
                  <p className="muted">
                    El consumo de IA se muestra al editar una cuenta existente.
                  </p>
                </div>
              ) : (
                <TenantAIUsagePanel tenantId={tenantId} />
              )}
            </div>
          )}

          {tab === "users" && (
            <div className="sheet-tab-panel" role="tabpanel">
              {!isEdit || !tenantId ? (
                <div className="sheet-placeholder">
                  <p className="muted">
                    Crea y guarda la cuenta para ver y gestionar los usuarios del
                    cliente.
                  </p>
                </div>
              ) : (
                <>
                  {onCreateTenantUser && (
                    <section className="card sheet-user-create">
                      <h4>Crear usuario</h4>
                      <p className="muted small">
                        Acceso al panel del cliente con código{" "}
                        <code>{form.accountCode}</code> y el usuario generado (EMP-001…).
                      </p>
                      <div className="form-grid">
                        <label>
                          Nombre
                          <input
                            required
                            value={userForm.full_name}
                            onChange={(ev) =>
                              setUserForm({ ...userForm, full_name: ev.target.value })
                            }
                          />
                        </label>
                        <label>
                          DNI/NIE
                          <input
                            required
                            value={userForm.id_document}
                            onChange={(ev) =>
                              setUserForm({
                                ...userForm,
                                id_document: ev.target.value.toUpperCase(),
                              })
                            }
                          />
                        </label>
                        <label>
                          Teléfono (WhatsApp)
                          <input
                            required
                            value={userForm.phone}
                            onChange={(ev) =>
                              setUserForm({ ...userForm, phone: ev.target.value })
                            }
                          />
                        </label>
                        <label>
                          Email
                          <input
                            type="email"
                            value={userForm.email}
                            onChange={(ev) =>
                              setUserForm({ ...userForm, email: ev.target.value })
                            }
                          />
                        </label>
                        <label>
                          Rol
                          <select
                            value={userForm.role}
                            onChange={(ev) =>
                              setUserForm({
                                ...userForm,
                                role: ev.target.value as Role,
                              })
                            }
                          >
                            <option value="tenant_admin">Administrador de cuenta</option>
                            <option value="manager">Responsable</option>
                            <option value="employee">Empleado</option>
                          </select>
                        </label>
                        <label>
                          Contraseña panel
                          <input
                            type="password"
                            required
                            minLength={6}
                            value={userForm.password}
                            onChange={(ev) =>
                              setUserForm({ ...userForm, password: ev.target.value })
                            }
                          />
                        </label>
                        <div className="form-actions form-grid-full">
                          <button
                            type="button"
                            className="btn btn-primary"
                            disabled={creatingUser}
                            onClick={submitNewUser}
                          >
                            {creatingUser ? "Creando…" : "Crear usuario"}
                          </button>
                        </div>
                      </div>
                    </section>
                  )}
                  {usersLoading ? (
                    <p className="muted">Cargando usuarios…</p>
                  ) : users.length === 0 ? (
                    <p className="muted small">Aún no hay usuarios en esta cuenta.</p>
                  ) : (
                    <>
                    <DataTable
                      data={userTableData}
                      columns={userColumns}
                      loading={usersLoading}
                      exportFilename="usuarios_cuenta"
                      height="360px"
                      onRowClick={(row) => {
                        const u = users.find((x) => x.id === (row as UserTableRow).id);
                        if (u) startEditUser(u);
                      }}
                    />
                    <p className="muted small" style={{ marginTop: "0.5rem" }}>
                      Haz clic en un usuario para editarlo.
                    </p>
                    {editingUserId && (
                      <section className="card sheet-user-create" style={{ marginTop: "1rem" }}>
                        <h4>Editar usuario</h4>
                        <div className="form-grid">
                          <label>
                            Nombre
                            <input
                              value={editUserForm.full_name}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, full_name: ev.target.value })
                              }
                            />
                          </label>
                          <label>
                            DNI/NIE
                            <input
                              value={editUserForm.id_document}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, id_document: ev.target.value.toUpperCase() })
                              }
                              placeholder="Solo si cambia"
                            />
                          </label>
                          <label>
                            Teléfono
                            <input
                              value={editUserForm.phone}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, phone: ev.target.value })
                              }
                            />
                          </label>
                          <label>
                            Email
                            <input
                              type="email"
                              value={editUserForm.email}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, email: ev.target.value })
                              }
                            />
                          </label>
                          <label>
                            Rol
                            <select
                              value={editUserForm.role}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, role: ev.target.value as Role })
                              }
                            >
                              <option value="tenant_admin">Administrador de cuenta</option>
                              <option value="manager">Responsable</option>
                              <option value="employee">Empleado</option>
                            </select>
                          </label>
                          <label>
                            Nueva contraseña
                            <input
                              type="password"
                              value={editUserForm.password}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, password: ev.target.value })
                              }
                              placeholder="Dejar vacío para no cambiar"
                            />
                          </label>
                          <label className="checkbox-row form-span-2">
                            <input
                              type="checkbox"
                              checked={editUserForm.is_active ?? true}
                              onChange={(ev) =>
                                setEditUserForm({ ...editUserForm, is_active: ev.target.checked })
                              }
                            />
                            Usuario activo
                          </label>
                          <div className="form-actions form-grid-full" style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                              type="button"
                              className="btn btn-primary"
                              disabled={savingUser}
                              onClick={saveEditUser}
                            >
                              {savingUser ? "Guardando…" : "Guardar cambios"}
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost"
                              onClick={cancelEditUser}
                            >
                              Cancelar
                            </button>
                            {onDeleteTenantUser && (
                              <button
                                type="button"
                                className="btn btn-danger"
                                style={{ marginLeft: "auto" }}
                                onClick={() => {
                                  const u = users.find((x) => x.id === editingUserId);
                                  if (u) {
                                    onDeleteTenantUser(u.id, u.full_name);
                                    setEditingUserId(null);
                                  }
                                }}
                              >
                                Desactivar usuario
                              </button>
                            )}
                          </div>
                        </div>
                      </section>
                    )}
                    </>
                  )}
                </>
              )}
            </div>
          )}

        </form>

        <footer className="sheet-footer">
          <div className="sheet-footer__actions">
            {isEdit && (
              <>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={onDelete}
                  disabled={saving}
                >
                  Eliminar
                </button>
                {form.is_active ? (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={onDeactivate}
                    disabled={saving}
                  >
                    Desactivar
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={onReactivate}
                    disabled={saving}
                  >
                    Reactivar
                  </button>
                )}
              </>
            )}
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={saving}
            >
              Cancelar
            </button>
            <button
              type="submit"
              form="tenant-sheet-form"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving
                ? "Guardando…"
                : isEdit
                  ? "Guardar cambios"
                  : "Crear cuenta"}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
