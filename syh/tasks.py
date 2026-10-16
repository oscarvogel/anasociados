import os

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from django.conf import settings

from utiles.impresiones import ResumenMensual

logger = get_task_logger(__name__)

# Carpeta dentro de MEDIA_ROOT donde quedan los PDF. El endpoint de descarga
# busca ahi por nombre de archivo: nunca recibe una ruta del navegador.
RESUMENES_DIR = "resumenes"


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=1800,
    soft_time_limit=1500,
)
def task_resumen_mensual(self, cliente_id):
    """Genera el PDF del resumen mensual y devuelve su nombre de archivo.

    El estado se publica con ``update_state`` (lo lee la vista de progreso) y
    el resultado final lo persiste el backend ``django-db``.
    """
    self.update_state(
        state="STARTED",
        meta={
            "current": 0,
            "total": 100,
            "message": "Iniciando procesamiento...",
        },
    )

    nombre_archivo = f"resumen_mensual_{cliente_id}.pdf"
    carpeta = os.path.join(settings.MEDIA_ROOT, RESUMENES_DIR)
    os.makedirs(carpeta, exist_ok=True)

    resumen = ResumenMensual(cliente_id)
    resumen.archivo = os.path.join(carpeta, nombre_archivo)

    try:
        logger.info("Generando resumen mensual para %s", cliente_id)
        resumen.generar_pdf(self)
    except SoftTimeLimitExceeded:
        logger.warning("El resumen mensual de %s excedio el tiempo limite", cliente_id)
        raise
    except Exception:
        logger.exception("Error generando el resumen mensual de %s", cliente_id)
        raise

    return nombre_archivo
