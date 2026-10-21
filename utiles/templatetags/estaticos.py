"""Estaticos con la version del archivo en la URL.

Nginx sirve los estaticos por alias al directorio fuente y no manda
Cache-Control. El navegador entonces guarda el CSS con la heuristica del 10%
sobre la antiguedad del archivo: como el CSS hacia dias que no cambiaba, la
vencimiento daba por horas o por dias. Despues de un despliegue, el celular
seguia viendo la version anterior.

Es lo que paso con el boton de menu del celular: el servidor ya servia el
archivo nuevo y el telefono seguia sin ver las rayas, porque tenia la version
vieja cacheada. Con la version en la URL, cada cambio de archivo es una URL
nueva y el navegador no la tiene guardada.
"""

import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()


def _ruta_en_disco(path):
    """
    Donde esta el archivo en el disco, o None si no se encuentra.

    Se busca con los finders (que recorren STATICFILES_DIRS) y no con
    `staticfiles_storage.path()`: esa apunta a STATIC_ROOT, que es una copia
    vieja de collectstatic y no tiene los archivos del proyecto. Con los
    finders sale el archivo de fuente, que es el que sirve Nginx por alias.
    """
    encontrado = finders.find(path)
    if encontrado:
        return encontrado
    try:
        ruta = staticfiles_storage.path(path)
    except (NotImplementedError, ValueError):
        return None
    return ruta if os.path.exists(ruta) else None


@register.simple_tag
def estatico(path):
    """La URL de un estatico con la version del archivo encima.

    Se usa como {% static %} pero agregando ?v=<mtime>. El mtime cambia con
    cada despliegue, asi que el archivo nuevo siempre se descarga.
    """
    url = staticfiles_storage.url(path)
    ruta = _ruta_en_disco(path)
    if not ruta:
        return url
    try:
        version = int(os.path.getmtime(ruta))
    except OSError:
        return url
    return f"{url}?v={version}"


@register.simple_tag
def archivo_estatico(path):
    """Ruta en disco de un estatico, para diagnostos y tests."""
    return _ruta_en_disco(path) or os.path.join(settings.BASE_DIR, "static", path)
