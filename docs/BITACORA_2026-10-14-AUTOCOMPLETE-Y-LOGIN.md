# Bitácora — 14/10/2026 (quinta tanda): combos con autocomplete y el login del portal

## Qué se hizo

Dos cosas, una pedido y una que apareció en el medio:

1. Todos los `<select>` de la app pasaron a ser **autocomplete con filtro**.
2. El **login del portal** seguía mostrando el tema viejo de Colorlib. Se
   arregló en el camino.

Commits: `adfaf1a` (autocomplete) y `070646e` (login).

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
