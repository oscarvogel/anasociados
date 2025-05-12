import os
import tempfile
import datetime
import locale
import unicodedata
import re


def getTempFileName(filename='pdf', base=False, extension='.pdf'):
    tf = tempfile.NamedTemporaryFile(prefix=filename, mode='w+b')
    if base:
        return f'{os.path.basename(tf.name)}{extension}'
    return f'{tf.name}{extension}'

def FormatoFecha(fecha: object = datetime.datetime.today(), formato: object = 'largo') -> object:
    # Establecer la configuración que tenga el entorno del usuario
    locale.setlocale(locale.LC_ALL, '')
    retorno = ''
    if isinstance(fecha, (str)):
        retorno = fecha
    else:
        if formato == 'largo':
            retorno = datetime.datetime.strftime(fecha, '%d %b %Y')
        elif formato == 'corto':
            retorno = datetime.datetime.strftime(fecha, '%d-%b')
        elif formato == 'dma':
            retorno = datetime.datetime.strftime(fecha, '%d/%m/%Y')
        elif formato == 'dma_hms':
            retorno = datetime.datetime.strftime(fecha, '%d/%m/%Y %H:%M:%S')
        elif formato == 'dia':
            # Obtener el nombre del día de la semana
            retorno = datetime.datetime.strftime(fecha, "%A")

    return retorno

def dividir_texto(texto, longitud):
    lineas = []
    while len(texto) > longitud:
        espacio = texto.rfind(' ', 0, longitud)
        if espacio == -1:
            espacio = longitud
        lineas.append(texto[:espacio])
        texto = texto[espacio:].strip()
    lineas.append(texto)
    return lineas


def clean_filename(filename):
    """
    Limpia el nombre del archivo para que sea seguro y compatible
    """
    # Normalizar caracteres unicode
    filename = unicodedata.normalize('NFKD', filename)
    # Eliminar caracteres que no sean ASCII
    filename = filename.encode('ASCII', 'ignore').decode('ASCII')
    # Reemplazar espacios y caracteres especiales
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '_', filename).strip('-_')
    return filename