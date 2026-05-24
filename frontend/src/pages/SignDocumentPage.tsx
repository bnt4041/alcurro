import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import SignatureCanvas from "../components/SignatureCanvas";
import BrandLogo from "../components/BrandLogo";

const API = "/api/public/firma";

interface Meta {
  full_name: string;
  document_title: string;
  company_name: string;
  email_hint: string | null;
  phone_hint: string | null;
  status: string;
  envelope_status: string;
}

type Step = "identify" | "otp" | "sign" | "done";

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : res.statusText);
  }
  return res.json() as Promise<T>;
}

export default function SignDocumentPage() {
  const { token } = useParams<{ token: string }>();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [step, setStep] = useState<Step>("identify");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [idDocument, setIdDocument] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [signerName, setSignerName] = useState("");
  const [signature, setSignature] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    if (!token) return;
    publicFetch<Meta>(`/${token}`)
      .then((m) => {
        setMeta(m);
        setSignerName(m.full_name);
        if (m.status === "firmado") setStep("done");
      })
      .catch((e) => setError(String(e.message || e)));
  }, [token]);

  const start = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await publicFetch(`/${token}/start`, {
        method: "POST",
        body: JSON.stringify({
          id_document: idDocument,
          email: email || undefined,
          phone: phone || undefined,
        }),
      });
      setStep("otp");
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await publicFetch(`/${token}/verify-otp`, {
        method: "POST",
        body: JSON.stringify({ code: otp }),
      });
      setStep("sign");
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setBusy(false);
    }
  };

  const sign = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !signature) return;
    setBusy(true);
    setError("");
    try {
      const res = await publicFetch<{ envelope_completed: string }>(`/${token}/sign`, {
        method: "POST",
        body: JSON.stringify({
          signature_base64: signature,
          signer_name: signerName,
          accept_terms: true,
        }),
      });
      setCompleted(res.envelope_completed === "true");
      setStep("done");
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!token) return;
    window.open(`${API}/${token}/download-signed`, "_blank");
  };

  return (
    <div className="sign-page">
      <header className="sign-page-header">
        <BrandLogo variant="light" />
        <h1>Firma electrónica</h1>
      </header>
      <main className="sign-page-main card">
        {error && <div className="alert alert-error">{error}</div>}
        {!meta && !error && <p className="muted">Cargando…</p>}
        {meta && (
          <>
            <p className="muted small">
              {meta.company_name} · {meta.document_title}
            </p>
            <p>
              Hola, <strong>{meta.full_name}</strong>
            </p>

            {step === "identify" && (
              <form onSubmit={start} className="form-grid">
                <p className="form-grid-full muted small">
                  Confirma tu identidad. Te enviaremos un código por WhatsApp
                  {meta.phone_hint && <> al número terminado en {meta.phone_hint}</>}.
                </p>
                <label>
                  DNI/NIE
                  <input
                    required
                    placeholder="12345678Z"
                    value={idDocument}
                    onChange={(ev) => setIdDocument(ev.target.value.toUpperCase())}
                  />
                </label>
                {meta.email_hint && (
                  <label>
                    Email (termina en {meta.email_hint})
                    <input
                      type="email"
                      value={email}
                      onChange={(ev) => setEmail(ev.target.value)}
                    />
                  </label>
                )}
                {meta.phone_hint && (
                  <label>
                    Teléfono
                    <input
                      value={phone}
                      onChange={(ev) => setPhone(ev.target.value)}
                      placeholder="Opcional si coincide el de RRHH"
                    />
                  </label>
                )}
                <div className="form-actions form-grid-full">
                  <button type="submit" className="btn btn-primary" disabled={busy}>
                    {busy ? "Enviando…" : "Recibir código"}
                  </button>
                </div>
              </form>
            )}

            {step === "otp" && (
              <form onSubmit={verify} className="form-grid">
                <label className="form-grid-full">
                  Código de verificación
                  <input
                    required
                    inputMode="numeric"
                    maxLength={6}
                    value={otp}
                    onChange={(ev) => setOtp(ev.target.value)}
                  />
                </label>
                <div className="form-actions form-grid-full">
                  <button type="submit" className="btn btn-primary" disabled={busy}>
                    Verificar
                  </button>
                </div>
              </form>
            )}

            {step === "sign" && (
              <form onSubmit={sign} className="form-grid">
                <label>
                  Nombre al firmar
                  <input
                    required
                    value={signerName}
                    onChange={(ev) => setSignerName(ev.target.value)}
                  />
                </label>
                <div className="form-grid-full">
                  <span className="label-like">Firma manuscrita</span>
                  <SignatureCanvas onChange={setSignature} />
                </div>
                <label className="checkbox form-grid-full">
                  <input type="checkbox" required defaultChecked />
                  Acepto que esta firma tiene validez como acuse de conformidad con el documento
                </label>
                <div className="form-actions form-grid-full">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={busy || !signature}
                  >
                    Firmar documento
                  </button>
                </div>
              </form>
            )}

            {step === "done" && (
              <div className="alert alert-ok">
                <p>Firma registrada correctamente.</p>
                {completed && (
                  <p className="small">
                    Todas las firmas están completadas. Puedes descargar el PDF firmado.
                  </p>
                )}
                {completed && (
                  <button type="button" className="btn btn-primary" onClick={download}>
                    Descargar PDF firmado
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
