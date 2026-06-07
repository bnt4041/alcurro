import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

interface LegalItem {
  document_id: string;
  code: string;
  title: string;
  body: string;
  version: number;
  is_required: boolean;
  accepted: boolean;
  accepted_at: string | null;
  accepted_version: number | null;
  needs_reaccept: boolean;
}

interface TokenPage {
  employee_name: string;
  tenant_name: string;
  pending_items: LegalItem[];
  all_accepted: boolean;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/legal/public${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : res.statusText);
  }
  return res.json() as Promise<T>;
}

export default function LegalTokenPage() {
  const { token } = useParams<{ token: string }>();
  const [page, setPage] = useState<TokenPage | null>(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    apiFetch<TokenPage>(`/token/${token}`)
      .then((data) => {
        setPage(data);
        if (data.all_accepted) setDone(true);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const currentDoc = page?.pending_items[currentIdx] ?? null;

  const handleAccept = async () => {
    if (!token || !currentDoc) return;
    setAccepting(true);
    setError("");
    try {
      const res = await apiFetch<{ document_id: string; accepted: boolean; remaining: number }>(
        `/token/${token}/accept/${currentDoc.document_id}`,
        { method: "POST" }
      );
      if (res.remaining === 0) {
        setDone(true);
      } else {
        setCurrentIdx((i) => i + 1);
      }
    } catch (err: unknown) {
      setError((err as Error).message);
    } finally {
      setAccepting(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <p style={styles.secondary}>Cargando documentos...</p>
        </div>
      </div>
    );
  }

  if (error && !page) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h2 style={styles.errorTitle}>Enlace no válido</h2>
          <p style={styles.secondary}>{error}</p>
          <p style={styles.hint}>Este enlace puede haber caducado (validez: 5 minutos). Solicita uno nuevo desde WhatsApp.</p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✓</div>
          <h2 style={styles.title}>Todo aceptado</h2>
          <p style={styles.secondary}>
            Has aceptado todos los textos legales requeridos. Se ha generado un certificado PDF
            que estará disponible en el apartado de documentos.
          </p>
          <p style={styles.hint}>Puedes cerrar esta página.</p>
        </div>
      </div>
    );
  }

  const total = page?.pending_items.length ?? 0;
  const progress = total > 0 ? Math.round((currentIdx / total) * 100) : 0;

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <p style={styles.tenantName}>{page?.tenant_name}</p>
          <h1 style={styles.title}>Aceptación de textos legales</h1>
          <p style={styles.secondary}>
            Hola, <strong>{page?.employee_name}</strong>. Para continuar usando el servicio
            es necesario que aceptes los siguientes documentos.
          </p>
        </div>

        {total > 1 && (
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
        )}
        {total > 1 && (
          <p style={styles.hint}>
            Documento {currentIdx + 1} de {total}
          </p>
        )}

        {currentDoc && (
          <div style={styles.docBox}>
            <h2 style={styles.docTitle}>{currentDoc.title}</h2>
            <p style={styles.docVersion}>Versión {currentDoc.version}</p>
            <div
              style={styles.docBody}
              dangerouslySetInnerHTML={{ __html: currentDoc.body }}
            />
          </div>
        )}

        {error && <p style={styles.errorMsg}>{error}</p>}

        <button
          style={accepting ? { ...styles.btn, ...styles.btnDisabled } : styles.btn}
          onClick={handleAccept}
          disabled={accepting}
        >
          {accepting ? "Procesando..." : "He leído y acepto este documento"}
        </button>

        <p style={styles.legalNote}>
          Al pulsar el botón confirmas que has leído y aceptas el contenido del documento.
          Se generará un certificado PDF con la fecha y hora de aceptación.
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#f1f5f9",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "center",
    padding: "2rem 1rem",
  },
  card: {
    background: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 2px 16px rgba(0,0,0,0.10)",
    padding: "2rem",
    width: "100%",
    maxWidth: "640px",
  },
  header: {
    marginBottom: "1.5rem",
  },
  tenantName: {
    fontSize: "0.78rem",
    fontWeight: 600,
    color: "#6b7280",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: "0.5rem",
  },
  title: {
    fontSize: "1.4rem",
    fontWeight: 700,
    color: "#12263a",
    margin: "0 0 0.5rem 0",
  },
  errorTitle: {
    fontSize: "1.4rem",
    fontWeight: 700,
    color: "#dc2626",
    margin: "0 0 0.5rem 0",
  },
  secondary: {
    color: "#374151",
    fontSize: "0.95rem",
    margin: 0,
  },
  hint: {
    color: "#6b7280",
    fontSize: "0.85rem",
    marginTop: "0.75rem",
  },
  progressBar: {
    height: "6px",
    background: "#e5e7eb",
    borderRadius: "3px",
    overflow: "hidden",
    marginBottom: "0.5rem",
  },
  progressFill: {
    height: "100%",
    background: "#2563eb",
    borderRadius: "3px",
    transition: "width 0.3s ease",
  },
  docBox: {
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "1.25rem",
    marginBottom: "1.5rem",
    background: "#fafafa",
  },
  docTitle: {
    fontSize: "1.05rem",
    fontWeight: 700,
    color: "#12263a",
    margin: "0 0 0.25rem 0",
  },
  docVersion: {
    fontSize: "0.78rem",
    color: "#9ca3af",
    margin: "0 0 1rem 0",
  },
  docBody: {
    fontSize: "0.88rem",
    color: "#374151",
    lineHeight: 1.65,
    maxHeight: "320px",
    overflowY: "auto",
  },
  btn: {
    display: "block",
    width: "100%",
    padding: "0.85rem",
    background: "#2563eb",
    color: "#ffffff",
    border: "none",
    borderRadius: "8px",
    fontSize: "1rem",
    fontWeight: 600,
    cursor: "pointer",
    marginBottom: "1rem",
  },
  btnDisabled: {
    background: "#93c5fd",
    cursor: "not-allowed",
  },
  legalNote: {
    fontSize: "0.78rem",
    color: "#9ca3af",
    textAlign: "center",
    margin: 0,
  },
  errorMsg: {
    color: "#dc2626",
    fontSize: "0.88rem",
    marginBottom: "1rem",
  },
  successIcon: {
    width: "56px",
    height: "56px",
    borderRadius: "50%",
    background: "#dcfce7",
    color: "#16a34a",
    fontSize: "1.8rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto 1rem auto",
  },
};
