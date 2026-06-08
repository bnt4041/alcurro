import { Link } from "react-router-dom";

export default function AvisoLegalPage() {
  return (
    <div className="legal-static">
      <div className="landing-container legal-static__inner">
        <Link to="/" className="legal-static__back">← Volver al inicio</Link>
        <h1>Aviso Legal</h1>
        <p className="legal-static__updated">Última actualización: junio 2025</p>

        <h2>1. Titular del sitio web</h2>
        <p>
          En cumplimiento de la Ley 34/2002, de 11 de julio, de Servicios de la Sociedad
          de la Información y Comercio Electrónico (LSSI-CE), se informa de que el titular
          de este sitio web es <strong>alcurro</strong>, en adelante «la empresa».
        </p>
        <p>
          Correo electrónico de contacto: <a href="mailto:hola@alcurro.es">hola@alcurro.es</a>
        </p>

        <h2>2. Objeto y ámbito de aplicación</h2>
        <p>
          El presente Aviso Legal regula el acceso y uso del sitio web <strong>alcurro.es</strong>,
          así como de la plataforma SaaS de gestión de recursos humanos accesible a través
          del mismo. El acceso al sitio implica la aceptación plena de las presentes condiciones.
        </p>

        <h2>3. Propiedad intelectual e industrial</h2>
        <p>
          Todos los contenidos del sitio web —textos, imágenes, diseño, código fuente,
          logotipos y denominaciones— son propiedad de alcurro o de sus licenciantes y están
          protegidos por la legislación española e internacional sobre propiedad intelectual e
          industrial. Queda prohibida su reproducción, distribución o comunicación pública sin
          autorización expresa.
        </p>

        <h2>4. Condiciones de uso del servicio</h2>
        <p>
          El acceso a la plataforma está restringido a usuarios registrados y autorizados.
          El usuario se compromete a hacer un uso lícito del servicio, respetando la
          legislación vigente y los derechos de terceros. Queda expresamente prohibido
          el uso del servicio para actividades ilícitas o contrarias a las presentes condiciones.
        </p>
        <p>
          La empresa se reserva el derecho a suspender o cancelar el acceso al servicio de
          aquellos usuarios que incumplan estas condiciones, sin derecho a indemnización alguna.
        </p>

        <h2>5. Limitación de responsabilidad</h2>
        <p>
          La empresa no se hace responsable de los daños o perjuicios derivados del uso
          incorrecto del servicio, de errores en los datos introducidos por el usuario, de
          interrupciones del servicio por causas ajenas a su control (fuerza mayor, fallos
          de terceros proveedores, etc.) ni de la pérdida de datos cuando el usuario no
          haya realizado las copias de seguridad oportunas.
        </p>
        <p>
          Los contenidos del sitio web tienen carácter meramente informativo y no constituyen
          asesoramiento jurídico, laboral o de ningún otro tipo.
        </p>

        <h2>6. Modificaciones</h2>
        <p>
          alcurro se reserva el derecho a modificar en cualquier momento el presente Aviso
          Legal, la Política de Privacidad y la Política de Cookies. Las modificaciones
          serán efectivas desde su publicación en el sitio web. El uso continuado del
          servicio tras la publicación de cambios implica su aceptación.
        </p>

        <h2>7. Legislación aplicable y jurisdicción</h2>
        <p>
          Las presentes condiciones se rigen por la legislación española. Para la resolución
          de cualquier controversia derivada del uso del sitio web o del servicio, las partes
          se someten, con renuncia expresa a cualquier otro fuero, a los Juzgados y Tribunales
          de España.
        </p>

        <div className="legal-static__footer-links">
          <Link to="/privacidad">Política de Privacidad</Link>
          <Link to="/cookies">Política de Cookies</Link>
        </div>
      </div>
    </div>
  );
}
