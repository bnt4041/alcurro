import { DragEvent, useRef, useState } from "react";

const DEFAULT_ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.gif";

interface Props {
  file: File | null;
  onFile: (file: File | null) => void;
  accept?: string;
  label?: string;
  hint?: string;
}

export default function FileDropzone({
  file,
  onFile,
  accept = DEFAULT_ACCEPT,
  label = "Arrastra el documento aquí",
  hint = "PDF o imagen (JPG, PNG, WebP). Máx. recomendado 15 MB.",
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = (f: File | undefined) => {
    if (!f) return;
    onFile(f);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    pick(e.dataTransfer.files?.[0]);
  };

  return (
    <div
      className={`file-dropzone ${dragOver ? "file-dropzone--active" : ""} ${file ? "file-dropzone--has-file" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragOver(false);
      }}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="file-dropzone-input"
        onChange={(e) => pick(e.target.files?.[0])}
      />
      {file ? (
        <>
          <span className="file-dropzone-icon">📄</span>
          <strong>{file.name}</strong>
          <span className="muted small">{(file.size / 1024).toFixed(0)} KB</span>
          <button
            type="button"
            className="btn btn-sm file-dropzone-clear"
            onClick={(e) => {
              e.stopPropagation();
              onFile(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
          >
            Quitar
          </button>
        </>
      ) : (
        <>
          <span className="file-dropzone-icon">⬆</span>
          <strong>{label}</strong>
          <span className="muted small">{hint}</span>
          <span className="muted small">o haz clic para elegir archivo</span>
        </>
      )}
    </div>
  );
}
