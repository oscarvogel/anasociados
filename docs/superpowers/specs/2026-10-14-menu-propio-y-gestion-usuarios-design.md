# Menú propio y gestión unificada de usuarios

## Objetivo

Ordenar la navegación del portal AN & Asociados para que refleje las tareas del
sistema y no el catálogo técnico de modelos registrados en Django Admin. El
Tablero existente se conserva. Las siguientes pantallas que se irán ajustando
son Alertas WhatsApp, Hallazgos y, después, la gestión de Usuarios.

La gestión de usuarios debe dejar de exigir que el operador salte entre varias
tablas de Django Admin para habilitar una cuenta y configurar sus relaciones.
El flujo propuesto reúne cuenta, empresa, áreas y WhatsApp en la interfaz propia
del portal.

## Contexto actual

- El sidebar vive en `templates/includes/sidebar.html` y combina enlaces propios
  con `admin_get_menu`, que genera grupos desde aplicaciones y modelos del
  administrador.
- Ese menú automático trunca nombres largos y muestra opciones técnicas junto
  a las pantallas operativas.
- Las pantallas de trabajo de Hallazgos y Alertas WhatsApp ya existen, igual que
  las pantallas de Móviles e Informes. El Tablero también existe y se conserva.
- `django.contrib.auth.models.User` contiene la cuenta y su estado `is_active`.
- `usuarios.Profile` relaciona una cuenta con un único `syh.Cliente`. La tabla
  de perfiles es preexistente y el modelo está marcado `managed = False`.
- `usuarios.AreasProfile` permite varias áreas por usuario y almacena un
  `telefono_whatsapp` por asignación.
- `syh.Cliente` y `syh.Area` corresponden a tablas preexistentes gestionadas
  fuera de las migraciones de Django (`managed = False`). Cada área pertenece a
  un cliente.
- Hay una especificación previa de rediseño visual que conserva Django Admin
  como interfaz administrativa. Esta especificación define una etapa distinta:
  desplazar gradualmente hacia pantallas propias los flujos operativos que el
  usuario ajuste, sin retirar el administrador como herramienta de respaldo.

## Alcance

### Incluido

- Reemplazar el menú generado por modelos de Django Admin por una navegación
  propia, declarada en configuración del proyecto y renderizada por el sidebar.
- Ordenar las funciones existentes bajo grupos claros y enlaces con etiquetas
  completas.
- Agregar un buscador que filtre grupos y enlaces del menú.
- Mantener Tablero y las rutas existentes de las pantallas incluidas en la
  navegación.
- Reunir la gestión de cuenta, empresa, áreas y WhatsApp por área en una sola
  experiencia de Usuarios.
- Permitir activar y desactivar cuentas desde la gestión propia de Usuarios.
- Mantener `/admin/` como acceso administrativo de transición para las cuentas
  que ya estén autorizadas por Django, pero no incluir el catálogo de modelos
  de Admin en el menú ordinario.

### Excluido

- Eliminar Django Admin, retirar su ruta o cambiar la política existente de
  autenticación/autorización de esa herramienta.
- Cambiar los permisos de negocio de las pantallas actuales o considerar la
  visibilidad del menú como un control de seguridad.
- Cambiar rutas, APIs, lógica de Hallazgos, Alertas WhatsApp, Móviles o Informes.
- Cambiar el esquema de las tablas existentes de usuarios, perfiles, clientes o
  áreas, o crear migraciones para esos modelos en esta etapa.
- Rediseñar el contenido del Tablero.

## Estructura inicial de navegación

La navegación es una jerarquía propia del portal. Los siguientes nombres son
etiquetas de interfaz; los destinos actuales se conservan.

1. **Tablero** — enlace directo a la pantalla actual.
2. **Seguridad e Higiene**
   - Hallazgos — enlace directo a la pantalla de trabajo existente.
3. **Alertas WhatsApp** — enlace directo al flujo existente; visible según la
   restricción actual de superusuario.
4. **Usuarios**
   - Gestión de usuarios — nueva experiencia consolidada, solo para
     superusuarios.
   - Informes de accesos — enlace actual, visible solo para superusuarios.
5. **Móviles** — agrupa las pantallas actuales de móviles, personal y
   vencimientos según sus permisos actuales.
6. **Informes** — agrupa los informes de velocidad, resumen mensual, consumo de
   combustible y gastos que actualmente están bajo Informes.

El orden y los grupos podrán ampliarse al migrar más flujos, pero ninguna opción
se incorporará automáticamente por registrar un modelo en Django Admin. Las
etiquetas de las aplicaciones y pantallas se mostrarán completas, sin
truncamiento artificial.

## Fuente y comportamiento del menú

- Declarar la navegación en un módulo propio del proyecto (propuesta:
  `core_an/navigation.py`) como datos explícitos: grupo, etiqueta, icono,
  destino y condición de acceso.
- Pasar al template solo las entradas aplicables al usuario actual. La
  condición del menú mejora la navegación, pero cada vista seguirá verificando
  autorización en servidor.
- Quitar `admin_get_menu` del sidebar; no depender de modelos, permisos de
  modelos o etiquetas de Admin para construir la navegación operativa.
- Añadir un campo accesible con etiqueta **Buscar en menú**. Al escribir,
  filtra grupos y enlaces por sus etiquetas; si coincide un enlace, su grupo
  permanece visible. Si no hay coincidencias, mostrar un mensaje claro. El
  filtrado no cambia rutas ni permisos.
- Los grupos mantienen submenús expandibles y resaltado de la ruta activa.
- En escritorio y móvil, el campo de búsqueda y sus resultados deben seguir
  siendo operables con teclado y exponer correctamente sus etiquetas y estados.

## Gestión unificada de Usuarios

### Experiencia

- Una lista de usuarios permite buscar por nombre de usuario, nombre, apellido,
  email, empresa o área y muestra estado de cuenta, empresa y áreas asignadas.
- Crear o editar un usuario desde una pantalla con secciones relacionadas:
  datos de la cuenta, activación, empresa, áreas y teléfono WhatsApp de cada
  asignación.
- La selección de empresa limita las áreas seleccionables a las pertenecientes
  a esa empresa.
- Permitir varias áreas para un usuario y configurar el WhatsApp por cada
  asignación, respetando la estructura actual.
- Desactivar una cuenta mantiene sus datos y relaciones; no equivale a borrar
  el usuario.
- La gestión se restringe a superusuarios en esta primera etapa. La edición del
  propio perfil existente sigue siendo un flujo separado.

### Persistencia y validación

- Usar las tablas y relaciones actuales: `User`, `Profile` y `AreasProfile`.
- No crear ni modificar esquema en esta etapa. Las tablas de clientes, áreas y
  perfiles son preexistentes.
- Guardar la cuenta, el perfil y las asignaciones de área dentro de una única
  transacción para no dejar una cuenta a medio configurar si falla una parte.
- Validar que exista una única empresa para el perfil del usuario y que cada
  área asociada pertenezca a esa empresa.
- Normalizar y validar los teléfonos WhatsApp con la lógica de validación que
  ya usa el proyecto.
- En edición, reconciliar las asignaciones seleccionadas: actualizar las
  existentes, crear las nuevas y retirar las que el operador quitó del
  formulario. No borrar áreas ni clientes del catálogo.
- Las contraseñas se capturan y guardan mediante las APIs de autenticación de
  Django; nunca se presentan ni se almacenan en texto plano. El flujo de
  edición no requiere volver a introducir la contraseña si no se está
  cambiando.

## Permisos y transición

- La navegación mantiene las condiciones actuales para Alertas WhatsApp,
  Informes de accesos y pantallas de Móviles.
- La nueva administración de usuarios se permite solo a superusuarios y la
  vista aplica esa restricción en servidor.
- `/admin/` queda fuera del menú normal y sigue protegido por el mecanismo de
  autorización actual de Django.
- Las pantallas propias reemplazan gradualmente el uso operativo de Admin; el
  acceso de respaldo no se elimina como parte de esta iniciativa.

## Entrega por etapas

1. Introducir el menú propio y el buscador; retirar el menú automático de
   modelos. Conservar destinos y condiciones actuales.
2. Mantener el Tablero y ajustar primero Alertas WhatsApp y Hallazgos como
   pantallas propias de trabajo.
3. Incorporar Gestión de usuarios con cuenta, empresa, áreas y WhatsApp en un
   solo flujo.
4. Seguir agrupando o sustituyendo otras pantallas conforme se trabajen Móviles
   e Informes, sin añadir opciones de Admin automáticamente.

Cada etapa debe poder desplegarse sin esperar la migración de los módulos
restantes.

## Criterios de aceptación

- El sidebar ya no enumera aplicaciones o modelos registrados en Django Admin.
- El Tablero conserva su destino y contenido.
- Las pantallas operativas actuales aparecen agrupadas con nombres completos y
  sus rutas existentes.
- El buscador encuentra etiquetas de grupos y enlaces, conserva visible el
  grupo de un resultado y presenta un estado vacío comprensible.
- Las condiciones de visibilidad actuales siguen vigentes y las vistas
  sensibles conservan validación de permisos en servidor.
- Un superusuario puede crear y editar una cuenta, activar/desactivar,
  seleccionar una empresa, asociar varias áreas válidas y configurar el
  WhatsApp de cada asignación desde un mismo flujo.
- No se puede guardar un área que pertenezca a una empresa distinta de la
  asignada al perfil.
- Una falla al guardar el perfil o las áreas no deja cambios parciales en la
  cuenta.
- El usuario común continúa pudiendo editar su propio perfil según el flujo
  actual.
- Django Admin sigue disponible para sus usuarios autorizados y ya no determina
  los enlaces del menú ordinario.

## Verificación prevista

- Recorrer el menú y su búsqueda con una cuenta superusuario y una cuenta
  estándar, verificando grupos, estados activos y accesos ocultos.
- Usar navegación por teclado para enfocar y filtrar el menú en escritorio y
  móvil.
- Probar alta/edición de usuario con una, varias y ninguna área; cambiar
  empresa; activar/desactivar; agregar/quitar asignaciones; validar WhatsApp y
  errores de persistencia.
- Confirmar en base de datos que cada perfil tiene una empresa y que todas las
  áreas de sus asignaciones pertenecen a ella.
- Confirmar que no cambian rutas ni autorización de las pantallas existentes,
  y que `/admin/` continúa respondiendo bajo sus reglas actuales.

## Decisiones pendientes para el plan

- Definir si la lista consolidada muestra todos los usuarios o permite filtros
  iniciales por estado y empresa; recomendación: búsqueda y filtros por estado
  y empresa.
- Determinar un flujo seguro de asignación inicial o restablecimiento de
  contraseña, evitando exponer contraseñas existentes.
- Cerrar el orden de los submenús de Móviles e Informes con el usuario durante
  la implementación, manteniendo todos los destinos actuales.
