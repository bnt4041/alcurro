# Alcurro — Guía de producto

**Alcurro** es una plataforma de gestión de personal y control horario pensada para empresas en España. Combina un **panel web** para responsables y administración con un **asistente de WhatsApp** para que los empleados hagan casi todo desde el móvil, sin apps ni instalaciones.

Su objetivo: cumplir la normativa española de registro de jornada de forma sencilla, y de paso resolver vacaciones, documentos, firmas y comunicación interna en un único sitio.

---

## En una frase

> Tus empleados fichan y gestionan sus cosas por WhatsApp; tú lo controlas todo desde un panel web, con validez legal y sin papeles.

---

## Índice de funcionalidades

1. [Control horario (fichajes)](#1-control-horario-fichajes)
2. [Paradas y descansos](#2-paradas-y-descansos)
3. [Asistente de WhatsApp (Curro)](#3-asistente-de-whatsapp-curro)
4. [Vacaciones y permisos](#4-vacaciones-y-permisos)
5. [Incidencias](#5-incidencias)
6. [Turnos y horarios](#6-turnos-y-horarios)
7. [Proyectos y obras](#7-proyectos-y-obras)
8. [Informes](#8-informes)
9. [Documentos](#9-documentos)
10. [Firmas electrónicas](#10-firmas-electrónicas)
11. [Comunicaciones](#11-comunicaciones)
12. [Textos legales](#12-textos-legales)
13. [Empleados y organización](#13-empleados-y-organización)
14. [Roles y permisos](#14-roles-y-permisos)
15. [Cuenta, planes y facturación](#15-cuenta-planes-y-facturación)
16. [Soporte](#16-soporte)
17. [Integraciones (API y webhooks)](#17-integraciones-api-y-webhooks)

---

## 1. Control horario (fichajes)

El corazón de Alcurro. Cada empleado registra su **entrada y salida** de la jornada.

**Qué cubre:**
- Fichaje desde **WhatsApp** (escribiendo "entro", "me voy"…) o desde el panel.
- **Registro inalterable**: una vez fichado, no se puede editar ni borrar, tal como exige la normativa española de registro de jornada. Cualquier corrección se hace mediante una *incidencia* (queda todo trazado).
- **Geolocalización**: cuando la empresa lo requiere, el empleado comparte su ubicación **en tiempo real** al fichar (no vale una ubicación estática o reenviada), garantizando que está realmente en el sitio.
- **Dirección legible**: la ubicación se traduce automáticamente a una dirección.
- Asociación opcional del fichaje a un **proyecto u obra**.
- Reglas configurables por empresa: si se exige ubicación, si se pide proyecto, resumen de jornada al salir, etc.

---

## 2. Paradas y descansos

Registro de las **pausas** dentro de la jornada (comida, café, descansos).

**Qué cubre:**
- Iniciar y finalizar pausas desde WhatsApp ("me voy a comer", "vuelvo").
- Quedan asociadas a la jornada abierta, para calcular el tiempo efectivo trabajado.
- Trazabilidad completa igual que los fichajes.

---

## 3. Asistente de WhatsApp (Curro)

El diferencial de Alcurro: un **asistente conversacional** por WhatsApp que entiende lenguaje natural (español coloquial de España). El empleado no necesita aprender comandos.

**Lo que puede hacer un empleado por WhatsApp:**
- Fichar entrada y salida.
- Iniciar y terminar pausas.
- Solicitar vacaciones y permisos ("quiero vacaciones del 1 al 5 de agosto").
- Consultar su saldo de vacaciones.
- Ver el resumen de su día (fichajes y pausas).
- Reportar una incidencia y justificarla.
- Confirmar la recepción de documentos y firmar.
- Aceptar textos legales.

**Además, para responsables:**
- Consultar las vacaciones **pendientes de aprobar**.
- Aprobar o rechazar vacaciones desde el propio chat.
- Ver incidencias abiertas y sin gestionar de su equipo.

**Y para administradores de cuenta:**
- Crear y modificar proyectos/obras conversando con el asistente.

Todo esto es **configurable**: desde el panel se decide qué acciones puede hacer cada tipo de usuario por WhatsApp.

---

## 4. Vacaciones y permisos

Gestión completa de ausencias.

**Qué cubre:**
- Solicitud de **vacaciones** (por WhatsApp o panel), con cálculo automático de días laborables.
- **Saldo de vacaciones** por empleado, con los días ya consumidos y en proceso.
- Solicitud de **permisos** y ausencias (médico, personal, etc.).
- **Aprobación o rechazo** por el responsable, con notificación automática al empleado.
- Distintos **tipos de permiso** configurables por la empresa.

---

## 5. Incidencias

Cualquier desviación sobre el fichaje normal se gestiona como una incidencia, con historial.

**Qué cubre:**
- **Incidencias automáticas**: la empresa puede activar reglas como "retraso en la entrada", "no fichó la entrada" o "jornada sin cerrar", que generan una incidencia sola.
- Aviso automático al empleado por WhatsApp para que **justifique** (con un enlace o respondiendo en el chat).
- **Incidencias manuales**: el empleado o el responsable pueden abrir una para corregir o explicar algo.
- Estados y **trazabilidad** (abierta, justificada, resuelta…), notas internas y adjuntos.
- Como los fichajes no se pueden tocar, las correcciones se canalizan aquí.

---

## 6. Turnos y horarios

Definición del horario esperado de cada empleado.

**Qué cubre:**
- Horario semanal (días y franjas), horas semanales.
- **Turnos complejos**: rotativos, partidos, ciclos, nocturnidad.
- Asignación masiva de horarios a varios empleados a la vez.
- Sirve de base para detectar retrasos y calcular desviaciones.

---

## 7. Proyectos y obras

Para empresas que trabajan por proyectos u obras (construcción, servicios, etc.).

**Qué cubre:**
- Alta de proyectos/obras con dirección y horas previstas.
- Al fichar, el empleado indica en qué proyecto está trabajando.
- Permite después medir horas dedicadas por proyecto.
- Los administradores pueden crearlos y modificarlos incluso por WhatsApp.

---

## 8. Informes

Visión de conjunto de la actividad para responsables y administración.

**Qué cubre:**
- Reportes de fichajes, horas trabajadas y paradas.
- Filtrado por empleado, periodo, empresa, etc.
- Exportación de datos para nóminas o auditoría.
- Registro accesible ante una inspección de trabajo.

---

## 9. Documentos

Entrega y control de documentación laboral.

**Qué cubre:**
- Envío de documentos a los empleados (por ejemplo, **nóminas**).
- **Acuse de recibo**: el empleado confirma que lo ha recibido.
- **Subida masiva** de documentos.
- Cada empleado tiene su carpeta de documentos accesible.

---

## 10. Firmas electrónicas

Firma de documentos con validez y trazabilidad, sin desplazamientos ni papel.

**Qué cubre:**
- Envío de un documento para firmar a uno o varios firmantes.
- **Doble autenticación por WhatsApp** (código OTP) antes de firmar.
- **Firma manuscrita** en el móvil y generación de un **PDF firmado + certificado** de la firma.
- Firmantes **externos** (no empleados): basta su nombre, teléfono y DNI.
- Estado de cada firmante y trazabilidad completa (enviado, autenticado, firmado).
- Posibilidad de cancelar o reenviar.

---

## 11. Comunicaciones

Envío de comunicados a la plantilla, con o sin firma.

**Qué cubre:**
- Enviar un **texto (y adjuntos opcionales)** a un grupo de empleados.
- **Audiencia flexible**: toda la empresa, o filtrando por departamentos, centros de trabajo, responsables (su equipo) o empleados concretos.
- Incluir **personas externas** (como en las firmas).
- Dos modos:
  - **Abierto**: simple envío por WhatsApp.
  - **Con firma**: el destinatario se autentica por WhatsApp y firma el comunicado, con trazabilidad completa (quién lo recibió, lo leyó y lo firmó).
- Se puede **cancelar** un comunicado o **añadir destinatarios** después.

---

## 12. Textos legales

Gestión de la aceptación de condiciones y políticas por parte de los empleados.

**Qué cubre:**
- Publicación de textos legales (condiciones, políticas internas, protección de datos…).
- El empleado los **acepta desde WhatsApp** mediante un enlace seguro.
- Se genera un **certificado de aceptación** y queda registrada la trazabilidad.
- Si hay documentos pendientes, se le recuerdan automáticamente al empleado antes de dejarle hacer otras acciones.

---

## 13. Empleados y organización

Estructura de la empresa y de su personal.

**Qué cubre:**
- Alta y gestión de **empleados** (datos, teléfono de WhatsApp, DNI, puesto, supervisor…).
- Estructura organizativa en varios niveles: **Empresa → Centro de trabajo → Departamento → Empleado**.
- **Multi-empresa**: una misma cuenta puede gestionar varias empresas.
- **Organigrama** visual.
- Importación masiva de empleados.

---

## 14. Roles y permisos

Control de quién puede ver y hacer qué.

**Qué cubre:**
- **Tipos de usuario**: Empleado, Responsable, Administrador de cuenta e Inspector de Trabajo.
- **Grupos de permisos**: plantillas reutilizables con permisos concretos (ver fichajes, aprobar vacaciones, gestionar documentos, etc.) asignables a los empleados.
- Opción **"También administrador de cuenta"**: un empleado normal puede tener además permisos de administrador (en el panel y por WhatsApp) sin dejar de ser empleado.
- **Inspector de Trabajo**: acceso de solo lectura pensado para inspecciones.
- Todo lo que se puede hacer por WhatsApp también se controla por rol.

---

## 15. Cuenta, planes y facturación

Administración de la suscripción de la cuenta.

**Qué cubre:**
- Suscripción **por cuenta** (no por empresa), con su titular de facturación.
- Gestión de **plan**, método de pago y **facturas** (a través de Paddle).
- Control de límite de usuarios según el plan.
- **Marca personalizada** de la cuenta (logo, colores) que se refleja en el panel y en las comunicaciones.
- Configuración del **WhatsApp** de la empresa para el asistente.

---

## 16. Soporte

Canal de ayuda con el equipo de Alcurro.

**Qué cubre:**
- Apertura de **tickets de soporte** desde el panel (o incluso por WhatsApp para administradores).
- Conversación, seguimiento del estado y notificaciones.

---

## 17. Integraciones (API y webhooks)

Para empresas que quieran conectar Alcurro con otros sistemas.

**Qué cubre:**
- **API** para consultar y crear datos (empleados, fichajes, etc.).
- **Webhooks** para recibir eventos.
- Zona de desarrollador con las claves y la documentación de los endpoints.

---

## Cómo encaja todo (flujo típico)

1. La empresa da de alta a sus empleados y define horarios, centros y proyectos.
2. Publica sus textos legales; los empleados los aceptan por WhatsApp.
3. Cada día, los empleados **fichan por WhatsApp** compartiendo su ubicación en tiempo real; hacen sus pausas.
4. Piden **vacaciones o permisos** por el chat; el responsable los **aprueba** también por WhatsApp.
5. Las **incidencias** (retrasos, olvidos) se detectan solas y se justifican en el móvil.
6. La empresa envía **nóminas y documentos**, recoge **firmas** y manda **comunicados** con trazabilidad.
7. Responsables y administración lo supervisan todo desde el **panel web**, con **informes** listos para nóminas o inspección.

---

## Puntos fuertes de Alcurro

- **Sin apps ni fricción**: los empleados usan WhatsApp, que ya tienen.
- **Cumplimiento legal** del registro de jornada en España, con registros inalterables y trazabilidad.
- **Anti-fraude en el fichaje**: exige ubicación en tiempo real (no reenviable).
- **Todo en uno**: fichaje, vacaciones, incidencias, documentos, firmas y comunicación interna.
- **Multi-empresa** y con permisos finos por rol.
- **Firmas y comunicados con validez** y doble autenticación por WhatsApp.
