# Bitácora — 14/10/2026 (quinta tanda): combos con autocomplete, el login del portal y los diálogos

## Qué se hizo

Tres cosas, dos pedidas y una que apareció en el camino:

1. Todos los `<select>` de la app pasaron a ser **autocomplete con filtro**.
2. El **login del portal** seguía mostrando el tema viejo de Colorlib.
3. Los **diálogos de confirmación** eran los nativos del navegador.

Commits: `adfaf1a` (autocomplete), `070646e` (login), `87edc1d` (diálogos).

## Los combos

### El problema

Con 16 empresas y áreas que se cargan por Ajax, elegir del desplegable nativo
era recorrer una lista larga sin buscar nada. El peor caso es el área de
Forestal Río Claro: 7 opciones que serellenan después de elegir empresa.

### Por qué un componente propio y no Select2

El proyecto ya trae jQuery, Bootstrap, Toastr y SweetAlert2 por CDN, así que
agregar una librería no rompía la convención. Se escribió a mano igual, por una
razón concreta: **la mitad de los combos se llenan por Ajax**, y Select2 hay que
rearmarlo cada vez que cambian las opciones. El componente lo resuelve solo.

`static/src/js/an-autocomplete.js` (434 líneas), estilos `.an-combo` en
`an-custom.css`.

### Lo que lo hace seguro de desplegar global

- **El `<select>` nativo queda en el DOM, oculto.** Al elegir se dispara un
  `change` NATIVO sobre el select, así que el código de cada pantalla sigue
  funcionando sin cambios: listeners, lecturas de `.value`, submits de
  formulario.
- **Un `MutationObserver` re-sincroniza los combos que se llenan por Ajax.** El
  select de área de hallazgos WhatsApp se convierte solo cuando llegan sus 7
  opciones. No hizo falta tocar ese template.
- **Se conecta en un solo lugar:** `includes/scripts.html`, que solo incluye
  `layouts/base.html` y `base-auth.html`. **El admin de Django queda intacto.**
- **Los selects con menos de 6 opciones siguen nativos.** Para elegir entre tres
  meses un buscador es más lento que el desplegable. Se puede ajustar con
  `data-an-min-opciones`, yERY `data-an-no-autocomplete` desactiva uno.

Búsqueda sin acentos con el fragmento resaltado, navegación por teclado
(flechas/Enter/Escape) y roles `combobox`/`listbox`.

### Bugs que aparecieron probando, no leyendo

1. **Enter no elegía nada** si no se había apretado una flecha antes. Ahora,
   apenas se escribe, la mejor coincidencia queda resaltada sola.
2. **"Sin resultados" no se veía nunca:** `abrir()` lo ocultaba después de que
   `pintarLista()` lo habilitara.
3. **La lista se cortaba a la mitad.** `.an-card` tiene `overflow: hidden` y el
   dropdown terminaba en y=552 con la card cortando en y=386: de 9 opciones se
   veían 4. Ahora la lista va en `position: fixed` sobre `<body>`, y si no
   entra abajo abre hacia arriba.

**Conclusión de método:** los tres aparecieron abriendo la página en el
navegador. `manage.py check` y los tests no los veían.

## El login del portal

### Lo que pasó

Al ir a verificar los combos en producción, el login mostraba la pantalla vieja:
círculos azul/violeta, "Username", "Remember me?", "Create Account". El
rediseño de AN estaba hecho pero **no se veía en la puerta de entrada**.

### La causa

Hay **dos logins distintos** y son de familias distintas:

| URL | Plantilla | Diseño |
|---|---|---|
| `/admin/login/` | `templates/admin/login.html` | AN ✅ |
| `/accounts/login/` | la del paquete pip `admin_datta` | Colorlib ❌ |

`/accounts/login/` no lo sirve Django: lo sirve `django-admin-datta`
(`admin_datta`), que trae su propia plantilla. El rediseño vivía solo en
`templates/admin/login.html`, que es el login del **admin**, y el proyecto no
tenía ningún override en `templates/accounts/`. DIRS gana sobre APP_DIRS, pero
no había nada en DIRS que ganar.

O sea: **el rediseño funcionaba, pero se había verificado en la pantalla
equivocada**. Quien estaba logueado entra por `/accounts/login/`; `/admin/login/`
solo aparece si sos admin y vas directo a `/admin/`.

**Esto no lo causó el deploy de los combos**: el commit del rediseño
(`fdca231`) solo agregó `templates/admin/login.html`. El hueco venía de antes.

### El arreglo

Dos archivos que extienden el diseño sin contenido propio:

- `templates/accounts/login.html`
- `templates/accounts/auth-signin.html`

Una sola fuente de verdad: si se toca el diseño, se toca
`templates/admin/login.html` y las tres pantallas quedan al día.

Se necesitan los dos nombres porque **local y servidor tienen versiones
distintas de `django-admin-datta`**: la de desarrollo resuelve a
`accounts/auth-signin.html` y la del servidor a `accounts/login.html`.

### Cómo se verificó

Renderizando con el `AuthenticationForm` real: los tres login devuelven el
diseño AN, sin "Create Account" ni "Remember me".

En producción, por HTTP: `/accounts/login/` 200, `an-login__brand` presente,
"Iniciar sesión" presente, vendor ausente, token CSRF presente y
`name="next" value="/utiles/whatsapp/hallazgos/"` — o sea, el redirect a la
pantalla pedida sigue funcionando.

## Los diálogos de confirmación

### Lo que pasaba

El botón *Aceptar y cerrar el hallazgo* de la bandeja de revisión abría un
`window.confirm()`: el recuadro gris del sistema operativo, con el título del
navegador arriba ("portal.anasociados.com.ar dice"). En una página con el
diseño de AN, eso rompe el conjunto.

Y no era solo ese. Al buscar `confirm(`/`alert(` en los templates había **tres
vivos**, no uno:

| Dónde | Qué era |
|---|---|
| `pages/utiles/evidencias_revision.html:402` | `window.confirm` al aceptar evidencia |
| `pages/index.html:348` | `alert` "selecciona un cliente" del botón Filtrar |
| `pages/index.html:360` | `alert` "selecciona un cliente" del botón de resumen |

`pages/index.html` parecía una demo del vendor, pero no: `home.index` la
renderiza y es el **Tablero**, la primera pantalla del menú.

El cuarto, `pages/syh/resumen_mensual.html:56`, está dentro de un
`{% comment %}`: código muerto, nunca se renderiza.

### El arreglo

`static/src/js/an-dialog.js`, con la misma idea que el autocomplete: componente
propio, una sola fuente de verdad, sin librería nueva.

```js
ANDialog.confirm({titulo, mensaje, confirmar, cancelar, tono})  // -> Promise<boolean>
ANDialog.alert({titulo, mensaje, confirmar, tono})              // -> Promise<boolean>
```

Devuelven una Promise, así que el flujo encadena igual que antes. Tonos `info`,
`aviso`, `peligro` y `exito`, con los colores del design system.

Detalles que no son cosméticos:

- **El overlay va en `position: fixed` sobre `<body>`**, por el mismo motivo que
  la lista de los combos: las cards del proyecto tienen `overflow: hidden`.
- **El foco vuelve al botón que abrió el diálogo.** Con el nativo se perdía, y
  un usuario de teclado quedaba sin saber dónde estaba.
- Escape cierra, el click en el fondo cierra, y `alert` muestra un solo botón.

### Cómo se verificó

En banco de pruebas: los cuatro tonos, Escape resolviendo `false` con el foco
devuelto, el `alert` con un botón visible y el otro `hidden`, click en el fondo
cerrando, consola limpia.

En producción, con sesión real: *Filtrar* sin empresa elegida abre "Falta elegir
la empresa" con el ícono ámbar y un solo botón *Entendido*.

## El autocomplete en producción

Con sesión real (`oscar`), en `/utiles/whatsapp/hallazgos/`:

1. Escribir `ramon` **sin tilde** → matchea **Lezcano Ramón Alejandro**, con
   "Ramón" resaltado.
2. Enter → el `<select>` guarda el valor y el `change` original dispara la carga
   de áreas.
3. Lezcano tiene 1 área (Silvicultura) → 2 opciones, bajo el umbral → **Área
   sigue como select nativo**. Correcto.
4. Forestal Río Claro tiene 7 áreas → el `MutationObserver` autoconvierte el
   `<select>`: queda `class="... an-combo__nativo" data-an-combo="1"
   tabindex="-1" aria-hidden="true"`.
5. Escribir `cosecha` en Área → 4 coincidencias con el fragmento resaltado, y la
   lista **no** la recorta el card.

## Cómo se despliega (para el que venga)

```bash
cd /var/www/an
git pull --ff-only origin main
systemctl restart an.service        # obligatorio: DEBUG=False cachea templates
```

**`collectstatic` NO hace falta.** Nginx sirve los estáticos por alias:

```nginx
location /static/ { alias /var/www/an/static/; }
```

o sea del directorio **fuente**, no de `staticfiles/`. Por eso `staticfiles/`
está viejo y no importa. (Igual: `whitenoise` está instalado en el venv pero no
en `INSTALLED_APPS`.)

## Pendientes

- **Las otras 8 pantallas de acceso siguen con el tema de Colorlib.** El
  proyecto no tiene ningún override de `accounts/` ni `registration/`, y el
  paquete trae: registro, recuperación de contraseña (4 pantallas), cambio de
  contraseña (2) y logout. El patrón ya está probado con el login; falta
  aplicarlo.
- **`home.index` apunta a `pages/index.html`**, que es el Tablero y no una demo
  del vendor. Cuando se buscan restos del tema viejo conviene mirarla: tiene
  gráficos con la paleta de Bootstrap (azules y naranjas) que no siguen el
  design system, y los `<select>` "--Selecciona un cliente--" que hoy no
  convierten a autocomplete porque el usuario solo tiene una empresa asignada.
- **Unificar la versión de `django-admin-datta` entre local y servidor.** Hoy
  son distintas y por eso hacen falta dos overrides para la misma pantalla. Si
  se unifican, `templates/accounts/login.html` queda como el único.
- `TEMPLATE_DIR_DATATB` apunta a `django_dyn_dt/templates`, que **no existe**.
  Entrada muerta en el `DIRS`.
- La pantalla de login tiene un **logo roto** (`/static/assets/images/logo-dark.svg`
  no carga) en la versión vieja; en la nueva usa `logo_almada_neri.png` y se ve
  bien.
- Verificar los combos en las pantallas de Móviles y_SYH_, que tienen many
  selects y no se probaron uno por uno (el componente es global y se verificó
  en la pantalla más difícil).
- De la tanda anterior, siguen igual: `Movimientos.id` con default compartido
  (`syh/models.py:138`); `syh_evidencia.movimiento` varchar(10) vs varchar(20)
  en base nueva; tests de `home` y `moviles` son stubs; `print(resultados)` en
  `syh/models.py:478`.
