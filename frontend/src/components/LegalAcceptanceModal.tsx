import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import Modal from "./Modal";

interface LegalStatusItem {
  document_id: string;
  code: string;
  title: string;
  body: string;
  version: number;
  is_required: boolean;
  accepted: boolean;
  needs_reaccept: boolean;
}

interface LegalStatus {
  all_required_accepted: boolean;
  items: LegalStatusItem[];
}

export default function LegalAcceptanceModal() {
  const [pending, setPending] = useState<LegalStatusItem[]>([]);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const status = await api.get<LegalStatus>("/legal/my/pending");
      const need = status.items.filter(
        (i) => i.is_required && (!i.accepted || i.needs_reaccept)
      );
      setPending(need);
      setChecked(false);
    } catch {
      setPending([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const current = pending[0];
  if (!current) return null;

  const accept = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post(`/legal/documents/${current.document_id}/accept`, {});
      setChecked(false);
      await load();
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Aceptación legal obligatoria" open onClose={() => {}}>
      <p className="muted small">
        Debes leer y aceptar los textos legales para continuar.
        {pending.length > 1 && <> ({pending.length} pendientes)</>}
      </p>
      <h3>{current.title}</h3>
      <p className="muted small">Versión {current.version}</p>
      <div className="legal-text legal-body-scroll">{current.body}</div>
      {error && <div className="alert alert-error">{error}</div>}
      <label className="checkbox">
        <input
          type="checkbox"
          checked={checked}
          onChange={(ev) => setChecked(ev.target.checked)}
        />
        He leído y acepto este documento
      </label>
      <div className="form-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={!checked || busy}
          onClick={accept}
        >
          {busy ? "Guardando…" : "Aceptar y continuar"}
        </button>
      </div>
    </Modal>
  );
}
