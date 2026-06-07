import { useEffect, useRef, useState } from "react";
import Modal from "./Modal";
import { getToken } from "../api/client";

interface Props {
  apiPath: string | null; // e.g. "/documents/{id}/preview" or "/signatures/{id}/signed"
  filename?: string;
  onClose: () => void;
}

function isImage(name: string): boolean {
  return /\.(jpe?g|png|gif|webp|svg|bmp)$/i.test(name);
}

export default function FilePreviewModal({ apiPath, filename = "", onClose }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const prevPath = useRef<string | null>(null);

  useEffect(() => {
    if (!apiPath || apiPath === prevPath.current) return;
    prevPath.current = apiPath;
    setBlobUrl(null);
    setError("");
    setLoading(true);

    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const companyId = localStorage.getItem("hrm_company_id");
    if (companyId) headers["X-Company-Id"] = companyId;

    fetch(`/api${apiPath}`, { headers })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Error ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        // Force PDF MIME so browsers render inline instead of downloading
        const mime = isImage(filename)
          ? blob.type || "image/jpeg"
          : "application/pdf";
        const typed = new Blob([blob], { type: mime });
        setBlobUrl(URL.createObjectURL(typed));
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [apiPath, filename]);

  // Revoke object URL on unmount / path change
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  const handleClose = () => {
    if (blobUrl) {
      URL.revokeObjectURL(blobUrl);
      setBlobUrl(null);
    }
    prevPath.current = null;
    onClose();
  };

  const img = isImage(filename);

  return (
    <Modal
      title={filename || "Vista previa"}
      open={!!apiPath}
      onClose={handleClose}
      xlarge
    >
      {loading && (
        <div style={{ textAlign: "center", padding: "3rem", color: "#6b7280" }}>
          Cargando documento…
        </div>
      )}
      {error && (
        <div style={{ textAlign: "center", padding: "3rem", color: "#dc2626" }}>
          {error}
        </div>
      )}
      {blobUrl && !img && (
        <iframe
          src={blobUrl}
          title={filename || "Documento"}
          style={{ width: "100%", height: "70vh", border: "none", borderRadius: "4px" }}
        />
      )}
      {blobUrl && img && (
        <div style={{ textAlign: "center" }}>
          <img
            src={blobUrl}
            alt={filename}
            style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain", borderRadius: "6px" }}
          />
        </div>
      )}
    </Modal>
  );
}
