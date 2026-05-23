import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import ToastContainer, { ToastItem, ToastType } from "../components/ToastContainer";
import { fireConfetti } from "../lib/confetti";

export type NotifyOptions = {
  /** Lanzar confeti (por defecto en success). */
  confetti?: boolean;
  /** ms hasta auto-cerrar (por defecto 4200). */
  duration?: number;
};

type ToastContextValue = {
  notify: (message: string, type?: ToastType, options?: NotifyOptions) => void;
  success: (message: string, options?: NotifyOptions) => void;
  error: (message: string, options?: NotifyOptions) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

let toastSeq = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, type: ToastType = "info", options?: NotifyOptions) => {
      const id = `toast-${++toastSeq}`;
      const duration = options?.duration ?? 4200;
      const withConfetti =
        options?.confetti ?? (type === "success");

      setToasts((prev) => [...prev, { id, message, type }]);

      if (withConfetti && type === "success") {
        fireConfetti();
      }

      window.setTimeout(() => dismiss(id), duration);
    },
    [dismiss]
  );

  const value = useMemo(
    () => ({
      notify,
      success: (message: string, options?: NotifyOptions) =>
        notify(message, "success", options),
      error: (message: string, options?: NotifyOptions) =>
        notify(message, "error", { ...options, confetti: false }),
    }),
    [notify]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast debe usarse dentro de ToastProvider");
  return ctx;
}
