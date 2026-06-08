import { Link } from "react-router-dom";

export default function ContactoPage() {
  return (
    <div className="legal-static">
      <div className="landing-container legal-static__inner legal-static__inner--contact">
        <Link to="/" className="legal-static__back">← Volver al inicio</Link>
        <h1>Contacto y soporte</h1>
        <p className="legal-static__lead">
          Si tienes dudas sobre la plataforma, un problema técnico o quieres conocer
          mejor alcurro antes de contratar, estamos aquí.
        </p>

        <div className="contact-cards">
          <div className="contact-card">
            <div className="contact-card__icon">
              <span className="material-symbols-outlined">mail</span>
            </div>
            <h3>Email general</h3>
            <p>Para consultas comerciales o cualquier pregunta.</p>
            <a href="mailto:hola@alcurro.es" className="btn btn-primary">hola@alcurro.es</a>
          </div>

          <div className="contact-card">
            <div className="contact-card__icon">
              <span className="material-symbols-outlined">support_agent</span>
            </div>
            <h3>Soporte técnico</h3>
            <p>
              El soporte a clientes activos se gestiona <strong>exclusivamente por tickets</strong>.
              Accede desde tu panel de administración → Soporte.
            </p>
            <Link to="/acceso" className="btn">Acceder al panel</Link>
          </div>

          <div className="contact-card">
            <div className="contact-card__icon">
              <span className="material-symbols-outlined">privacy_tip</span>
            </div>
            <h3>Privacidad y RGPD</h3>
            <p>Para ejercer tus derechos de acceso, rectificación o supresión de datos.</p>
            <a href="mailto:privacidad@alcurro.es" className="btn">privacidad@alcurro.es</a>
          </div>
        </div>

        <div className="contact-notice">
          <span className="material-symbols-outlined">info</span>
          <p>
            <strong>Tiempos de respuesta:</strong> respondemos en un plazo máximo de 2 días
            hábiles para soporte técnico y 24 horas para incidencias críticas de producción.
            Los clientes con plan anual tienen prioridad de atención.
          </p>
        </div>
      </div>
    </div>
  );
}
