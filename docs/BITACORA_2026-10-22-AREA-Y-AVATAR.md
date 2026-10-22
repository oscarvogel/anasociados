# Bitácora — 22/10/2026: el filtro por área y el avatar "fuera de escuadra"

Dos cosas que llegaron juntas desde el portal de AN:

1. **El ícono del usuario se veía "fuera de escuadra"**: un círculo verde con
   la inicial colgando por abajo, medio fuera del círculo.
2. **Al filtrar los hallazgos se podía elegir empresa, pero no área.**

| | Antes | Ahora |
|---|---|---|
| Avatar del header | Inicial colgando fuera del círculo + un chevron de más | Inicial centrada en el círculo, un solo chevron |
| Filtro de área en Hallazgos | No existía (solo empresa y estado) | Pastilla "Área", con las áreas de la empresa elegida |
| Links de los filtros | Escritos a mano en la plantilla | Los arma `hl_query`: cambian un filtro y dejan los otros |
| Buscador | Al buscar se perdían empresa y estado | Conserva todos los filtros |

Archivos tocados: `static/src/css/an-custom.css`,
`utiles/templatetags/hallazgos.py` (nuevo),
`templates/pages/syh/visualizar_movimientos.html`, `syh/views.py`,
`syh/tests.py`.

## El avatar "fuera de escuadra"

### El síntoma

En el header, arriba a la derecha, el círculo verde con la inicial (la "N" de
Neri, la "I" de Indufor) se veía así:

```
   ( N     <- la inicial asoma por abajo del circulo y se sale de el
  (   )
```

En el celular se veía peor: la inicial asomaba como una muesca blanca en el
borde inferior del círculo.

### La causa

El tema de Colorlib (Datta) tiene esta regla:

```css
.pcoded-header .dropdown .dropdown-toggle {
  line-height: 70px;      /* <- la culpable */
  display: inline-block;
  padding-right: 15px;
}
```

`.an-topbar__user` (el link del usuario) tiene **3 clases** en el selector del
tema (`.pcoded-header .dropdown .dropdown-toggle`) y el nuestro
(`.an-app .an-topbar__user`) tiene **2**: el tema gana.

Consecuencias, medidas en el navegador:

```
span.an-topbar__avatar   display: inline-grid   width: 34px   height: 34px
                         line-height: 70px      <- heredado del link
a.an-topbar__user        display: inline-block  line-height: 70px
```

El `line-height: 70px` se heredaba al `<span>` del avatar. El span es un
`inline-grid` de 34x34 con `place-items: center`, pero **la caja de línea del
texto mide 70px**, más que el grid: la inicial se dibujaba en una caja más
alta que el círculo y quedaba colgando por abajo, fuera de él.

Lo mismo pasaba con la alineación: el link era `inline-block` y no
`inline-flex`, así que `align-items: center` y `gap` de nuestro CSS no se
aplicaban.

### El arreglo

En `static/src/css/an-custom.css`, con más especificidad que la del tema:

```css
.an-app .pcoded-header .navbar-nav .dropdown.drp-user > .an-topbar__user {
  display: inline-flex; align-items: center; gap: .55rem; line-height: 1.4;
  vertical-align: middle; padding: 0 .75rem; color: var(--an-color-text); font-weight: 700;
}
.an-app .an-topbar__avatar {
  display: inline-grid; width: 34px; height: 34px; place-items: center;
  line-height: 1; font-weight: 800; border-radius: 50%; color: #fff; background: var(--an-color-primary);
}
```

Medido después del arreglo:

```
span.an-topbar__avatar   line-height: 14px
a.an-topbar__user        display: inline-flex   line-height: 19.6px
letra "N"  x=1359.6 y=25.6 w=10.5 h=19   (circulo x=1347.9 y=18.6 w=34 h=34)
```

La letra queda **dentro** del círculo, y el círculo dentro del header.

### El segundo chevron

La misma regla del tema agrega un chevron propio:

```css
.pcoded-header .dropdown .dropdown-toggle:after {
  content: "\e842"; font-family: 'feather';
  position: absolute; top: 0; right: 15px;
}
```

Como la plantilla ya trae su propio `<i class="feather icon-chevron-down">`,
se veían **dos chevrones**: uno pegado al nombre y otro suelto contra el
borde derecho del header (bien visible en las capturas que mandaron). Se
desactiva con:

```css
.an-app .pcoded-header .dropdown.drp-user > .an-topbar__user::after { content: none; }
```

**Conclusión de método:** el bug se ve en el navegador, no leyendo el CSS.
Lo que hizo falta fue medir los estilos calculados (`getComputedStyle`) en la
página real, no adivinar.

## El menú de usuario seguía en azul

Lo pidió Oscar con una captura, después del despliegue de lo de arriba: al
abrir el menú de usuario (Mi perfil / Cambiar contraseña) la banda de arriba
seguía **azul**, y con ella el triángulo que une el panel con el header.

Es el tema: pinta ese menú con su propio azul, `#04a9f5`.

```css
.pcoded-header .dropdown .profile-notification .pro-head { background: #04a9f5; }
.pcoded-header .dropdown.drp-user.show:before          { color: #04a9f5; }
.pcoded-header .dropdown .profile-notification .pro-body li:hover { background: rgba(4,169,245,.1); }
```

En el diseño AN el header es verde, así que el menú va en el mismo verde del
avatar (`--an-color-primary`), con el texto del panel en el color de texto de
AN y el hover en verde claro.

Medido después del arreglo:

```
.pro-head                 background rgb(59, 93, 48)   = --an-color-primary
drp-user.show:before      color      rgb(59, 93, 48)   = --an-color-primary
pro-body li a             color      rgb(38, 51, 38)   = --an-color-text
pro-body li:hover         background rgb(242, 246, 236) = --an-color-surface-soft
pro-body li:hover > a     color      rgb(44, 74, 29)   = --an-color-primary-strong
```

**Ojo con la especificidad:** las reglas del tema tienen cuatro clases
(`.pcoded-header .dropdown .profile-notification .pro-head`) y las de AN dos
(`.an-app .an-topbar__avatar`). Con dos, el tema gana: por eso las reglas
nuevas van con `.an-app` delante, para quedar en cinco.

## El filtro por área

### Lo que faltaba

La vista (`syh/views.py`) **ya filtraba por área**: `_filtros_hallazgos`
lee el parámetro `area` y lo aplica a la consulta, y el PDF de la pantalla
también lo usa. Lo que **no existía** era el botón para elegirlo: en la
plantilla no había ni un `area=`.

O sea: el filtro existía, era invisible.

Además, los links de la barra de filtros estaban **escritos a mano** en la
plantilla, cada uno armando su URL con la lista de parámetros que se le
acordaba. Por eso el área no estaba en ninguno: no era que estuviera mal, es
que **no había dónde anotarla**.

### Lo que se hizo

**1. Un tag de plantilla** (`utiles/templatetags/hallazgos.py`) que arma los
links desde los parámetros que ya tiene la petición:

```django
{% hl_query empresa=pk %}        {# cambia la empresa, conserva area, estado y busqueda #}
{% hl_query area=None %}          {# saca el area de la URL #}
{% hl_query estado=opcion.seleccionados %}   {# estados: replaces la lista entera #}
```

Un filtro que puede valer más de una vez (los estados) se pasa como lista y
se reemplaza entero. Con `None` se saca el filtro.

**2. La vista** (`syh/views.py`):

- `_areas_visibles(cliente, areas_profile, empresa_sel)`: las áreas que el
  usuario puede filtrar. Con empresa elegida, **solo las de esa empresa**;
  sin empresa, todas las que puede ver.
- `area_sel_nombre`: el nombre del área elegida, para el resumen de la
  pastilla.
- `estados_opciones`: para cada estado, la lista de estados que quedan
  elegidos si se aprieta esa pastilla. El "se acumulan" de los chips se
  calcula **en el servidor**, no en la plantilla.

**3. La plantilla**: una pastilla "Área" igual que la de empresa (plegada,
porque son 35 áreas), y **todos** los links de la pantalla pasan a usar
`hl_query`.

### Decisiones que hubo que tomar

1. **El nombre del área lleva el de la empresa cuando hay más de una.**
   Hay áreas que se llaman igual en empresas distintas: "Transporte" está en
   Forestal Río Claro, en Holc Pedro Pablo y en Muller Antonio; "Silvicultura"
   en Lezcano y en Mezetti. Con empresa elegida el nombre va solo; sin ella,
   va "Transporte · Forestal Río Claro".

2. **Cambiar de empresa deja el área en cero.** El área pertenece a una
   empresa: si se elige una empresa que no tiene el área elegida, la pantalla
   se queda vacía sin explicación. Es preferible que el link de empresa
   limpie el área.

3. **El buscador conserva los filtros.** El buscador es un formulario GET:
   si no lleva los filtros escondidos, al buscar se perdían la empresa y el
   estado (y ahora también el área). Ahora lleva `empresa`, `area`, `estado` y
   `vista` como campos escondidos.

4. **El PDF lleva el área.** `_url_imprimir_hallazgos` ya la contemplaba; con
   el filtro en pantalla, el archivo sale con lo que se está viendo.

### Un bug que apareció de paso

El CSS del filtro plegado se llamaba `.hl-filtros--plegado` y la plantilla
usaba `.hl-filtros--plegable`: **nunca coincidieron**, así que el filtro de
empresa nunca estuvo plegado de verdad (por eso en las capturas se ve la
lista de empresas entera, empujando los hallazgos). Ahora las dos partes se
llaman igual.

### Un bug que no era del filtro

Los links de los filtros ahora salen con `&amp;` (HTML válido: Django
escapa el `&` que arma el tag). Los tests parseaban la URL **cruda** del
HTML, así que veían un parámetro llamado `amp;estado` en vez de `estado`.
Se resolvió deshaciendo la entidad antes de parsear (`html.unescape`), que es
lo que corresponde: el HTML nuevo es el correcto, el viejo escribía `&` a
mano dentro del `href`.

## Cómo se verificó

- **Suite completa contra MySQL real** (la base de producción, con
  `.venv-dj52` / Django 5.2.18): `107 tests, OK` (63 en `syh`). 10 tests
  nuevos del área.
- **Navegador contra la base real**, entrando como `neri` (superusuario):
  - 1638x969 y 1366x768: los filtros no se pisan ni generan scroll horizontal.
  - 390x844 (celular): el avatar se ve bien y los filtros apilan.
  - El área filtra de verdad: `?empresa=d35991e2&area=7fa54b9b` deja los 14
    hallazgos de "Cosecha PM" de Indufor y los contadores de arriba se
    actualizan.
  - Los chips de estado siguen **sumándose** con el área puesta.
  - El link del PDF sale con `empresa`, `area` y `estado`.

### Dos cosas que se aprendieron en el camino

1. **Un filtro invisible no es un filtro.** La vista filtraba por área desde
   antes; lo que faltaba era el botón. Antes de "agregar la funcionalidad"
   hay que preguntarse si lo que falta es el dato o la puerta.
2. **Los links escritos a mano en la plantilla no escalan.** Cada filtro
   nuevo tenía que agregarse a todos los links (y por eso el área faltaba en
   todos). Armarlos con un tag los deja juntos en un solo lugar.

## Despliegue

**22/10/2026, 10:18**, contra `vps-3177145-x.dattaweb.com:5438`, proyecto en
`/var/www/an`.

```
git push origin main                   # 22b8bef..b283e64
ssh anasociados "cd /var/www/an && git pull --ff-only origin main"
systemctl restart an.service           # gunicorn 23.0.0, 3 workers, sin errores
```

El pull entró como **fast-forward limpio**: el servidor tiene archivos locales
sin versionar (dos PNG de gráficos, un PDF de resumen y dos `.sh`), pero son
artefactos generados y no tocan código. La base **no se toca**: no hay
migraciones.

Tres commits, uno por tema:

```
54405de feat: los hallazgos se pueden filtrar por area
4f8e700 fix: la inicial del avatar ya no queda colgando fuera del circulo
b283e64 docs: bitacora del filtro por area y el avatar
```

**Nginx sirve los estáticos por alias** (`location /static/ { alias
/var/www/an/static/; }`), así que el CSS nuevo se ve **sin `collectstatic`**.

### Verificación en producción

- `https://portal.anasociados.com.ar/` responde.
- El CSS que devuelve el servidor tiene las tres reglas nuevas: el bloque de
  usuario redefinido, el `::after` del tema desactivado y el `line-height: 1`
  del avatar.
- `/syh/movimientos/` responde **200** con y sin filtros, y en el HTML:
  la pastilla de "Área", el área elegida, los links con `area=` y el link del
  PDF con `empresa` y `area`.
- En el navegador, a 1638x969, contra el portal real:

```
.an-topbar__avatar   line-height: 14px        (era 70px)
.an-topbar__user     display: inline-flex     (era inline-block)
::after del tema     content: none            (el chevron duplicado)
letra "o"   x=1482.2 y=25.6 w=11.2 h=19
circulo     x=1470.8 y=18.6 w=34  h=34       -> la letra esta dentro
```

La sesión que se usó para verificar se **borró** de la base al terminar
(comprobado: la misma cookie ahora recibe un 302 en vez de un 200) y los
scripts de comprobación se eliminaron del servidor.

### Una nota de PowerShell

Los mensajes de commit con **here-strings** (`-m @'...'@`) no served: PowerShell
partió el texto en palabras y `git` los Tomó como rutas ("pathspec 'de' did not
match"). Con `-F <archivo>` el mensaje va como está. También: el pipe de
PowerShell a un comando nativo mete **BOM** (U+FEFF) y Python lo rechaza como
carácter no imprimible: para mandar un script al servidor conviene `scp`, que
manda los bytes crudos.

## Pendientes

- **El área no se puede elegir desde la URL sin empresa.** Sin empresa
  elegida la lista trae las 35 áreas de las 16 empresas. Funciona, pero es
  larga: si molesta, se puede filtrar por empresa primero (que es lo natural).
- **La búsqueda no busca por el nombre del área.** El buscador mira el
  hallazgo, el responsable y el id. Buscar "Cosecha PM" no trae los hallazgos
  del área: para eso está el filtro.
- Sigue igual lo de la tanda anterior: el PDF no lleva las fotos de los
  hallazgos; el envío por WhatsApp necesita `WHATSAPP_ENABLED` y
  `WHATSAPP_API_KEY` en el `.env` del VPS.
- **Falta probarlo en el teléfono.** Lo verificado en producción es con
  navegador de escritorio; el recorrido de Oscar desde el celular (que es de
  donde mandaron las capturas) queda para él.
