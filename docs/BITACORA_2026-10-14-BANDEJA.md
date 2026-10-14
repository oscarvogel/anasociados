# Bitácora — 14/10/2026 (segunda tanda)

## Qué se hizo

Dejar de usar el admin de Django como frontend de hallazgos, y cerrar el
circuito de evidencia con un paso que faltaba: que el administrador **vea la
foto y decida**.

Commits: `f31f3b4` (bandeja), `87bc185` y uno más (fixes de JS).

## Por qué el admin no servía

No era "incómodo" en abstracto. Eran tres cosas concretas:

1. **La búsqueda no tenía la empresa.** En `syh/admin.py`,
   `MovimientosAdmin.search_fields = ('id', 'area__detalle', 'periodo', 'hallazgo')`.
   El nombre de la empresa estaba en `list_display` pero **no** en
   `search_fields`. Con 16 clientes y 1313 hallazgos, buscar por empresa —lo
   primero que se hace— no encontraba nada.
2. **Las fotos estaban escondidas.** Solo se veían entrando a cada hallazgo por
   el inline, de a una. La lista aparte (`EvidenciaListAdmin`) está
   restringida a superusuario (`has_module_permission`, `syh/admin.py:108`).
3. **No había forma de saber qué había que revisar.** El listado no mostraba
   si un hallazgo tenía evidencia pendiente.

Y el hueco de fondo: **no existía el concepto de "revisar"**. La acción
"Cerrar los hallazgos seleccionados" cerraba todo hallazgo que *tuviera una
foto*, sin mirarla. Era exactamente el atajo que el flujo de WhatsApp vino a
evitar.

## La bandeja

`/utiles/evidencias-revision/#<token>` — el token va en el fragmento, igual
que el link del responsable, y la página lo pasa como `Bearer`.

Cuando el responsable sube evidencia, el aviso al administrador ahora trae el
link. En el celular: la foto grande (tocala para verla completa), el hallazgo,
el vencimiento, quién la subió, y dos botones.

- **Aceptar** → el hallazgo queda `Cumplido` con `fecha_realizado = hoy`. Un
  toque y el circuito cierra.
- **Rechazar** → **exige motivo**, porque el motivo es lo que recibe el
  responsable. El hallazgo no se toca (sigue abierto) y se le manda WhatsApp
  con el motivo para que resubita.

### El link del administrador es un token DISTINTO

No es una comodidad, es una decisión de seguridad. El enlace del responsable y
el del administrador son del mismo modelo y mismo alcance (empresa + área), y
se separan con `puede_revisar`. Si fueran el mismo, que se filtrara el link de
subida permitiría **subir evidencia y cerrar hallazgos** con un solo token.

El test que cubre esto se verificó que **muerde**: sacando el chequeo de
`puede_revisar`, `test_el_enlace_del_responsable_no_abre_la_bandeja` falla.

### La foto no se sirve desde `MEDIA_URL`

Un `<img src>` no puede mandar headers, y el token tiene que viajar solo en
`Authorization` (si fuera un query param, quedaría en los logs y en el
`Referer`). Por eso la foto se pide con `fetch`, se convierte a blob y se pinta
con una object URL. Hay una vista `evidencias_revision_imagen` que sí exige el
token.

## Cambios en el admin

- `search_fields` ahora incluye `cliente__nombre` y `responsable`.
- La lista de evidencias muestra el estado de revisión y se puede filtrar por
  él, y se puede buscar por empresa.
- **No se pueden agregar evidencias a mano** (`has_add_permission = False`):
  acreditar un hallazgo desde el panel, sin que nadie lo subiera, era un hueco.
- **Se sacó la acción "Cerrar los hallazgos seleccionados".** Dejar disponible
  un atajo que cierra sin mirar la foto contradice todo el flujo. Queda el
  comentario en el código explicando a dónde fue.

## Migraciones

- `syh.0033` — `Evidencia` gana `estado`, `revisado_por`, `revisado_at`,
  `motivo_rechazo`.
- `utiles.0005` — `EnlacePublicoHallazgos.puede_revisar`.

Backup antes de aplicarlas en `/root/backups-pre-bandeja/20261014-141010/`.

## Bugs que aparecieron en esta tanda

### 1. Dos `ReferenceError` en el JavaScript del template

`labela` en vez de `etiqueta`, y `tarjeta` usándose dentro de `decidir()` sin
recibirla (era local de `construirTarjeta()`). Los dos rompían la página y los
dos **pasaron los tests**: los tests verifican que el template renderice y el
texto del modal, no que el JavaScript corra.

Salieron recién al abrir la página de verdad en el navegador.

**Conclusión de método:** para el frontend de este proyecto, la verificación es
abrir la página y mirar la consola. No hay atajo. El `ReferenceError` además
era silencioso a medias: en el segundo caso el POST **sí se había hecho**
(falló solo el refresco de la pantalla), así que la base mostraba el rechazo
aplicado mientras la pantalla decía error.

### 2. Con `DEBUG=False`, Django cachea los templates

Después del `git pull`, el servidor seguía sirviendo la versión vieja del
template aunque el archivo en disco ya estuviera arreglado. Hay que
**reiniciar `an`** para que los workers de gunicorn vuelvan a leer.

Va a pasar en cada deploy que toque un template.

### 3. El área de prueba no tiene teléfono de responsable

El rechazo de la evidencia #7 **no pudo avisar por WhatsApp**: el área
Sistemas de Vogel Oscar (`bb7f55df`) no tiene ningún `AreasProfile` con
`telefono_whatsapp`. Es la misma razón por la que `subido_por` viene vacío.
El código lo maneja bien (devuelve `ok: False` con un detalle claro, y el
rechazo queda registrado igual), pero el aviso no sale.

Se verificó la ruta de envío real contra un área que **sí** tiene teléfono
(`ab1d0b73`): `{'ok': True, 'enviados': ['5493757677124'], 'errores': []}`.

## Verificación

Suite: **29 tests en verde** (13 nuevos de la bandeja).

Contra producción, con navegador real:

1. La bandeja carga, con las 2 evidencias y sus fotos (una del celular, una de
   prueba).
2. **Rechazar**: `POST` 200, evidencia #7 → `rechazada` con motivo,
   `revisado_at` puesto, y el hallazgo `de1650ae` **sigue `Gestión en Curso`**.
3. **Aceptar**: evidencia #6 → `aceptada`, `revisado_por='Oscar Vogel
   (prueba)'`, y el hallazgo `bddc1570` pasó a `Cumplido` con
   `fecha_realizado=2026-10-14` (hoy).
4. La bandeja queda vacía con "Nada para revisar".
5. El mensaje del administrador incluye el link de revisión (verificado
   interceptando el envío).

Después de verificar se devolvió el área a como estaba, para que el flujo se
pueda probar de nuevo.

## Pendientes

- **Cargar el teléfono del responsable en el área Sistemas** del cliente de
  prueba. Sin eso no hay `subido_por` ni aviso de rechazo.
- **El link de revisión es por empresa/área, no por administrador.** El campo
  `revisado_por` queda "sin identificar" salvo que se complete el nombre en la
  página (se recuerda en el dispositivo). Un link por contacto daría
  atribución real sin pedir nada.
- **La vista de hallazgos sigue siendo la de siempre**
  (`syh:visualizar_movimientos`, "Informes - Hallazgos"). El admin ya no es el
  lugar de trabajo para revisar evidencia, pero la vista de hallazgos **tampoco
  se mejoró**: sigue con 10 por página y sin búsqueda por texto. Es el segundo
  paso, ya que el usuario priorizó la bandeja.
- **`revisado_por` y `revisado_at` son readonly en el admin**, pero no hay
  forma de corregir una decisión equivocada desde la interfaz: hay que entrar
  por shell. Si va a pasar, va a hacer falta una forma de revertir.
- **Pendientes de la tanda anterior**, siguen igual:
  - `Movimientos.id` con default compartido (`syh/models.py:138`).
  - `syh_evidencia.movimiento` varchar(10) vs varchar(20) en base nueva.
  - Números de WhatsApp de prueba (`5493757677124`, `5493743667526`).
  - El VPS reinicia solo todos los días a las 02:00.
  - Tests de `home`, `moviles` y `usuarios` son stubs.
  - `print(resultados)` en `syh/models.py:478`.