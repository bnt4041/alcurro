import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import DataTable, { type DataTableColumn } from "../components/DataTable";
import TenantAccountSheet, {
  AccountSheetTab,
  TenantFormState,
  TenantUserCreateForm,
  TenantUserRow,
} from "../components/TenantAccountSheet";
import { TenantBillingOverview } from "../components/TenantBillingTab";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";
import {
  isValidAccountCode,
  normalizeAccountCode,
  suggestAccountCode,
} from "../lib/slug";
import { formatMoney } from "../lib/money";
import type { InvoiceRow, SubscriptionSummary } from "../lib/subscription";
import { SUBSCRIPTION_STATUS_LABELS } from "../lib/subscription";

interface GroupTemplate {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
  is_system: boolean;
}

interface TenantRow {
  id: string;
  slug: string;
  name: string;
  legal_name: string | null;
  tax_id: string | null;
  billing_email: string | null;
  billing_phone: string | null;
  billing_address?: string | null;
  billing_city?: string | null;
  billing_postal_code?: string | null;
  billing_province?: string | null;
  billing_country?: string;
  is_active: boolean;
  created_at: string;
  subscription: SubscriptionSummary | null;
}

type TenantTableRow = TenantRow & {
  plan_label: string;
  subscription_label: string;
  amount_label: string;
  account_label: string;
};

const emptyForm = (): TenantFormState => ({
  accountCode: "",
  name: "",
  legal_name: "",
  tax_id: "",
  billing_email: "",
  billing_phone: "",
  billing_address: "",
  billing_city: "",
  billing_postal_code: "",
  billing_province: "",
  billing_country: "ES",
  is_active: true,
});

function tenantToForm(t: TenantRow): TenantFormState {
  return {
    accountCode: t.slug,
    name: t.name,
    legal_name: t.legal_name ?? "",
    tax_id: t.tax_id ?? "",
    billing_email: t.billing_email ?? "",
    billing_phone: t.billing_phone ?? "",
    billing_address: t.billing_address ?? "",
    billing_city: t.billing_city ?? "",
    billing_postal_code: t.billing_postal_code ?? "",
    billing_province: t.billing_province ?? "",
    billing_country: t.billing_country || "ES",
    is_active: t.is_active,
  };
}

export default function PlatformPage() {
  const toast = useToast();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [templates, setTemplates] = useState<GroupTemplate[]>([]);
  const [form, setForm] = useState<TenantFormState>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetTab, setSheetTab] = useState<AccountSheetTab>("general");
  const [accountCodeManual, setAccountCodeManual] = useState(false);
  const [saving, setSaving] = useState(false);
  const [users, setUsers] = useState<TenantUserRow[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [creatingUser, setCreatingUser] = useState(false);
  const [billing, setBilling] = useState<TenantBillingOverview | null>(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);

  const sheetMode = editingId ? "edit" : "create";

  const tenantTableData = useMemo<TenantTableRow[]>(
    () =>
      tenants.map((t) => ({
        ...t,
        plan_label: t.subscription?.plan_name ?? "—",
        subscription_label: t.subscription
          ? SUBSCRIPTION_STATUS_LABELS[t.subscription.status] ?? t.subscription.status
          : "—",
        amount_label: t.subscription
          ? formatMoney(t.subscription.amount_cents, t.subscription.currency)
          : "—",
        account_label: t.is_active ? "Activa" : "Inactiva",
      })),
    [tenants]
  );

  const tenantColumns = useMemo<DataTableColumn<TenantTableRow>[]>(
    () => [
      {
        title: "Código",
        field: "slug",
        headerFilter: "input",
        formatter: (c) => `<code>${String(c.getValue())}</code>`,
        width: 110,
      },
      { title: "Nombre", field: "name", headerFilter: "input", minWidth: 160 },
      {
        title: "CIF",
        field: "tax_id",
        headerFilter: "input",
        formatter: (c) => String(c.getValue() ?? "—"),
        width: 110,
      },
      { title: "Tarifa", field: "plan_label", headerFilter: "input", minWidth: 120 },
      {
        title: "Suscripción",
        field: "subscription_label",
        headerFilter: "select",
        headerFilterParams: {
          values: {
            "": "Todos",
            ...Object.fromEntries(
              Object.values(SUBSCRIPTION_STATUS_LABELS).map((v) => [v, v])
            ),
          } as Record<string, string>,
        },
        formatter: (cell) => {
          const r = cell.getRow().getData() as TenantTableRow;
          if (!r.subscription) return "—";
          const cls =
            r.subscription.status === "active"
              ? "badge--ok"
              : r.subscription.status === "past_due"
                ? "badge--danger"
                : "";
          return `<span class="badge ${cls}">${r.subscription_label}</span>`;
        },
        width: 130,
      },
      { title: "Importe", field: "amount_label", headerFilter: "input", width: 100 },
      {
        title: "Cuenta",
        field: "account_label",
        headerFilter: "select",
        headerFilterParams: { values: { "": "Todos", Activa: "Activa", Inactiva: "Inactiva" } },
        width: 100,
      },
    ],
    []
  );

  const loadInvoices = async (tenantId: string) => {
    setInvoicesLoading(true);
    try {
      setInvoices(await api.get<InvoiceRow[]>(`/platform/tenants/${tenantId}/invoices`));
    } catch {
      setInvoices([]);
    } finally {
      setInvoicesLoading(false);
    }
  };

  const loadBilling = async (tenantId: string) => {
    setBillingLoading(true);
    try {
      setBilling(
        await api.get<TenantBillingOverview>(`/platform/tenants/${tenantId}/billing`)
      );
    } catch {
      setBilling(null);
    } finally {
      setBillingLoading(false);
    }
  };

  const loadUsers = async (tenantId: string) => {
    setUsersLoading(true);
    try {
      setUsers(
        await api.get<TenantUserRow[]>(`/platform/tenants/${tenantId}/users`)
      );
    } catch {
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  };

  const load = async () => {
    setTenants(await api.get<TenantRow[]>("/platform/tenants"));
    setTemplates(await api.get<GroupTemplate[]>("/platform/group-templates"));
  };

  useEffect(() => {
    load();
  }, []);

  const syncAutoCode = (
    name: string,
    legalName: string,
    manual: boolean,
    currentCode: string
  ) => (manual ? currentCode : suggestAccountCode(name, legalName));

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setAccountCodeManual(false);
    setSheetTab("general");
    setSheetOpen(true);
  };

  const openSheet = async (t: TenantRow) => {
    let row = t;
    try {
      row = await api.get<TenantRow>(`/platform/tenants/${t.id}`);
    } catch {
      /* list row */
    }
    setEditingId(row.id);
    setForm(tenantToForm(row));
    setAccountCodeManual(true);
    setSheetTab("general");
    setUsers([]);
    setSheetOpen(true);
    void loadUsers(row.id);
    void loadBilling(row.id);
    void loadInvoices(row.id);
  };

  const closeSheet = () => {
    setSheetOpen(false);
    setEditingId(null);
    setForm(emptyForm());
    setAccountCodeManual(false);
    setSheetTab("general");
    setUsers([]);
    setBilling(null);
    setInvoices([]);
  };

  const handleTabChange = (tab: AccountSheetTab) => {
    setSheetTab(tab);
    if (!editingId) return;
    if (tab === "users") void loadUsers(editingId);
    if (tab === "billing") {
      void loadBilling(editingId);
      void loadInvoices(editingId);
    }
  };

  const onNameChange = (name: string) => {
    setForm((f) => ({
      ...f,
      name,
      accountCode: editingId
        ? f.accountCode
        : syncAutoCode(name, f.legal_name, accountCodeManual, f.accountCode),
    }));
  };

  const onLegalNameChange = (legal_name: string) => {
    setForm((f) => ({
      ...f,
      legal_name,
      accountCode: editingId
        ? f.accountCode
        : syncAutoCode(f.name, legal_name, accountCodeManual, f.accountCode),
    }));
  };

  const buildPayload = () => {
    const autoSlug = suggestAccountCode(form.name, form.legal_name);
    const slug = normalizeAccountCode(form.accountCode || autoSlug);
    if (!isValidAccountCode(slug)) {
      throw new Error(
        "Indica un nombre comercial válido para generar el código de cuenta."
      );
    }
    return {
      slug,
      name: form.name.trim(),
      legal_name: form.legal_name.trim(),
      tax_id: form.tax_id.trim(),
      billing_email: form.billing_email.trim(),
      billing_phone: form.billing_phone.trim(),
      billing_address: form.billing_address.trim() || undefined,
      billing_city: form.billing_city.trim() || undefined,
      billing_postal_code: form.billing_postal_code.trim() || undefined,
      billing_province: form.billing_province.trim() || undefined,
      billing_country: form.billing_country.trim() || "ES",
      is_active: form.is_active,
    };
  };

  const validateForm = (): AccountSheetTab | null => {
    if (!form.name.trim() || !form.legal_name.trim()) return "general";
    const autoSlug = suggestAccountCode(form.name, form.legal_name);
    const slug = normalizeAccountCode(form.accountCode || autoSlug);
    if (!isValidAccountCode(slug)) return "general";
    if (!form.tax_id.trim() || !form.billing_email.trim() || !form.billing_phone.trim()) {
      return "billing";
    }
    return null;
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    const invalidTab = validateForm();
    if (invalidTab) {
      setSheetTab(invalidTab);
      toast.error("Completa los campos obligatorios en General y Facturación.");
      return;
    }
    setSaving(true);
    try {
      const base = buildPayload();
      if (editingId) {
        await api.patch(`/platform/tenants/${editingId}`, base);
        toast.success(`Cuenta «${base.name}» actualizada correctamente`);
        void loadUsers(editingId);
        void loadBilling(editingId);
        void loadInvoices(editingId);
      } else {
        const body: Record<string, unknown> = { ...base };
        if (!accountCodeManual && !form.accountCode.trim()) {
          delete body.slug;
        }
        const created = await api.post<TenantRow>("/platform/tenants", body);
        toast.success(
          `Cuenta «${base.name}» creada. Código de acceso: ${created.slug}`
        );
        setEditingId(created.id);
        setForm(tenantToForm(created));
        setAccountCodeManual(true);
        setSheetTab("users");
        void loadUsers(created.id);
      }
      await load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async () => {
    if (!editingId) return;
    if (
      !confirm(
        `¿Desactivar la cuenta «${form.name}»? Los usuarios no podrán acceder.`
      )
    ) {
      return;
    }
    setSaving(true);
    try {
      await api.patch(`/platform/tenants/${editingId}`, { is_active: false });
      toast.success(`Cuenta «${form.name}» desactivada`);
      closeSheet();
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const reactivate = async () => {
    if (!editingId) return;
    setSaving(true);
    try {
      await api.patch(`/platform/tenants/${editingId}`, { is_active: true });
      toast.success(`Cuenta «${form.name}» reactivada`);
      setForm((f) => ({ ...f, is_active: true }));
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const removePermanent = async () => {
    if (!editingId) return;
    if (
      !confirm(
        `¿Eliminar permanentemente «${form.name}» (${form.accountCode})? Esta acción no se puede deshacer.`
      )
    ) {
      return;
    }
    setSaving(true);
    try {
      await api.delete(`/platform/tenants/${editingId}?permanent=true`);
      toast.success(`Cuenta «${form.name}» eliminada`);
      closeSheet();
      load();
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setSaving(false);
    }
  };

  const createTenantUser = async (data: TenantUserCreateForm) => {
    if (!editingId) return;
    setCreatingUser(true);
    try {
      await api.post(`/platform/tenants/${editingId}/users`, {
        ...data,
        email: data.email || undefined,
      });
      toast.success(`Usuario creado. Acceso: cuenta «${form.accountCode}»`);
      await loadUsers(editingId);
    } catch (err) {
      toast.error(String(err).replace(/^Error:\s*/i, ""));
      throw err;
    } finally {
      setCreatingUser(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Cuentas cliente"
        subtitle="Administración global de alcurro"
        action={
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            + Nueva cuenta
          </button>
        }
      />

      <section className="card settings-section">
        <h3>Grupos por defecto (nuevos clientes)</h3>
        <p className="muted small">
          Al crear una cuenta se clonan estos grupos con sus permisos.
        </p>
        <ul className="template-list">
          {templates.map((t) => (
            <li key={t.id}>
              <strong>{t.name}</strong>
              {t.is_system && <span className="badge"> Sistema</span>}
              <div className="muted small">{t.description}</div>
            </li>
          ))}
        </ul>
      </section>

      <DataTable
        data={tenantTableData}
        columns={tenantColumns}
        exportFilename="cuentas_cliente"
        onRowClick={(row) => void openSheet(row)}
      />
      <p className="muted small table-foot-hint">
        Haz clic en una fila para abrir la ficha de la cuenta.
      </p>

      <TenantAccountSheet
        open={sheetOpen}
        mode={sheetMode}
        tab={sheetTab}
        tenantId={editingId}
        form={form}
        accountCodeManual={accountCodeManual}
        saving={saving}
        users={users}
        usersLoading={usersLoading}
        billing={billing}
        billingLoading={billingLoading}
        invoices={invoices}
        invoicesLoading={invoicesLoading}
        subscription={tenants.find((x) => x.id === editingId)?.subscription ?? null}
        onBillingReload={() => {
          if (!editingId) return;
          void loadBilling(editingId);
          void loadInvoices(editingId);
          load();
        }}
        onTabChange={handleTabChange}
        onClose={closeSheet}
        onSave={save}
        onNameChange={onNameChange}
        onLegalNameChange={onLegalNameChange}
        onAccountCodeManual={setAccountCodeManual}
        onRegenerateCode={() => {
          setAccountCodeManual(false);
          setForm((f) => ({
            ...f,
            accountCode: suggestAccountCode(f.name, f.legal_name),
          }));
        }}
        onFormPatch={(patch) => setForm((f) => ({ ...f, ...patch }))}
        onDeactivate={editingId ? deactivate : undefined}
        onReactivate={editingId ? reactivate : undefined}
        onDelete={editingId ? removePermanent : undefined}
        onCreateTenantUser={editingId ? createTenantUser : undefined}
        creatingUser={creatingUser}
      />
    </>
  );
}
