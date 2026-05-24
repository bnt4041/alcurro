import { ReactNode } from "react";

interface Props {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
  tall?: boolean;
}

export default function Modal({ title, open, onClose, children, wide, tall }: Props) {
  if (!open) return null;
  const modalClass = [
    "modal",
    wide ? "modal-wide" : "",
    tall ? "modal-tall" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={modalClass} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <header className="modal-header">
          <h2>{title}</h2>
          <button type="button" className="btn-icon" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
