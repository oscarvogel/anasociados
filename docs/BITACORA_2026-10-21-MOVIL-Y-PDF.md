# Bitácora — 21/10/2026: el menú del celular, el PDF de los pendientes y el WhatsApp

## Qué se hizo

Tres pedidos que llegaron juntos en un audio de WhatsApp de Oscar (el que
releva los hallazgos en las visitas y después se los pasa al encargado):

1. **Desde el celular no se abría el menú.**
2. **No se podía enviar el resumen por WhatsApp.**
3. **No se podía imprimir (descargar el PDF) de los pendientes.**

El resultado: **el menú se abría perfecto y el WhatsApp funcionaba perfecto**;
lo que no estaba era **el botón**. Y el botón de imprimir **no existía**: se
había ido con el rediseño de la pantalla de hallazgos.

| | Antes | Ahora |
|---|---|---|
| Menú en el celular | Botón invisible | Botón visible, menú con máscara y cierre |
| PDF de los pendientes | Botón borrado, vista huérfana | Botón en Hallazgos y en el Tablero |
| Enviar por WhatsApp | funcionando, pero **inalcanzable** | funcionando y a dos toques |
| Cerrar los pendientes | De a uno, con recarga por cada uno | De a varios, de una |

Archivos tocados: `static/src/css/an-custom.css`, `utiles/impresiones.py`,
`syh/views.py`, `syh/urls.py`, `syh/tests.py`, `home/views.py`,
`home/tests.py`, `templates/pages/index.html`,
`templates/pages/syh/visualizar_movimientos.html`.
## El botón de menú invisible

### El problema

El tema de Colorlib dibuja el botón de menú (las tres rayas) en **blanco**:
su header es azul oscuro (`#3f4d67`) y las rayas se ven. El diseño de AN
pone el header **blanco** (`an-custom.css: .an-app .pcoded-header { background:
#fff }`) y las rayas se quedaron blancas sobre blanco.

El botón estaba en el DOM, con su tamaño y su posición correctas. Medido en
el navegador a 429 px:

```
A#mobile-collapse1.mobile-menu  rect: x=428 y=0 w=37 h=70
  span            background-color: rgb(255, 255, 255)   <- blanco
  span::before    background-color: rgb(255, 255, 255)   <- blanco
  span::after     background-color: rgb(255, 255, 255)   <- blanco
```

O sea: el botón estaba, se podía tocar, y no se veía. Desde el celular no
había forma de llegar a **Alertas WhatsApp**, a **Hallazgos** ni a nada.

### El arreglo

En `an-custom.css`, las rayas del header toman el verde del sistema visual:

```css
.an-app .pcoded-header .mobile-menu span,
.an-app .pcoded-header .mobile-menu span::before,
.an-app .pcoded-header .mobile-menu span::after { background-color: var(--an-color-primary-strong); }
```

Con el menú abierto el botón se convierte en una X, así que la barra del medio
se transparentiza y las dos diagonales toman el mismo verde.

### Bugs que aparecieron probando, no leyendo

1. **El botón de la barra lateral también estaba invisible.** El tema lo
   pinta en `#a9b7d0` (gris azulado) y AN le puso fondo blanco a la marca.
   Como en el celular el tema hide la marca de la barra lateral, no molesta
   en el teléfono: se deja como estaba.
2. **Franja gris suelta arriba de todo** con el menú abierto. Es la máscara
   de oscurecido del tema (`.pcoded-header::before`, `rgba(0,0,0,.2)`), que
   queda pegada al **alto del header** (141 px) y no a la pantalla: se veía
   una banda gris arriba y el resto de la página sin oscurecer. Ahora es una
   capa fija que cubre la pantalla entera.
3. **La X no se podía apretar.** La máscara se pinta por encima del botón
   que la cierra (`z-index: 1` contra `z-index: auto`). Con `z-index: 2` el
   botón queda arriba.

**Conclusión de método:** los tres aparecieron abriendo el portal en el
navegador a 429 px. `manage.py check` y los tests no los veían: el botón
estaba perfecto para el navegador.

## El teléfono seguía viendo la versión vieja del CSS

Desplegado el arreglo del botón de menú, Oscar entró desde su celular y **no
veía las rayas**. El servidor ya servía el archivo nuevo (comprobado con un
`curl` al CSS), la plantilla también, y en el navegador de la máquina el
botón se veía bien. En el teléfono, no.

La causa: **Nginx sirve los estáticos sin `Cache-Control`**. El navegador
entonces guarda el CSS con la heurística del 10% sobre la antigüedad del
archivo: como el CSS hacía días que no cambiaba, la vencimiento daba por
horas o por días. El celular entraba con el HTML nuevo (el HTML va con
`no-cache, no-store`) pero con el CSS viejo, y ahí seguían las rayas
blancas.

La solución es **poner la versión del archivo en la URL**: cada cambio de CSS
es una URL nueva y el navegador no la tiene guardada.

- `utiles/templatetags/estaticos.py`: el tag `{% estatico %}`, que hace lo
  que `{% static %}` pero con `?v=<mtime>` al final.
- `head.html` y `scripts.html`: todos los estáticos pasan por el tag.
- Las plantillas públicas y las de móviles también. Las que tenían `?v=3` y
  `?v=9` a mano quedan con la versión sola: no hay que acordarse de subirla
  en cada cambio.

Un detalle que costó: la versión se busca con los **finders** de staticfiles
y no con `staticfiles_storage.path()`, que apunta a `STATIC_ROOT` (una copia
vieja de `collectstatic`, sin los archivos del proyecto). Con los finders
sale el archivo de fuente, que es el que sirve Nginx por alias.

## El PDF de los pendientes

### Lo que había pasado

El reporte **existía y funcionaba**. Lo que se había perdido era el botón:

- El botón `#btnImprimir` estaba en el Tablero y **se fue con el rediseño** de
  la pantalla de hallazgos (commit `91833cf`, *"hallazgos: agrupados por
  empresa con los pendientes arriba"*).
- La vista `syh:imprimir_movimientos` quedó **huérfana**: no la enlazaba
  nadie. El `menu` la tenía escrita en `active_view_names`, como resto de la
  vida anterior.
- La clase `ImprimeHallazgos` **reventaba sin empresa ni área**: pedía
  `cliente.id` y `area.id` del filtro, y sin filtro no había ninguno.
  `GET /syh/imprimir_movimientos` sin parámetros devolvía **500**.
- La misma vista **no pedía sesión**: con la URL se leía el PDF con los
  hallazgos de **todas** las empresas sin entrar al sistema.
- Cada pedido escribía un **`grafico_torta.png` en el directorio de trabajo**
  del servidor (y el gráfico, además, nunca se usaba: estaba comentado el
  `drawImage`).

### Lo que se hizo

**1. La clase del reporte, reescrita** (`utiles/impresiones.py`).

- El título y el nombre del archivo salen de los **propios hallazgos** del
  reporte, no de los parámetros del filtro. Con varias empresas el archivo se
  llama `hallazgos-16-empresas-20261021.pdf` en vez de poner el nombre de la
  primera, que mentía en la etiqueta.
- El resumen por estado se calcula con los hallazgos del reporte: **el
  resumen y la lista no pueden contradecirse** y no hay forma de que falte el
  cliente o el área.
- **No escribe archivos en el servidor** y no usa matplotlib.
- Columnas: Fecha, Vence, Estado, Hallazgo, Responsable. La columna del
  responsable se agrega porque el PDF es el que se le pasa al encargado.
- El sello **`Impreso 21/10/2026 14:28:30`** lo pone la clase base y queda en
  todas las páginas. Es lo que zanja el *"che, pero todavía me aparece como
  incumplido"*: si el PDF dice cuándo se descargó, el archivo es el que manda.

**2. Una vista nueva** (`syh:imprimir_hallazgos`), con **los mismos filtros
que la pantalla**: empresa, área, estado, búsqueda y franja (vencidos, por
vencer, por revisar). Los filtros se sacaron de la vista de pantalla a una
función compartida (`_filtros_hallazgos`) para que **el PDF y la pantalla no
puedan mostrar cosas distintas**.

El PDF lleva **todos** los hallazgos del filtro, no los 8 por empresa que se
muestran en pantalla: un reporte truncado no sirve para pasarlo a nadie.

**3. La URL vieja sigue viva.** `syh:imprimir_movimientos` ahora delega en la
nueva (el Tablero y los enlaces guardados la usan) y **pide sesión**, que
antes no pedía.

### Los botones

- **Hallazgos**: botón "Descargar PDF" en la cabecera, con los filtros que se
  están viendo. En el celular queda a todo el ancho, arriba de todo.
- **Tablero**: botón "Descargar PDF" debajo de "Filtrar", con la empresa y el
  área elegidas. **Aparece solo con empresa elegida**: sin filtro el archivo
  traería los pendientes de las 16 empresas, que no es lo que se está mirando.
  Es el flujo que Oscar usaba antes.

## Cerrar varios hallazgos de una vez

El PDF es la lista para llevar y después cerrar. Pero cerrar era de a uno:
abrir el editor, elegir el estado, guardar y esperar que la página se recargue.
En el celular, con diez hallazgos de la visita, es media hora de taps.

Ahora cada hallazgo abierto tiene una **casilla** y, al marcar alguno, aparece
abajo una **barra fija** con "N seleccionados" y el botón "Marcar como
cumplidos". Un toque y se cierran todos los marcados.

- Los que quedan marcados se ponen en **Cumplido** y, si no tenían fecha de
  realizado, se les pone **la de hoy**: un hallazgo cerrado sin fecha de
  cuándo se hizo no sirve para el resumen mensual.
- Solo se cierran **los hallazgos que el usuario puede tocar**, con el mismo
  corte que la edición de a uno: un usuario de una empresa no cierra los de
  otra aunque mande los ids. El chequeo es id por id, con
  `_hallazgo_permitido`.
- Las casillas solo aparecen en los hallazgos **abiertos**: marcar uno ya
  cerrado no tiene sentido.
- La barra aparece sola cuando hay algo marcado y desaparece al recargar, así
  no ocupa lugar en una pantalla que se mira mucho. El cuerpo de la página
  gana un `padding-bottom` mientras está visible, para que el último hallazgo
  no quede debajo.

## El WhatsApp

**No estaba roto.** Se llegó, se eligió empresa y área, se preparó el resumen
y se abrió el modal de confirmación, todo a 429 px de ancho. El botón de
enviar responde *"No se pudo enviar el mensaje. Revisá la conexión con
WhatsApp e intentá nuevamente"* porque **localmente no hay API key**.

Lo que le falta al servidor es lo de siempre: `WHATSAPP_ENABLED=True` y
`WHATSAPP_API_KEY` en el `.env` del VPS. Eso no se puede verificar desde
aca: queda como pendiente.

El mensaje que se manda **lleva un enlace público** a los hallazgos del área,
así que el encargado los ve sin entrar al sistema.

## Cómo se verificó

**Con datos reales, no con SQLite.** Se levantó una MariaDB 11.8 en WSL
(puerto 3308, datadir en `~/mysql_an`) y se importó `mysql/an.sql`, el dump
de producción: 1310 movimientos, 16 clientes, 34 áreas, 19 usuarios.

- **Suite completa contra MySQL real**: `92 tests, OK` (con `.venv-dj52`,
  Django 5.2.18, que es el de producción). 18 tests nuevos: 8 del PDF, 7 del
  cierre masivo y 3 del botón de menú.
- **Navegador a 429 x 969** (el ancho del celular del cliente): menú que
  abre, botón que se ve, PDF que se descarga, WhatsApp que llega al modal.
- **El PDF abierto en un visor real** (el visor de PDF del Chrome), no solo
  mirando el `%PDF` del principio: se vio la cabecera con el logo, el sello
  de fecha y hora, las columnas sin pisarse y el resumen por estado.

### Dos cosas que se aprendieron en el camino

1. **En Windows, `Get-Content` lee como ANSI**: al agregar los tests con
   PowerShell, las tildes del archivo quedaron doblemente codificadas y
   **fallaron dos tests que ya estaban en verde** (`"Gestión en Curso"` ya no
   era un estado válido y el view rechazaba el POST entero). Los archivos se
   tocan con Python en UTF-8.
2. **El `python.exe` del venv es un lanzador**: el proceso que de verdad
   escucha el puerto es el intérprete base (`C:\Program Files\Python312`).
   Matar el lanzador deja vivo al otro sirviendo **la version vieja** de las
   plantillas, y parece que los cambios no se aplican. Para parar el server
   hay que matar al dueno del puerto:
   `Get-NetTCPConnection -LocalPort 8123 -State Listen` y despues
   `Stop-Process` sobre ese PID.

### Un bug del cierre masivo que solo aparecio en el navegador

El POST de "marcar varios" llegaba con `400 No elegiste ningun hallazgo`:
los ids iban pero Django no los leia. La causa era mandar el cuerpo como
**texto** (`body: cuerpo.toString()`): el navegador lo manda como
`text/plain` y Django no lo parsea como formulario. Hay que mandar el
`URLSearchParams` **como objeto** (`body: cuerpo`), que es lo que hace que el
navegador ponga el `Content-Type` correcto. Los tests de la vista pasaban
iguales: el problema estaba en como se armaba la peticion, no en la vista.

## Despliegue

**21/10/2026, 15:36** (menú + PDF) y **15:50** (cierre masivo), contra
`vps-3177145-x.dattaweb.com:5438`, proyecto en `/var/www/an`.

```
git pull --ff-only origin main   # c93532d..df16403, fast-forward
systemctl restart an.service     # gunicorn 23.0.0, 3 workers, sin errores
```

El servidor tiene cambios locales, pero son **artefactos generados** (los
PNG de los graficos, un PDF de resumen y dos .sh), no codigo: el pull entra
limpio. La base no se toca: **no hay migraciones nuevas**.

Verificacion en produccion:

- `https://portal.anasociados.com.ar/` responde 200.
- El CSS nuevo se sirve: las tres reglas nuevas (rayas, mascara y boton de
  descarga) estan en el `an-custom.css` que devuelve el servidor.
- `journalctl -u an.service`: gunicorn levanta 3 workers y no registra
  errores.

Lo que **no** se pudo verificar desde aca es el recorrido de Oscar en su
celular: eso hay que probarlo en el telefono.

## Pendientes

- **Confirmar en el VPS que `WHATSAPP_ENABLED` y `WHATSAPP_API_KEY` están
  cargados.** El envío no se puede verificar desde la maquina de desarrollo:
  aca no hay API key y el error es correcto. Es lo unico que impide que
  Oscar mande el resumen.
- **El PDF no lleva las fotos de los hallazgos.** Sale el texto del
  hallazgo, el area, el responsable y las fechas, pero no las evidencias.
  Meterlas requiere otra clase de reporte (y decidir cuantos y de que peso).
- **El PDF no se puede mandar solo por WhatsApp.** El sistema manda texto con
  un enlace; el archivo lo baja Oscar y lo comparte desde el telefono. Si se
  quiere mandar el PDF adjunto por la API, hay que ver que soporta el
  gateway (`oscarvogel/vogel_whatsapp_api`).
- **La URL vieja cambio de significado.** `syh:imprimir_movimientos` antes
  traia **todos** los movimientos, cumplidos incluidos; ahora trae los
  **pendientes**, que es lo que se pide. Si algun enlace guardado dependia de
  los cumplidos, va a ver menos filas.
- **La instancia MariaDB de WSL en el 3308** quedo levantada con una copia
  del dump de produccion. Es de descarte: si se quiere volver a levantarla,
  los pasos estan en `docs/ENTORNO_DE_DESARROLLO.md` (el datadir nuevo esta
  en `~/mysql_an`, con `mariadb-install-db` en vez de MySQL 8). El puerto
  3307 que se documenta en ese archivo **no** arranco: el datadir viejo era de
  MySQL 8 y la MariaDB 11.8 del sistema no lo puede abrir.
- **Falta `collectstatic`?** No: Nginx sirve los estaticos por alias al
  directorio **fuente**, asi que el CSS nuevo se ve sin collectstatic. Igual
  que antes.
- De la tanda anterior, siguen igual: la vista `register` de `admin_datta` es
  una puerta a un error 500; `TEMPLATE_DIRDATB` apunta a un directorio que no
  existe; los tests de `moviles` y `home` eran stubs (`home` ahora tiene los
  tres del boton de menu); tres graficos del Tablero se ven vacios sin filtro.
