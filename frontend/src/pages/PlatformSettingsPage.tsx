import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useToast } from "../context/ToastContext";

interface PlatformSettings {
  id: string;
  legal_name: string;
  tax_id: string;
  billing_address: string | null;
  billing_city: string | null;
  billing_postal_code: string | null;
  billing_province: string | null;
  billing_country: string;
  billing_email: string | null;
  billing_phone: string | null;
  website: string | null;
  iban: string | null;
  bank_name: string | null;
  swift_bic: string | null;
  invoice_prefix: string;
  invoice_next_number: number;
  invoice_current_year: number;
  vat_rate: number;
  invoice_footer_text: string | null;
  credit_note_prefix: string;
  credit_note_next_number: number;
  credit_note_current_year: number;
  auto_send_invoice_email: boolean;
}

export default function PlatformSettingsPage() {
  const { notify } = useToast();
  const [data, setData] = useState<PlatformSettings | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const res = await api.get<PlatformSettings>("/platform/settings");
    setData(res);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      await api.patch("/platform/settings", data);
      notify("Configuración guardada", "success");
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setSaving(false);
    }
  };

  if (!data) return <p className="muted">Cargando…</p>;

  const set = (field: keyof PlatformSettings, value: string | number | boolean | null) =>
    setData((prev) => prev ? { ...prev, [field]: value } : prev);

  return (
    <>
      <PageHeader
        title="Configuración de plataforma"
        subtitle="Datos fiscales de alcurro y parámetros de facturación"
      />

      <form onSubmit={handleSubmit}>
        <section className="card settings-section">
          <h3>Datos fiscales del emisor</h3>
          <p className="muted small">
            Estos datos aparecen en todas las facturas emitidas a los clientes como datos del proveedor (alcurro).
          </p>
          <div className="form-grid">
            <label>
              Razón social <span className="required">*</span>
              <input
                required
                value={data.legal_name}
                onChange={(e) => set("legal_name", e.target.value)}
              />
            </label>
            <label>
              CIF / NIF <span className="required">*</span>
              <input
                required
                value={data.tax_id}
                onChange={(e) => set("tax_id", e.target.value)}
              />
            </label>
            <label>
              Email de facturación
              <input
                type="email"
                value={data.billing_email ?? ""}
                onChange={(e) => set("billing_email", e.target.value || null)}
              />
            </label>
            <label>
              Teléfono
              <input
                value={data.billing_phone ?? ""}
                onChange={(e) => set("billing_phone", e.target.value || null)}
              />
            </label>
            <label>
              Sitio web
              <input
                value={data.website ?? ""}
                onChange={(e) => set("website", e.target.value || null)}
              />
            </label>
            <label>
              Dirección
              <input
                value={data.billing_address ?? ""}
                onChange={(e) => set("billing_address", e.target.value || null)}
              />
            </label>
            <label>
              Ciudad
              <input
                value={data.billing_city ?? ""}
                onChange={(e) => set("billing_city", e.target.value || null)}
              />
            </label>
            <label>
              Código postal
              <input
                value={data.billing_postal_code ?? ""}
                onChange={(e) => set("billing_postal_code", e.target.value || null)}
              />
            </label>
            <label>
              Provincia
              <input
                value={data.billing_province ?? ""}
                onChange={(e) => set("billing_province", e.target.value || null)}
              />
            </label>
            <label>
              País (código ISO)
              <input
                maxLength={2}
                value={data.billing_country}
                onChange={(e) => set("billing_country", e.target.value.toUpperCase())}
              />
            </label>
          </div>
        </section>

        <section className="card settings-section">
          <h3>Datos bancarios</h3>
          <p className="muted small">
            Se muestran en el pie de cada factura para facilitar el pago por transferencia.
          </p>
          <div className="form-grid">
            <label>
              IBAN
              <input
                value={data.iban ?? ""}
                onChange={(e) => set("iban", e.target.value || null)}
                placeholder="ES00 0000 0000 0000 0000 0000"
              />
            </label>
            <label>
              Entidad bancaria
              <input
                value={data.bank_name ?? ""}
                onChange={(e) => set("bank_name", e.target.value || null)}
              />
            </label>
            <label>
              SWIFT / BIC
              <input
                value={data.swift_bic ?? ""}
                onChange={(e) => set("swift_bic", e.target.value || null)}
              />
            </label>
          </div>
        </section>

        <section className="card settings-section">
          <h3>Configuración de facturación</h3>
          <div className="form-grid">
            <label>
              Prefijo de factura
              <input
                required
                maxLength={10}
                value={data.invoice_prefix}
                onChange={(e) => set("invoice_prefix", e.target.value.toUpperCase())}
                placeholder="ALC"
                style={{ maxWidth: 120 }}
              />
            </label>
            <label>
              Siguiente número
              <input
                type="number"
                min={1}
                value={data.invoice_next_number}
                onChange={(e) => set("invoice_next_number", parseInt(e.target.value) || 1)}
                style={{ maxWidth: 120 }}
              />
            </label>
            <label>
              Tipo de IVA (%)
              <input
                type="number"
                min={0}
                max={100}
                value={data.vat_rate}
                onChange={(e) => set("vat_rate", parseInt(e.target.value) || 21)}
                style={{ maxWidth: 100 }}
              />
            </label>
            <label>
              Prefijo de factura de abono
              <input
                required
                maxLength={10}
                value={data.credit_note_prefix}
                onChange={(e) => set("credit_note_prefix", e.target.value.toUpperCase())}
                placeholder="ALC-R"
                style={{ maxWidth: 120 }}
              />
            </label>
            <label>
              Siguiente nº de abono
              <input
                type="number"
                min={1}
                value={data.credit_note_next_number}
                onChange={(e) => set("credit_note_next_number", parseInt(e.target.value) || 1)}
                style={{ maxWidth: 120 }}
              />
            </label>
            <label style={{ gridColumn: "1 / -1" }}>
              Texto de pie de factura
              <textarea
                rows={3}
                value={data.invoice_footer_text ?? ""}
                onChange={(e) => set("invoice_footer_text", e.target.value || null)}
                placeholder="Información adicional que aparecerá al pie de cada factura…"
              />
            </label>
          </div>
        </section>

        <section className="card settings-section">
          <h3>Automatizaciones</h3>
          <div className="form-grid">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={data.auto_send_invoice_email}
                onChange={(e) => set("auto_send_invoice_email", e.target.checked)}
              />
              <span>
                <strong>Enviar factura automáticamente por email</strong>
                <br />
                <span className="muted small">
                  Al recibir un pago de Lemon Squeezy, se genera la factura y se envía por email al cliente.
                  Requiere SMTP configurado y que el cliente tenga email de facturación.
                </span>
              </span>
            </label>
          </div>
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            Año actual: <strong>{data.invoice_current_year}</strong> · El contador de número se reinicia automáticamente cada año.
          </p>
        </section>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Guardando…" : "Guardar configuración"}
          </button>
        </div>
      </form>
    </>
  );
}
