import os
import tempfile
import datetime
import locale
from syh.models import ParametroSistema

def obtener_parametro(parametro_deseado, valor_por_defecto):
    try:
        # Intenta obtener el parámetro existente
        parametro = ParametroSistema.objects.get(parametro=parametro_deseado).valor
    except ParametroSistema.DoesNotExist:
        # Si no existe, crea uno nuevo
        parametro = ParametroSistema.objects.create(parametro=parametro_deseado, valor=valor_por_defecto).valor

    return parametro

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
