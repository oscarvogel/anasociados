"""Tags de plantilla de la pantalla de hallazgos.

La pantalla de hallazgos filtra por empresa, area, estado y busqueda, y cada
pastilla es un link que tiene que llevar los OTROS filtros puestos. Escritos a
mano en la plantilla, esos links se desactualizan en cuanto se agrega un
filtro nuevo (por eso el area faltaba: no estaba en ningun link).

`hl_query` arma el link desde los parametros que ya tiene la peticion y
cambia solo lo que se le pasa.
"""

from django import template
from django.http import QueryDict
from django.utils.html import mark_safe

register = template.Library()


def _aplicar(params, cambios):
    """Cambia los parametros de la URL. `None` saca el filtro."""
    for clave, valor in cambios.items():
        if valor is None:
            params.pop(clave, None)
        elif isinstance(valor, (list, tuple)):
            params.setlist(clave, [str(v) for v in valor])
        else:
            params.setlist(clave, [str(valor)])
    return params


@register.simple_tag(takes_context=True)
def hl_query(context, **cambios):
    """
    Link de un filtro de la pantalla de hallazgos.

    Cambia solo lo que se le pasa y el resto de los filtros queda como
    estaban: `{% hl_query empresa=pk %}` cambia la empresa y conserva el area,
    los estados y la busqueda. Con `None` se saca un filtro de la URL.

    Un filtro que puede valer mas de una vez (los estados) se pasa como lista
    y se reemplaza entero.
    """
    peticion = context.get("request")
    params = peticion.GET.copy() if peticion is not None else QueryDict(mutable=True)
    params = _aplicar(params, cambios)

    ruta = peticion.path if peticion is not None else ""
    query = params.urlencode()
    return f"{ruta}?{query}" if query else ruta


@register.simple_tag(takes_context=True)
def hl_query_oculto(context, *claves):
    """
    Los filtros actuales como campos escondidos de un formulario.

    El buscador es un formulario GET: si no lleva los filtros escondidos, al
    buscar se pierde la empresa y el area que estaban elegidas. La busqueda no
    se copia porque el formulario ya tiene su propio campo para eso.
    """
    peticion = context.get("request")
    if peticion is None:
        return ""

    salida = []
    for clave in claves:
        for valor in peticion.GET.getlist(clave):
            salida.append(
                f'<input type="hidden" name="{clave}" value="{valor}">'
            )
    return mark_safe("".join(salida))
