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

Los tests de JS no existen: los de la bandeja Janvier pasaron en verde con dos
`ReferenceError`. El chequeo de navegador es parte del trabajo, no un extra.

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