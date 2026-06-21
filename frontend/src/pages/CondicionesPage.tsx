import { Link } from "react-router-dom";

export default function CondicionesPage() {
  return (
    <div className="legal-static">
      <div className="landing-container legal-static__inner">
        <Link to="/" className="legal-static__back">← Volver al inicio</Link>
        <h1>Condiciones del Servicio y del Producto</h1>
        <p className="legal-static__updated">Última actualización: junio 2025</p>

        <h2>1. Objeto</h2>
        <p>
          Las presentes Condiciones regulan la contratación y el uso de <strong>alcurro</strong>,
          una plataforma SaaS de gestión de recursos humanos (control horario, fichajes,
          permisos, turnos, documentación laboral y comunicación por WhatsApp), en adelante
          «el Servicio». La contratación o el uso del Servicio implica la aceptación plena y
          sin reservas de estas Condiciones, junto con el <Link to="/aviso-legal">Aviso Legal</Link> y
          la <Link to="/privacidad">Política de Privacidad</Link>.
        </p>

        <h2>2. Descripción del producto</h2>
        <p>
          El Servicio se presta en modalidad de software como servicio (SaaS), accesible a
          través de navegador web y de la integración con WhatsApp. Las funcionalidades
          disponibles dependen del plan contratado y pueden evolucionar con el tiempo. alcurro
          podrá añadir, modificar o retirar funcionalidades para mejorar el producto, sin que
          ello suponga merma sustancial de las prestaciones esenciales del plan contratado.
        </p>

        <h2>3. Registro y cuenta</h2>
        <p>
          Para utilizar el Servicio es necesario crear una cuenta facilitando datos veraces,
          completos y actualizados. El titular de la cuenta es responsable de la
          confidencialidad de sus credenciales y de toda actividad realizada bajo las mismas,
          así como de la gestión de los usuarios y permisos que cree dentro de su organización.
          El uso del Servicio está reservado a personas mayores de edad con capacidad legal
          para contratar en nombre de la empresa que representan.
        </p>

        <h2>4. Planes, precios y facturación</h2>
        <p>
          El Servicio se ofrece mediante suscripción de pago recurrente, con ciclo de
          facturación mensual o anual según el plan elegido. Los precios aplicables son los
          publicados en la página de tarifas en el momento de la contratación e incluyen los
          impuestos indirectos que correspondan conforme a la normativa vigente.
        </p>
        <p>
          La facturación se realiza a nivel de cuenta. La suscripción se renueva
          automáticamente por períodos sucesivos iguales al contratado, salvo cancelación
          previa. alcurro podrá actualizar los precios, comunicándolo con antelación
          razonable; los nuevos precios se aplicarán a partir de la siguiente renovación.
        </p>

        <h2>5. Procesamiento de pagos</h2>
        <p>
          Los pagos se gestionan a través de proveedores de pago externos que actúan como
          Merchant of Record y son responsables del cobro, la emisión de recibos y la gestión
          fiscal de la transacción. alcurro no almacena los datos completos de las tarjetas u
          otros medios de pago. El impago o el rechazo del cargo podrá conllevar la suspensión
          del acceso al Servicio tras los intentos de cobro y avisos previstos.
        </p>

        <h2>6. Período de prueba y cancelación</h2>
        <p>
          Cuando se ofrezca, el período de prueba permite evaluar el Servicio en las
          condiciones que se indiquen en cada caso. El cliente puede cancelar su suscripción
          en cualquier momento desde el portal de cliente o el panel de la cuenta; la
          cancelación surte efecto al final del período ya facturado, manteniéndose el acceso
          hasta esa fecha. No se realizan reembolsos por períodos ya iniciados, salvo
          obligación legal o decisión expresa de alcurro.
        </p>

        <h2>7. Disponibilidad y soporte</h2>
        <p>
          alcurro pondrá medios razonables para garantizar la disponibilidad del Servicio, sin
          que ello suponga un compromiso de funcionamiento ininterrumpido. Podrán realizarse
          tareas de mantenimiento, actualización o corrección que afecten temporalmente al
          acceso, procurando minimizar su impacto. El soporte se presta por los canales
          publicados en la web.
        </p>

        <h2>8. Uso aceptable</h2>
        <p>
          El cliente se compromete a hacer un uso lícito del Servicio, respetando la
          legislación vigente y los derechos de terceros. Queda prohibido, entre otros: el
          acceso no autorizado, la realización de actividades que comprometan la seguridad o
          el rendimiento de la plataforma, el uso para fines fraudulentos o ilícitos, y la
          reventa o cesión del Servicio sin autorización. alcurro podrá suspender o cancelar
          el acceso ante incumplimientos, sin derecho a indemnización.
        </p>

        <h2>9. Datos del cliente y protección de datos</h2>
        <p>
          El cliente es responsable del tratamiento de los datos personales que introduzca en
          la plataforma (empleados, registros horarios, etc.), actuando alcurro como encargado
          del tratamiento conforme al RGPD y a la <Link to="/privacidad">Política de
          Privacidad</Link>. El cliente garantiza disponer de la base legal necesaria para el
          tratamiento de dichos datos. Los registros de fichaje se conservan conforme a la
          normativa laboral española aplicable.
        </p>

        <h2>10. Propiedad intelectual</h2>
        <p>
          El Servicio, su software, diseño, marcas y contenidos son propiedad de alcurro o de
          sus licenciantes. La contratación otorga al cliente un derecho de uso personal, no
          exclusivo e intransferible durante la vigencia de la suscripción. Los datos
          introducidos por el cliente siguen siendo de su titularidad.
        </p>

        <h2>11. Limitación de responsabilidad</h2>
        <p>
          El Servicio se presta «tal cual». alcurro no será responsable de los daños derivados
          del uso incorrecto del Servicio, de errores en los datos introducidos por el
          cliente, de interrupciones por causas ajenas a su control o de la pérdida de datos
          cuando no se hayan adoptado las medidas de respaldo oportunas. En todo caso, la
          responsabilidad de alcurro quedará limitada al importe abonado por el cliente en los
          doce meses anteriores al hecho que la origine.
        </p>

        <h2>12. Modificaciones</h2>
        <p>
          alcurro se reserva el derecho a modificar las presentes Condiciones. Las
          modificaciones serán efectivas desde su publicación en el sitio web. El uso
          continuado del Servicio tras la publicación de cambios implica su aceptación.
        </p>

        <h2>13. Legislación aplicable y jurisdicción</h2>
        <p>
          Las presentes Condiciones se rigen por la legislación española. Para la resolución
          de cualquier controversia, las partes se someten a los Juzgados y Tribunales que
          correspondan conforme a la normativa aplicable.
        </p>

        <div className="legal-static__footer-links">
          <Link to="/aviso-legal">Aviso Legal</Link>
          <Link to="/privacidad">Política de Privacidad</Link>
          <Link to="/cookies">Política de Cookies</Link>
        </div>
      </div>
    </div>
  );
}
