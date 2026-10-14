# Bitácora — 14/10/2026 (tercera tanda)

## Qué se hizo

Dos cosas, en este orden:

1. **Enlace de revisión por administrador.** El enlace era uno solo por
   empresa/área y `revisado_por` quedaba siempre en "sin identificar".
2. **La pantalla de hallazgos, rehecha.**

Commits: `b939532` (enlace por contacto), `615bd16` + `cff5b42` (la vista que
se revirtió), `91833cf` (la vista nueva).

## 1. Enlace por contacto

Cada `ContactoNotificacion` con `recibe_evidencias` y activo recibe **su
propio** enlace. Se separates del del responsable por `puede_revisar`, y ahora
también por `contacto`.

- `EnlacePublicoHallazgos.contacto` (nullable: los enlaces del responsable y
  los de revisión anteriores no tienen dueño).
- El aviso al administrador se arma por contacto, cada uno con su link.
- Quien aprueba se toma **del enlace**, no del campo del formulario: mandar un
  nombre falso por POST no cambia la firma. Hay un test que lo comprueba
  mandando `revisor=MENTIRA` y esperando el nombre del contacto.
- La bandeja muestra "Revisando: Oscar Vogel" y oculta el campo de texto. Para
  los enlaces viejos sin dueño, el campo sigue disponible.

Verificado en producción: aceptar con el link de Oscar dejó
`revisado_por='Oscar Vogel'`.

## 2. La pantalla de hallazgos

**El intento anterior estaba mal y se revirtió** (`cff5b42`). Era una tabla
con casillas de filtro y botón "Aplicar filtro": el patrón del admin con mejor
buscador. No era "otra forma de visualización", era pintura nueva sobre lo
mismo. Quedó solo el arreglo del sidebar, que es un bug real y va aparte.

La pantalla ahora:

- **Arriba, cuatro contadores**: vencidos, vencen en 5 días, con evidencia por
  revisar, empresas con pendientes.
- **Una sección por empresa**, ordenada por urgencia: primero la que tiene
  vencidos, después la que tiene algo por revisar, después la que más vence
  pronto. Los empates los desempata el nombre.
- Cada sección lista sus hallazgos abiertos hasta 8, y después "y N más".
- El buscador busca en todo, **incluido lo ya cumplido**: si estás buscando
  algo puntual lo querás encontrar esté o no. Sin búsqueda, solo lo abierto.
- Las fotos se piden al click. Las de un celular pesan megabytes y la pantalla
  puede listar cientos.

## Lo que dicen los datos

En producción hay **482 hallazgos vencidos** y 532 abiertos en total, en 15
empresas. La más grande (Forestal Río Claro) tiene 187 vencidos de 221.

Eso no es un bug de la pantalla: es deuda histórica acumulada. La pantalla
ahora la hace visible, que antes estaba escondida atrás de 130 páginas de
tabla. Pero probablemente necesite una decisión: ¿es real o son hallazgos
viejos que nadie cerró y que en algún momento hay que dar por resueltos?

## Bugs que aparecieron

### 1. `{% url 'profile' %}` no existe — 500 para todo usuario no superusuario

El sidebar lo tenía dentro de `{% if request.user.is_authenticated and not
request.user.is_superuser %}`. No hay ninguna URL con ese nombre en el
proyecto, así que Django levantaba `NoReverseMatch` y la página entera daba 500
para cualquier usuario que no fuera superusuario. Apunta ahora a
`usuarios:update_user`, la única pantalla de perfil que existe.

**Y el arreglo inicial se rompió solo.** Escribí el comentario explicativo con
`{% url 'profile' %}` adentro. Los comentarios `{# ... #}` no aceptan
etiquetas de plantilla, y su regex **no cruza saltos de línea**: un comentario
de varias líneas con llaves y `%` hace que Django lo interprete como una
etiqueta real. Por eso el error seguía apareciendo después de "arreglarlo".

### 2. La columna Ubicación se veía siempre vacía

El campo `ubicacion` está comentado en el modelo `syh.Movimientos` aunque
exista en la tabla. La plantilla vieja lo renderizaba (siempre vacío) y no se
puede filtrar por él (`FieldError`). La pantalla nueva no lo usa.

### 3. "Pendiente de revision" sin tilde, en texto que se ve en pantalla

Estaba en las `choices` del modelo. Corregido (migración `syh.0034`).

## Verificación

Suite: **51 tests en verde** (17 nuevos de la vista agrupada).

Contra producción, con navegador:

1. La pantalla carga con los contadores y las secciones por empresa en orden
   de urgencia.
2. El botón de fotos de un hallazgo trae la foto con su estado
   ("Pendiente de revisión"), fecha y quién la subió.
3. El buscador responde ("sillones" → 1 resultado).
4. El item de menú "Hallazgos" queda resaltado al estar en la pantalla.

Los tests de JS no existen: los de la bandeja pasaron en verde con dos
`ReferenceError`. El chequeo de navegador es parte del trabajo, no un extra.

## Cuarta parte: el menú y un 500 que no se veía

El usuario avisó "no cambiaste nada" mirando `/admin/syh/evidencia/`. Tenía
razón en el síntoma: la pantalla nueva está en otra URL, y encima esa URL
**daba 500 sin sesión**. Con sesión andaba, por eso no se había visto.

### El 500

La vista no tenía `@login_required` y hacía
`Profile.objects.get(user=request.user)`. Con un `AnonymousUser` eso tira
**TypeError**, no `Profile.DoesNotExist`, así que el `except` no lo agarraba
y la vista reventaba. Es bug viejo, de la vista original: sin sesión nunca
funcionó. Ahora hay `login_required` en la vista y en el endpoint de
evidencias, con dos tests que fijan que sin sesión responda 302/403 y **nunca
500**.

Corolario: un test que dice "responde bien" no alcanza si nunca probaste el
camino sin sesión.

### El menú

"Hallazgos" estaba escondido dentro de "Informes", que es un submenú: dos
clicks para llegar a la pantalla de trabajo. Y la gente terminaba laburando
en el admin, que es para cargar datos.

- **Hallazgos** va ahora al primer nivel, justo debajo de Tablero.
- Sale de Informes, que queda solo con reportes.
- La etiqueta del reporte de accesos se actualizó (decía
  "Informes - Hallazgos").

### El resaltado nunca funcionó

El sidebar marca el item activo comparando `segment`, y cada vista lo pasa en
su contexto. La de hallazgos no lo pasaba, así que el link nunca se encendía
— tampoco cuando estaba en Informes. Agregado, con un test que lo fija.

## Quinta parte: filtros y edición (me había pasado de corrección)

El usuario: "no puedo filtrar por empresa, ni por estado, además no puedo
modificar nada". Tenía razón. Al quitarle el aire de admin, le había quitado
también las funciones: se había pedido otra **forma de ver**, no menos
capacidades.

- **Filtro por empresa** (plegado, con scroll: son 16 y a la vista empujaban
  los hallazgos fuera de la pantalla) y **por estado** (abiertos / Incumplido /
  Gestión en Curso / Cumplido / Cerrado).
- Son links, no un formulario con botón "Aplicar": no hay nada que aplicar.
- **Los cuatro contadores de arriba son filtros**: click en "Vencidos" y la
  lista se acota. El contador NO cambia con el filtro, porque si cambiara,
  filtrar por vencidos dejaría el contador de vencidos en cero.
- **Botón "Editar" por hallazgo**: estado, responsable, fecha de vencimiento y
  observación. Al guardar recarga y los contadores se recalculan en el
  servidor, en vez de reproducir esa aritmética en el navegador.
- Marcar **Cumplido** pone la `fecha_realizado` si no la tiene: un hallazgo
  cerrado sin fecha de cuándo se hizo no sirve para el resumen mensual.
- El update exige CSRF y el mismo corte por cliente que la vista.

### Dos bugs que encontraron los tests al escribirlos

1. **Un POST vacío borraba el responsable y las observaciones.** Ahora solo se
   toca lo que vino en el POST.
2. **Filtrar por "vencidos" mostraba el total de abiertos** en vez de los
   visibles. Agregado `visibles` al grupo, separado de `total`.

## Sexta parte: comentarios que se imprimían en la pantalla

Al mirar la pantalla desplegada apareció el texto de un comentario de Django
escrito en el medio de la página, y otro en el sidebar.

**Los comentarios `{# ... #}` de Django no pueden ocupar varias líneas.**
No tiran error: Django los imprime como texto. Todos los templates que trae
Django usan comentarios de una sola línea, por algo.

Pasó dos veces en esta tanda, en dos archivos distintos, y en ninguno de los
dos casos hubo excepción ni fallo de test: solo texto en pantalla. Se
cambiaron por el tag de bloque `{% comment %}` / `{% endcomment %}`, que sí
acepta varias líneas.

Trampa del tag de bloque: **no puede contener el texto `endcomment` adentro**,
porque lo cierra antes de tiempo y el que queda después da
`TemplateSyntaxError: Invalid block tag 'endcomment'`. Pasó.

Hay un test que revisa las cuatro plantillas del flujo y falla si encuentra
un `{#` sin su `#}` en la misma línea. Se verificó que muerde.

## Pendientes

- **Decidir qué hacer con los 482 vencidos.** La pantalla los muestra, pero
  probablemente haya un corte de historia.
- **`subido_por` vacío** en las áreas sin teléfono de responsable cargado. El
  área Sistemas del cliente de prueba es una.
- **La vista de hallazgos no tiene paginación**: si una empresa tiene 187
  vencidos, el "y N más" los mete todos en el DOM. Con `?todos=1` funciona,
  pero si una empresa crece mucho la página se va a hacer pesada.
- **No hay forma de cambiar el estado de un hallazgo** desde la pantalla. Se
  ve y se lista, pero para corregir un estado hay que ir al admin.
- **Pendientes de las tandas anteriores**, siguen igual:
  - `Movimientos.id` con default compartido (`syh/models.py:138`).
  - `syh_evidencia.movimiento` varchar(10) vs varchar(20) en base nueva.
  - Números de WhatsApp de prueba.
  - El VPS reinicia solo a las 02:00.
  - Tests de `home`, `moviles` y `usuarios` son stubs.
  - `print(resultados)` en `syh/models.py:478`.