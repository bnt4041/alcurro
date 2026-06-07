import { ReactNode } from "react";

interface Props {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
  tall?: boolean;
  xlarge?: boolean;
}

export default function Modal({ title, open, onClose, children, wide, tall, xlarge }: Props) {
  if (!open) return null;
  const modalClass = [
    "modal",
    xlarge ? "modal-xlarge" : wide ? "modal-wide" : "",
    tall || xlarge ? "modal-tall" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className="modal-overlay">
      <div className={modalClass} role="dialog" aria-modal="true">
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
