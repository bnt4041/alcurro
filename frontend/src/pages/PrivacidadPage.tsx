import { Link } from "react-router-dom";

export default function PrivacidadPage() {
  return (
    <div className="legal-static">
      <div className="landing-container legal-static__inner">
        <Link to="/" className="legal-static__back">← Volver al inicio</Link>
        <h1>Política de Privacidad</h1>
        <p className="legal-static__updated">Última actualización: junio 2025</p>

        <h2>1. Responsable del tratamiento</h2>
        <p>
          El responsable del tratamiento de los datos personales recogidos a través de
          este sitio web y de la plataforma alcurro es la propia empresa titular del servicio.
          Puede contactar con nosotros en: <a href="mailto:privacidad@alcurro.es">privacidad@alcurro.es</a>
        </p>

        <h2>2. Datos que recogemos</h2>
        <p>Tratamos las siguientes categorías de datos:</p>
        <ul>
          <li><strong>Datos de registro y cuenta:</strong> nombre, apellidos, correo electrónico, nombre de empresa y datos de facturación.</li>
          <li><strong>Datos de empleados (introducidos por el cliente):</strong> nombre, número de teléfono, datos de jornada laboral, geolocalización (si el cliente activa esta función), documentación laboral.</li>
          <li><strong>Datos de uso:</strong> logs de acceso, dirección IP, tipo de navegador, páginas visitadas y funciones utilizadas en la plataforma.</li>
          <li><strong>Datos de pago:</strong> gestionados íntegramente por Stripe. alcurro no almacena datos de tarjeta de crédito.</li>
          <li><strong>Comunicaciones por WhatsApp:</strong> mensajes intercambiados con el bot, procesados de forma local en la infraestructura del cliente.</li>
        </ul>

        <h2>3. Finalidad y base legal del tratamiento</h2>
        <table className="legal-table">
          <thead>
            <tr><th>Finalidad</th><th>Base legal</th></tr>
          </thead>
          <tbody>
            <tr><td>Prestación del servicio contratado</td><td>Ejecución de contrato (art. 6.1.b RGPD)</td></tr>
            <tr><td>Facturación y gestión de pagos</td><td>Obligación legal (art. 6.1.c RGPD)</td></tr>
            <tr><td>Comunicaciones sobre el servicio</td><td>Interés legítimo (art. 6.1.f RGPD)</td></tr>
            <tr><td>Registro horario de empleados</td><td>Obligación legal RDL 8/2019 (art. 6.1.c RGPD)</td></tr>
            <tr><td>Mejora del servicio y análisis de uso</td><td>Interés legítimo (art. 6.1.f RGPD)</td></tr>
          </tbody>
        </table>

        <h2>4. Destinatarios de los datos</h2>
        <p>
          No cedemos tus datos a terceros salvo obligación legal. Contamos con los
          siguientes encargados del tratamiento, con los que hemos suscrito los acuerdos
          correspondientes:
        </p>
        <ul>
          <li><strong>Stripe, Inc.</strong> — procesamiento de pagos (EEUU, con garantías adecuadas SCCs)</li>
          <li><strong>Proveedor de hosting/VPS</strong> — alojamiento de la plataforma en servidores en la UE</li>
          <li><strong>Meta Platforms (WhatsApp)</strong> — infraestructura de mensajería</li>
        </ul>
        <p>
          El modelo de IA (Ollama) se ejecuta localmente en el servidor del cliente.
          alcurro <strong>no envía datos de conversaciones a servicios de IA en la nube</strong>.
        </p>

        <h2>5. Transferencias internacionales</h2>
        <p>
          Los datos de pago se transfieren a Stripe, Inc. (EEUU) bajo Cláusulas Contractuales
          Estándar aprobadas por la Comisión Europea. Los datos de empleados se alojan en
          servidores dentro del Espacio Económico Europeo.
        </p>

        <h2>6. Conservación de datos</h2>
        <p>
          Conservamos los datos durante la vigencia del contrato y, posteriormente, durante
          los plazos legales aplicables (4 años para datos fiscales, 6 años para registros
          de jornada conforme al ET). Pasados estos plazos, los datos son eliminados o
          anonimizados.
        </p>

        <h2>7. Tus derechos</h2>
        <p>
          Tienes derecho a acceder, rectificar, suprimir, oponerte al tratamiento, solicitar
          la portabilidad y la limitación del tratamiento de tus datos. Puedes ejercer estos
          derechos enviando un correo a{" "}
          <a href="mailto:privacidad@alcurro.es">privacidad@alcurro.es</a> con copia de tu
          documento de identidad.
        </p>
        <p>
          Tienes también derecho a presentar una reclamación ante la Agencia Española de
          Protección de Datos (<a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">aepd.es</a>).
        </p>

        <h2>8. Seguridad</h2>
        <p>
          Aplicamos medidas técnicas y organizativas adecuadas para proteger tus datos:
          cifrado en tránsito (TLS), control de acceso por roles, copias de seguridad
          periódicas y auditoría de accesos. En caso de brecha de seguridad que afecte
          a tus derechos, lo notificaremos en los plazos legales.
        </p>

        <div className="legal-static__footer-links">
          <Link to="/aviso-legal">Aviso Legal</Link>
          <Link to="/condiciones">Condiciones del Servicio</Link>
          <Link to="/cookies">Política de Cookies</Link>
        </div>
      </div>
    </div>
  );
}
