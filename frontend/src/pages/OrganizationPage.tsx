import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { canModule } from "../lib/permissions";
import { useToast } from "../context/ToastContext";

interface Department {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
}

interface WorkCenter {
  id: string;
  name: string;
  code: string;
  kiosk_token: string | null;
  departments: Department[];
}

const kioskUrl = (token: string) => `${window.location.origin}/kiosko/${token}`;

interface OrgTreeCompany {
  id: string;
  name: string;
  work_centers: WorkCenter[];
}

export default function OrganizationPage() {
  const { user } = useAuth();
  const { notify } = useToast();
  const [tree, setTree] = useState<OrgTreeCompany[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

  // Formulario nuevo centro de trabajo
  const [wcModalOpen, setWcModalOpen] = useState(false);
  const [wcForm, setWcForm] = useState({ name: "" });
  const [wcSaving, setWcSaving] = useState(false);

  // Formulario nuevo departamento
  const [deptModalOpen, setDeptModalOpen] = useState(false);
  const [deptForm, setDeptForm] = useState({ name: "", work_center_id: "" });
  const [deptSaving, setDeptSaving] = useState(false);

  // Modo kiosko
  const [kioskWc, setKioskWc] = useState<WorkCenter | null>(null);
  const [kioskBusy, setKioskBusy] = useState(false);
  const [kioskConfirm, setKioskConfirm] = useState<"regenerate" | "disable" | null>(null);

  const canWc = user && canModule(user.permissions, "write", "work_centers");
  const canDept = user && canModule(user.permissions, "write", "departments");

  const load = () =>
    api.get<OrgTreeCompany[]>("/org/tree").then((data) => {
      setTree(data);
      // Mantener la empresa seleccionada si aún existe, si no, seleccionar la primera
      setSelectedCompanyId((prev) =>
        data.find((c) => c.id === prev) ? prev : data[0]?.id ?? ""
      );
    });

  useEffect(() => {
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedCompany = tree.find((c) => c.id === selectedCompanyId) ?? tree[0];

  // WCs de la empresa actualmente seleccionada (no todas las empresas mezcladas)
  const currentWcs = selectedCompany?.work_centers ?? [];

  const addWc = async (e: FormEvent) => {
    e.preventDefault();
    setWcSaving(true);
    try {
      const created = await api.post<{ code: string }>("/org/work-centers", {
        name: wcForm.name,
        company_id: selectedCompany?.id,
      });
      setWcForm({ name: "" });
      setWcModalOpen(false);
      notify(`Centro creado (código ${created.code})`, "success");
      load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setWcSaving(false);
    }
  };

  const addDept = async (e: FormEvent) => {
    e.preventDefault();
    setDeptSaving(true);
    try {
      const created = await api.post<{ code: string }>("/org/departments", deptForm);
      setDeptForm({ name: "", work_center_id: "" });
      setDeptModalOpen(false);
      notify(`Departamento creado (código ${created.code})`, "success");
      load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setDeptSaving(false);
    }
  };

  const kioskAction = async (kind: "enable" | "regenerate" | "disable") => {
    if (!kioskWc) return;
    setKioskBusy(true);
    try {
      const path = `/org/work-centers/${kioskWc.id}/kiosk`;
      let token: string | null = null;
      if (kind === "disable") await api.delete(path);
      else token = (await api.post<{ kiosk_token: string | null }>(path, {})).kiosk_token;
      setKioskWc({ ...kioskWc, kiosk_token: token });
      setKioskConfirm(null);
      notify(
        kind === "disable"
          ? "Kiosko desactivado"
          : kind === "regenerate"
            ? "Enlace regenerado; el anterior ya no funciona"
            : "Kiosko activado",
        "success",
      );
      load();
    } catch (err) {
      notify(String(err).replace(/^Error:\s*/i, ""), "error");
    } finally {
      setKioskBusy(false);
    }
  };

  const copyKioskUrl = (token: string) =>
    navigator.clipboard
      .writeText(kioskUrl(token))
      .then(() => notify("Enlace copiado", "success"))
      .catch(() => notify("No se pudo copiar el enlace", "error"));

  return (
    <>
      <PageHeader
        title="Organización"
        subtitle="Empresa → Centro de trabajo → Departamento → Empleados"
        action={
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {canWc && (
              <button
                type="button"
                className="btn btn-sm btn-primary"
                onClick={() => setWcModalOpen(true)}
                disabled={!selectedCompany}
              >
                + Centro de trabajo
              </button>
            )}
            {canDept && (
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => {
                  setDeptForm({ name: "", work_center_id: currentWcs[0]?.id ?? "" });
                  setDeptModalOpen(true);
                }}
                disabled={currentWcs.length === 0}
              >
                + Departamento
              </button>
            )}
          </div>
        }
      />

      {/* Selector de empresa (solo si hay más de una) */}
      {tree.length > 1 && (
        <div className="card settings-section" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", margin: 0 }}>
            <strong>Empresa:</strong>
            <select
              value={selectedCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              style={{ minWidth: 200 }}
            >
              {tree.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          <span className="muted small">
            {currentWcs.length} centro{currentWcs.length !== 1 ? "s" : ""} de trabajo
          </span>
        </div>
      )}

      {/* Árbol de organización de la empresa seleccionada */}
      <div className="org-tree card">
        {tree.map((company) => (
          <div
            key={company.id}
            className="org-tree__company"
            style={{ display: tree.length > 1 && company.id !== selectedCompanyId ? "none" : undefined }}
          >
            {tree.length > 1 && <h3>{company.name}</h3>}
            {company.work_centers.length === 0 && (
              <p className="muted small">Sin centros de trabajo. Crea uno con el botón superior.</p>
            )}
            {company.work_centers.map((wc) => (
              <div key={wc.id} className="org-tree__wc">
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                  <strong>
                    {wc.name} <code>{wc.code}</code>
                  </strong>
                  {wc.kiosk_token && <span className="badge badge-ok">Kiosko activo</span>}
                  {canWc && (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => {
                        setKioskConfirm(null);
                        setKioskWc(wc);
                      }}
                    >
                      Kiosko
                    </button>
                  )}
                </div>
                {wc.departments.length === 0 ? (
                  <p className="muted small" style={{ marginLeft: "1rem" }}>Sin departamentos</p>
                ) : (
                  <ul>
                    {wc.departments.map((d) => (
                      <li key={d.id}>
                        {d.name} <code>{d.code}</code>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        ))}
        {tree.length === 0 && (
          <p className="muted">Cargando estructura organizativa…</p>
        )}
      </div>

      {/* Modal: nuevo centro de trabajo */}
      <Modal
        title={`Nuevo centro de trabajo${selectedCompany ? ` — ${selectedCompany.name}` : ""}`}
        open={wcModalOpen}
        onClose={() => setWcModalOpen(false)}
      >
        <form onSubmit={addWc}>
          <p className="muted small">
            El código se asigna automáticamente (p. ej. CEN-001, CEN-002…).
            {tree.length > 1 && (
              <> Se creará en la empresa <strong>{selectedCompany?.name}</strong>.</>
            )}
          </p>
          <div className="form-grid" style={{ marginTop: "1rem" }}>
            <label>
              Nombre <span className="required">*</span>
              <input
                required
                autoFocus
                value={wcForm.name}
                onChange={(e) => setWcForm({ name: e.target.value })}
              />
            </label>
          </div>
          <div className="form-actions" style={{ marginTop: "1.5rem" }}>
            <button type="button" className="btn" onClick={() => setWcModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={wcSaving}>
              {wcSaving ? "Creando…" : "Crear centro"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: modo kiosko del centro */}
      <Modal
        title={`Modo kiosko${kioskWc ? ` — ${kioskWc.name}` : ""}`}
        open={!!kioskWc}
        onClose={() => setKioskWc(null)}
      >
        {kioskWc && (
          <div>
            <p className="muted small">
              Enlace único para fichar en este centro desde una tablet u ordenador. Cada empleado
              se identifica con su código numérico y su PIN de kiosko (se configura en la ficha
              del empleado). Si tiene la jornada abierta se registra la salida; si no, la entrada.
              Una jornada abierta hace más de 12 h no se cierra: se abre una nueva y se genera una
              incidencia.
            </p>
            {kioskWc.kiosk_token ? (
              <>
                <label style={{ marginTop: "1rem", display: "block" }}>
                  Enlace del kiosko
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <input readOnly value={kioskUrl(kioskWc.kiosk_token)} onFocus={(e) => e.target.select()} />
                    <button type="button" className="btn" onClick={() => copyKioskUrl(kioskWc.kiosk_token!)}>
                      Copiar
                    </button>
                    <a className="btn" href={kioskUrl(kioskWc.kiosk_token)} target="_blank" rel="noreferrer">
                      Abrir
                    </a>
                  </div>
                </label>
                {kioskConfirm ? (
                  <div className="card" style={{ marginTop: "1rem", padding: "0.75rem" }}>
                    <p style={{ margin: 0 }}>
                      {kioskConfirm === "regenerate"
                        ? "Se creará un enlace nuevo y el actual dejará de funcionar en todos los dispositivos. ¿Continuar?"
                        : "El enlace dejará de funcionar y no se podrá fichar desde el kiosko de este centro. ¿Continuar?"}
                    </p>
                    <div className="form-actions" style={{ marginTop: "0.75rem" }}>
                      <button type="button" className="btn" onClick={() => setKioskConfirm(null)} disabled={kioskBusy}>
                        Cancelar
                      </button>
                      <button
                        type="button"
                        className={`btn ${kioskConfirm === "disable" ? "btn-danger" : "btn-primary"}`}
                        onClick={() => kioskAction(kioskConfirm)}
                        disabled={kioskBusy}
                      >
                        {kioskConfirm === "regenerate" ? "Regenerar enlace" : "Desactivar kiosko"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="form-actions" style={{ marginTop: "1.5rem" }}>
                    <button type="button" className="btn" onClick={() => setKioskConfirm("disable")}>
                      Desactivar
                    </button>
                    <button type="button" className="btn" onClick={() => setKioskConfirm("regenerate")}>
                      Regenerar enlace
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="form-actions" style={{ marginTop: "1.5rem" }}>
                <button type="button" className="btn" onClick={() => setKioskWc(null)}>
                  Cerrar
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => kioskAction("enable")}
                  disabled={kioskBusy}
                >
                  {kioskBusy ? "Activando…" : "Activar kiosko"}
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Modal: nuevo departamento */}
      <Modal
        title="Nuevo departamento"
        open={deptModalOpen}
        onClose={() => setDeptModalOpen(false)}
      >
        <form onSubmit={addDept}>
          <p className="muted small">
            El código se asigna automáticamente.
            {tree.length > 1 && (
              <> Solo se muestran centros de <strong>{selectedCompany?.name}</strong>.</>
            )}
          </p>
          <div className="form-grid" style={{ marginTop: "1rem" }}>
            <label>
              Centro de trabajo <span className="required">*</span>
              <select
                required
                value={deptForm.work_center_id}
                onChange={(e) => setDeptForm({ ...deptForm, work_center_id: e.target.value })}
              >
                <option value="">Seleccionar centro…</option>
                {/* Solo WCs de la empresa seleccionada */}
                {currentWcs.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Nombre <span className="required">*</span>
              <input
                required
                autoFocus
                value={deptForm.name}
                onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
              />
            </label>
          </div>
          <div className="form-actions" style={{ marginTop: "1.5rem" }}>
            <button type="button" className="btn" onClick={() => setDeptModalOpen(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={deptSaving}>
              {deptSaving ? "Creando…" : "Crear departamento"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
