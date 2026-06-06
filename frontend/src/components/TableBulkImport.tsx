import { useRef, useState } from "react";
import type { ImportColumn } from "../lib/tableImport";
import { downloadImportTemplate, mapImportRows, parseSpreadsheetFile } from "../lib/tableImport";

export interface BulkImportResult {
  created?: number;
  updated?: number;
  errors: string[];
}

interface Props {
  templateFilename: string;
  columns: ImportColumn[];
  hint?: string;
  disabled?: boolean;
  onImport: (rows: Record<string, string>[]) => Promise<BulkImportResult>;
  onComplete?: () => void;
}

export default function TableBulkImport({
  templateFilename,
  columns,
  hint,
  disabled,
  onImport,
  onComplete,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");

  const downloadTemplate = () => {
    downloadImportTemplate(templateFilename, columns);
  };

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setRunning(true);
    setMsg("");
    try {
      const raw = await parseSpreadsheetFile(file);
      const mapped = mapImportRows(raw, columns);
      if (!mapped.length) {
        setMsg("El archivo no contiene filas de datos.");
        return;
      }
      const res = await onImport(mapped);
      const parts: string[] = [];
      if (res.created != null) parts.push(`${res.created} creados`);
      if (res.updated != null) parts.push(`${res.updated} actualizados`);
      const ok = parts.length ? parts.join(", ") : "Importación completada";
      setMsg(
        res.errors.length
          ? `${ok}. ${res.errors.length} error(es): ${res.errors.slice(0, 3).join("; ")}${res.errors.length > 3 ? "…" : ""}`
          : ok
      );
      if (res.errors.length === 0 || (res.created ?? 0) + (res.updated ?? 0) > 0) {
        onComplete?.();
      }
    } catch (err) {
      setMsg(String(err).replace(/^Error:\s*/i, ""));
    } finally {
      setRunning(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="table-bulk-import">
      <button
        type="button"
        className="btn btn-sm btn-icon"
        disabled={disabled}
        onClick={downloadTemplate}
        title="Descargar plantilla Excel"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        <span>Plantilla</span>
      </button>
      <button
        type="button"
        className="btn btn-sm btn-icon"
        disabled={disabled || running}
        onClick={() => inputRef.current?.click()}
        title="Importar desde archivo"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <span>{running ? "Importando…" : "Importar"}</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls,.csv"
        hidden
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {hint && <span className="muted small table-bulk-import__hint">{hint}</span>}
      {msg && (
        <span
          className={`small table-bulk-import__msg ${
            msg.includes("error") ? "text-danger" : ""
          }`}
        >
          {msg}
        </span>
      )}
    </div>
  );
}
