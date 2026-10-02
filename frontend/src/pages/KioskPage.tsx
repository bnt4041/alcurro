import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import "../styles/kiosk.css";

const API = "/api/public/kiosk";

const PIN_MIN = 4;
const PIN_MAX = 6;
const CODE_MAX = 10;
const RESULT_RESET_MS = 6000;
const ERROR_RESET_MS = 3500;
const IDLE_RESET_MS = 30000;

interface KioskMeta {
  work_center_name: string;
  company_name: string;
  tenant_name: string;
  tenant_slug: string;
}

interface Branding {
  logo_url: string | null;
  primary_color: string;
}

interface ClockResult {
  action: "entrada" | "salida";
  employee_name: string;
  at: string;
  entrada_at: string | null;
  previous_expired: boolean;
}

type GeoState = "pending" | "ok" | "denied" | "unavailable";
type Step = "code" | "pin" | "sending" | "result" | "error";

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = Array.isArray(err.detail) ? "Datos no válidos" : err.detail;
    throw new Error(typeof detail === "string" ? detail : res.statusText);
  }
  return res.json() as Promise<T>;
}

const fmtTime = (d: Date) => d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });

function workedLabel(from: string, to: string): string {
  const mins = Math.max(0, Math.round((new Date(to).getTime() - new Date(from).getTime()) / 60000));
  return `${Math.floor(mins / 60)} h ${String(mins % 60).padStart(2, "0")} min`;
}

export default function KioskPage() {
  const { token } = useParams<{ token: string }>();
  const [meta, setMeta] = useState<KioskMeta | null>(null);
  const [branding, setBranding] = useState<Branding | null>(null);
  const [loadError, setLoadError] = useState("");
  const [now, setNow] = useState(() => new Date());

  const [geo, setGeo] = useState<GeoState>("pending");
  const position = useRef<GeolocationPosition | null>(null);

  const [step, setStep] = useState<Step>("code");
  const [code, setCode] = useState("");
  const [pin, setPin] = useState("");
  const [result, setResult] = useState<ClockResult | null>(null);
  const [error, setError] = useState("");
  const resetTimer = useRef<number | undefined>(undefined);

  // --- Datos del centro + branding ---
  useEffect(() => {
    if (!token) return;
    publicFetch<KioskMeta>(`/${token}`)
      .then((m) => {
        setMeta(m);
        document.title = `Fichaje · ${m.work_center_name}`;
        fetch(`/api/tenants/public/${encodeURIComponent(m.tenant_slug)}/branding`)
          .then((r) => (r.ok ? r.json() : null))
          .then((b) => b && setBranding(b))
          .catch(() => undefined);
      })
      .catch((e) => setLoadError(String(e.message || e)));
  }, [token]);

  // --- Reloj ---
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  // --- Geolocalización ---
  const onGeoError = useCallback((err: GeolocationPositionError) => {
    if (err.code === err.PERMISSION_DENIED) setGeo("denied");
    else if (!position.current) setGeo("unavailable");
  }, []);

  const onGeo = useCallback((pos: GeolocationPosition) => {
    position.current = pos;
    setGeo("ok");
  }, []);

  const requestGeo = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setGeo("unavailable");
      return;
    }
    setGeo((g) => (g === "ok" ? g : "pending"));
    navigator.geolocation.getCurrentPosition(onGeo, onGeoError, {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 60000,
    });
  }, [onGeo, onGeoError]);

  useEffect(() => {
    if (!meta || !("geolocation" in navigator)) {
      if (meta) setGeo("unavailable");
      return;
    }
    requestGeo();
    const id = navigator.geolocation.watchPosition(onGeo, onGeoError, {
      enableHighAccuracy: true,
      maximumAge: 60000,
    });
    return () => navigator.geolocation.clearWatch(id);
  }, [meta, requestGeo, onGeo, onGeoError]);

  // --- Flujo ---
  const reset = useCallback(() => {
    window.clearTimeout(resetTimer.current);
    setStep("code");
    setCode("");
    setPin("");
    setResult(null);
    setError("");
  }, []);

  const scheduleReset = useCallback(
    (ms: number) => {
      window.clearTimeout(resetTimer.current);
      resetTimer.current = window.setTimeout(reset, ms);
    },
    [reset],
  );

  useEffect(() => () => window.clearTimeout(resetTimer.current), []);

  // Inactividad a mitad de fichaje → volver al inicio
  useEffect(() => {
    if ((step === "code" && code) || step === "pin") scheduleReset(IDLE_RESET_MS);
  }, [step, code, pin, scheduleReset]);

  const submit = useCallback(
    async (pinValue: string) => {
      if (!token) return;
      const pos = position.current;
      if (!pos) {
        setError(
          geo === "denied"
            ? "Activa el permiso de ubicación para poder fichar."
            : "Obteniendo ubicación… inténtalo de nuevo en unos segundos.",
        );
        setStep("error");
        requestGeo();
        scheduleReset(ERROR_RESET_MS);
        return;
      }
      setStep("sending");
      try {
        const res = await publicFetch<ClockResult>(`/${token}/fichar`, {
          method: "POST",
          body: JSON.stringify({
            employee_code: code,
            pin: pinValue,
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          }),
        });
        setResult(res);
        setStep("result");
        scheduleReset(RESULT_RESET_MS);
      } catch (e) {
        setError(String((e as Error).message || e));
        setStep("error");
        scheduleReset(ERROR_RESET_MS);
      }
    },
    [token, code, geo, requestGeo, scheduleReset],
  );

  const pressDigit = useCallback(
    (d: string) => {
      if (step === "code") setCode((c) => (c.length < CODE_MAX ? c + d : c));
      else if (step === "pin") setPin((p) => (p.length < PIN_MAX ? p + d : p));
    },
    [step],
  );

  const pressBack = useCallback(() => {
    if (step === "code") setCode((c) => c.slice(0, -1));
    else if (step === "pin") {
      if (pin) setPin((p) => p.slice(0, -1));
      else setStep("code");
    }
  }, [step, pin]);

  const pressOk = useCallback(() => {
    if (step === "code" && code) {
      setPin("");
      setStep("pin");
    } else if (step === "pin" && pin.length >= PIN_MIN) {
      void submit(pin);
    } else if (step === "result" || step === "error") {
      reset();
    }
  }, [step, code, pin, submit, reset]);

  // Teclado físico
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) pressDigit(e.key);
      else if (e.key === "Backspace") pressBack();
      else if (e.key === "Enter") pressOk();
      else if (e.key === "Escape") reset();
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pressDigit, pressBack, pressOk, reset]);

  const style = branding?.primary_color
    ? ({ "--kiosk-primary": branding.primary_color } as React.CSSProperties)
    : undefined;

  if (loadError) {
    return (
      <div className="kiosk kiosk--center" style={style}>
        <div className="kiosk-panel">
          <h1>Kiosko no disponible</h1>
          <p className="kiosk-muted">{loadError}</p>
        </div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="kiosk kiosk--center">
        <p className="kiosk-muted">Cargando…</p>
      </div>
    );
  }

  const keypadActive = step === "code" || step === "pin";
  const okEnabled = (step === "code" && !!code) || (step === "pin" && pin.length >= PIN_MIN);

  return (
    <div className="kiosk" style={style}>
      <header className="kiosk-header">
        <div className="kiosk-brand">
          {branding?.logo_url && <img src={branding.logo_url} alt={meta.tenant_name} />}
          <div>
            <strong>{meta.work_center_name}</strong>
            <span className="kiosk-muted">{meta.company_name}</span>
          </div>
        </div>
        <div className="kiosk-clock">
          <span className="kiosk-clock__time">
            {now.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
          <span className="kiosk-muted">
            {now.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" })}
          </span>
        </div>
      </header>

      <div className={`kiosk-geo kiosk-geo--${geo}`}>
        {geo === "ok" && "📍 Ubicación activa"}
        {geo === "pending" && "📍 Solicitando ubicación…"}
        {geo === "denied" && (
          <>
            ⚠️ Permiso de ubicación denegado. Actívalo en la configuración del navegador para fichar.
            <button type="button" onClick={requestGeo}>Reintentar</button>
          </>
        )}
        {geo === "unavailable" && (
          <>
            ⚠️ No se pudo obtener la ubicación.
            <button type="button" onClick={requestGeo}>Reintentar</button>
          </>
        )}
      </div>

      <main className="kiosk-panel">
        {step === "result" && result && (
          <div className={`kiosk-result kiosk-result--${result.action}`}>
            <div className="kiosk-result__icon">{result.action === "entrada" ? "→" : "←"}</div>
            <h1>{result.action === "entrada" ? "Entrada registrada" : "Salida registrada"}</h1>
            <p className="kiosk-result__name">{result.employee_name}</p>
            <p className="kiosk-result__time">{fmtTime(new Date(result.at))}</p>
            {result.action === "salida" && result.entrada_at && (
              <p className="kiosk-muted">
                Entrada a las {fmtTime(new Date(result.entrada_at))} · {workedLabel(result.entrada_at, result.at)}
              </p>
            )}
            {result.previous_expired && (
              <p className="kiosk-warning">
                Tu jornada anterior llevaba más de 12 h abierta y no se ha podido cerrar. Se ha
                abierto una nueva jornada y RRHH revisará la anterior.
              </p>
            )}
            <button type="button" className="kiosk-btn" onClick={reset}>Aceptar</button>
          </div>
        )}

        {step === "error" && (
          <div className="kiosk-result kiosk-result--error">
            <div className="kiosk-result__icon">!</div>
            <h1>No se pudo fichar</h1>
            <p>{error}</p>
            <button type="button" className="kiosk-btn" onClick={reset}>Volver</button>
          </div>
        )}

        {step === "sending" && (
          <div className="kiosk-result">
            <div className="kiosk-spinner" />
            <p className="kiosk-muted">Registrando fichaje…</p>
          </div>
        )}

        {keypadActive && (
          <>
            <p className="kiosk-prompt">
              {step === "code" ? "Introduce tu código de empleado" : "Introduce tu PIN"}
            </p>
            <div className="kiosk-display" aria-live="polite">
              {step === "code"
                ? code || <span className="kiosk-muted">—</span>
                : Array.from({ length: Math.max(PIN_MIN, pin.length) }, (_, i) => (
                    <span key={i} className={`kiosk-dot${i < pin.length ? " kiosk-dot--on" : ""}`} />
                  ))}
            </div>
            {step === "pin" && <p className="kiosk-muted kiosk-sub">Código {code}</p>}
            <div className="kiosk-keypad">
              {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
                <button key={d} type="button" onClick={() => pressDigit(d)}>
                  {d}
                </button>
              ))}
              <button type="button" className="kiosk-key--alt" onClick={pressBack} aria-label="Borrar">
                ⌫
              </button>
              <button type="button" onClick={() => pressDigit("0")}>
                0
              </button>
              <button
                type="button"
                className="kiosk-key--ok"
                onClick={pressOk}
                disabled={!okEnabled}
                aria-label={step === "code" ? "Continuar" : "Fichar"}
              >
                {step === "code" ? "→" : "✓"}
              </button>
            </div>
          </>
        )}
      </main>

      <footer className="kiosk-footer kiosk-muted">{meta.tenant_name} · Registro de jornada</footer>
    </div>
  );
}
