import { useEffect, useState } from "react";
import { publicApi } from "../api/public";

const DEFAULT_TEXT =
  "¡Hola! Me gustaría más información sobre Alcurro y cómo solicitar acceso para mi empresa.";

/**
 * Botón flotante que abre WhatsApp con la línea comercial de Alcurro.
 * El número se lee de /public/site-config; si no está configurado, no se muestra.
 */
export default function WhatsAppFab() {
  const [number, setNumber] = useState<string | null>(null);

  useEffect(() => {
    publicApi
      .getSiteConfig()
      .then((c) => setNumber(c.whatsapp_number))
      .catch(() => setNumber(null));
  }, []);

  if (!number) return null;

  const href = `https://wa.me/${number}?text=${encodeURIComponent(DEFAULT_TEXT)}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="wa-fab"
      aria-label="Hablar por WhatsApp con Alcurro"
      title="¿Dudas? Escríbenos por WhatsApp"
    >
      <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden focusable="false">
        <path
          fill="currentColor"
          d="M16.003 3.2c-7.06 0-12.8 5.74-12.8 12.8 0 2.26.6 4.46 1.73 6.4L3.2 28.8l6.57-1.72a12.74 12.74 0 0 0 6.23 1.62h.01c7.06 0 12.8-5.74 12.8-12.8s-5.74-12.7-12.8-12.7zm0 23.04h-.01a10.6 10.6 0 0 1-5.4-1.48l-.39-.23-3.9 1.02 1.04-3.8-.25-.4a10.56 10.56 0 0 1-1.62-5.65c0-5.87 4.78-10.64 10.65-10.64 2.84 0 5.51 1.11 7.52 3.12a10.56 10.56 0 0 1 3.12 7.53c0 5.87-4.78 10.5-10.62 10.5zm5.84-7.92c-.32-.16-1.9-.94-2.19-1.04-.29-.11-.5-.16-.72.16-.21.32-.82 1.04-1.01 1.25-.19.21-.37.24-.69.08-.32-.16-1.35-.5-2.57-1.59-.95-.85-1.59-1.9-1.78-2.22-.19-.32-.02-.49.14-.65.14-.14.32-.37.48-.56.16-.19.21-.32.32-.53.11-.21.05-.4-.03-.56-.08-.16-.72-1.74-.99-2.38-.26-.62-.52-.54-.72-.55h-.61c-.21 0-.56.08-.85.4-.29.32-1.12 1.09-1.12 2.66s1.15 3.09 1.31 3.3c.16.21 2.26 3.45 5.48 4.84.77.33 1.36.53 1.83.68.77.24 1.47.21 2.02.13.62-.09 1.9-.78 2.17-1.53.27-.75.27-1.39.19-1.53-.08-.13-.29-.21-.61-.37z"
        />
      </svg>
    </a>
  );
}
