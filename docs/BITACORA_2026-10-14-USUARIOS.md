# Bitácora — 14/10/2026 (cuarta tanda): el check de "Cuenta habilitada" no guardaba

## Qué se hizo

Un bug reportado desde la pantalla de Gestión de usuarios: al desmarcar **Cuenta
habilitada** y tocar *Guardar usuario*, la cuenta quedaba como estaba. Se
investigó contra la base de pruebas y se corrigió.

Archivos tocados:

- `usuarios/management_forms.py`
- `usuarios/views.py`
- `templates/pages/usuarios/management_user_form.html`
- `usuarios/tests.py` (nuevo: la app no tenía ningún test)

## El bug

**No era el checkbox.** `is_active` se guardaba bien. Lo que pasaba es otra cosa:

El campo **Empresa** (`cliente`) era obligatorio, y el `user_form.is_valid()` da
`False` si falta. Cuando el usuario no tiene empresa asignada —o sea, sin fila
en `perfiles`— el formulario se abría con *Empresa* vacío y el operador tenía que
elegir una. Si deshabilitaba la cuenta y guardaba sin elegir empresa, el POST
era inválido, **no se guardaba nada** y la pantalla volvía con el error
"Este campo es requerido".

El operador veía su checkbox desmarcado, el error rojo de empresa, y lo
natural era concluir que el checkbox no se guardaba. El cambio de estado se
perdía **en silencio**: no porque `is_active` estuviera roto, sino porque el
formulario entero se rechazaba y él no sabía por qué.

Esto es especialmente tramposo porque una cuenta dada de alta en Admin sin
perfil queda sin empresa, y es justo el caso de las cuentas nuevas.

## El arreglo

Empresa pasa a ser **opcional**, con la semántica de "no la quiero cambiar":

- `cliente` es `required=False` con texto de ayuda que lo dice explícito.
- Si viene vacía, **no se borra el perfil existente**: se conserva. Antes
  `Profile.objects.update_or_create()` con `cliente=None` habría fallado por la
  FK; ahora la llamada solo se hace cuando hay empresa elegida.
- Si el usuario nunca tuvo perfil, sigue sin perfil. No se inventa uno: la
  tabla `perfiles` es preexistente y `managed = False`.

Para las áreas hay que tener cuidado, porque `AreaAssignmentFormSet` se
construye con `form_kwargs={"cliente": ...}` y **sin empresa el queryset de
áreas queda vacío**. Eso, al guardar, borraba las asignaciones que el usuario ya
tenía. Por eso:

- `empresa_para_areas = selected_client or empresa_del_perfil`: el formset se
  arma con la empresa elegida o, si no hay, con la que ya tenía el usuario.
- El borrado final de asignaciones retiradas solo corre si hay empresa. Sin
  empresa no se puede agregar ni quitar áreas, pero tampoco se pierde nada.

## Cómo se verificó

Contra **MySQL de pruebas** (`an_test` en WSL, puerto 3307), no contra SQLite ni
contra producción. Verificado antes de correr que el proceso apuntaba a
`an_test` y no a la base real.

`usuarios/tests.py`, 5 tests:

| Test | Qué fija |
|---|---|
| `test_desmarcar_cuenta_habilitada_se_guarda` | el gesto reportado: desmarcar y guardar |
| `test_marcar_cuenta_habilitada_se_guarda` | el caso inverso, para no obtener un verde falso |
| `test_deshabilitar_sin_elegir_empresa_se_guarda` | el bug: estado cambia sin empresa |
| `test_deshabilitar_sin_elegir_empresa_no_crea_perfil` | no se inventa perfil |
| `test_editar_con_empresa_conserva_areas_y_perfil` | no-regresión: empresa vacía no borra áreas ni perfil |

El segundo test existe por una razón concreta: un checkbox desmarcado **no viaja
en el POST**. Un test que solo cubriera ese caso pasaría aunque el campo no se
guardara nunca. Por eso se prueban los dos sentidos.

Suite completa: `utiles` 33 OK, `syh` 37 OK, `usuarios` 5 OK. `home` y `moviles`
siguen sin tests (0). El runner raíz (`manage.py test` sin etiqueta) encuentra 0
tests: hay que pasar la app.

## Un detalle encontrado de paso

`Cliente.id` y `Area.id` son `CharField(primary_key=True, max_length=10)` **sin
default**. `Cliente.objects.create(nombre="X")` los deja en `''`, no falla, y
después todo `ModelChoiceField` responde "Este campo es requerido" porque el
valor enviado no coincide con ninguna opción. Si se escriben tests para estas
apps, hay que pasar `id=` explícito.

## Cómo se deshabilita una cuenta mientras tanto

Como salida alternativa, `User` sigue registrado en Django Admin
(`/admin/auth/user/<id>/change/`), con su checkbox "Activo". El plan de diseño lo
deja como acceso de respaldo a propósito, así que no lo toqué.

## Pendientes

- **El mismo problema en el alta de usuario nuevo**: si se crea sin empresa, el
  `password1` sigue siendo obligatorio y el perfil tampoco se crea. Coherente,
  pero conviene decidir si una cuenta puede existir sin empresa o si hay que
  exigírsela en algún momento.
- **Mensaje de error más claro** cuando el formulario no guarda: hoy el operador
  tiene que inferir que no se guardó nada. Un aviso del tipo "no se guardó nada,
  revisá los campos marcados" evitaría la confusión de este bug.
- **La lista de usuarios** (`management_users.html`) no tiene acción para
  cambiar el estado; hay que entrar al editor. Con el fix ya no rompe, pero sigue
  siendo un paso de más.
- `home` y `moviles` siguen sin ningún test.