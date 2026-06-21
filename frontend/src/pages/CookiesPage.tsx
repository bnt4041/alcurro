import { Link } from "react-router-dom";

export default function CookiesPage() {
  const clearConsent = () => {
    localStorage.removeItem("cookie_consent");
    window.location.reload();
  };

  return (
    <div className="legal-static">
      <div className="landing-container legal-static__inner">
        <Link to="/" className="legal-static__back">← Volver al inicio</Link>
        <h1>Política de Cookies</h1>
        <p className="legal-static__updated">Última actualización: junio 2025</p>

        <h2>¿Qué es una cookie?</h2>
        <p>
          Una cookie es un pequeño archivo de texto que un sitio web almacena en tu
          dispositivo cuando lo visitas. Las cookies se usan para que la web recuerde
          tus preferencias, mantener tu sesión activa o analizar cómo se usa el servicio.
        </p>

        <h2>¿Qué cookies usamos?</h2>
        <table className="legal-table">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Duración</th>
              <th>Finalidad</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>alcurro_session</code></td>
              <td>Esencial</td>
              <td>Sesión</td>
              <td>Mantiene la sesión del usuario autenticado</td>
            </tr>
            <tr>
              <td><code>cookie_consent</code></td>
              <td>Esencial</td>
              <td>1 año</td>
              <td>Guarda tu elección sobre el aviso de cookies</td>
            </tr>
            <tr>
              <td><code>access_token</code> (localStorage)</td>
              <td>Esencial</td>
              <td>Sesión / hasta logout</td>
              <td>Token JWT de autenticación en la app</td>
            </tr>
          </tbody>
        </table>

        <p>
          <strong>alcurro no utiliza cookies de rastreo, publicidad ni analítica de terceros.</strong>{" "}
          No hay Google Analytics, Facebook Pixel ni tecnologías similares en este sitio.
        </p>

        <h2>Cookies de terceros</h2>
        <p>
          Durante el proceso de pago, <strong>Stripe</strong> puede instalar cookies propias
          para prevenir el fraude y garantizar la seguridad de la transacción. Estas cookies
          están sujetas a la{" "}
          <a href="https://stripe.com/es/privacy" target="_blank" rel="noopener noreferrer">
            política de privacidad de Stripe
          </a>.
        </p>

        <h2>Cómo gestionar las cookies</h2>
        <p>
          Puedes configurar tu navegador para rechazar todas las cookies, eliminar las
          existentes o avisarte cuando se vaya a instalar una. Ten en cuenta que deshabilitar
          las cookies esenciales puede impedir el funcionamiento correcto de la plataforma.
        </p>
        <ul>
          <li><a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener noreferrer">Google Chrome</a></li>
          <li><a href="https://support.mozilla.org/es/kb/habilitar-y-deshabilitar-cookies-sitios-web" target="_blank" rel="noopener noreferrer">Mozilla Firefox</a></li>
          <li><a href="https://support.apple.com/es-es/guide/safari/sfri11471/mac" target="_blank" rel="noopener noreferrer">Safari</a></li>
          <li><a href="https://support.microsoft.com/es-es/microsoft-edge/eliminar-las-cookies-en-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09" target="_blank" rel="noopener noreferrer">Microsoft Edge</a></li>
        </ul>

        <h2>Gestión de tu consentimiento</h2>
        <p>
          Puedes retirar o modificar tu consentimiento en cualquier momento. Al pulsar el
          botón siguiente se restablece el banner de cookies para que puedas elegir de nuevo:
        </p>
        <button type="button" className="btn btn-secondary" onClick={clearConsent}>
          Restablecer preferencias de cookies
        </button>

        <div className="legal-static__footer-links">
          <Link to="/aviso-legal">Aviso Legal</Link>
          <Link to="/condiciones">Condiciones del Servicio</Link>
          <Link to="/privacidad">Política de Privacidad</Link>
        </div>
      </div>
    </div>
  );
}
