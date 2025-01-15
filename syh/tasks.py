from venv import logger
from celery import shared_task
import os, json
from celery.signals import task_prerun, task_postrun
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django_celery_results.models import TaskResult
from utiles.impresiones import ResumenMensual


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Guarda el estado inicial de la tarea"""
    logger.info(f'Iniciando tarea {task_id}')
    TaskResult.objects.update_or_create(
        task_id=task_id,
        defaults={
            'status': 'STARTED',
            'result': json.dumps({
                'current': 0,
                'total': 100,
                'message': 'Iniciando tarea...'
            })
        }
    )

# @task_postrun.connect
# def task_postrun_handler(task_id, task, *args, **kwargs):
#     """Guarda el estado final de la tarea"""
#     logger.info(f'Terminando tarea {task_id}')
#     TaskResult.objects.update_or_create(
#         task_id=task_id,
#         defaults={
#             'status': 'SUCCESS',
#             'result': json.dumps({
#                 'current': 100,
#                 'total': 100,
#                 'message': 'Tarea finalizada exitosamente'
#             })
#         }
#     )

@shared_task(bind=True,
             acks_late=True,
             reject_on_worker_lost=True,
             time_limit=1800,
             soft_time_limit=1500)
def task_resumen_mensual(self, cliente_id):
    try:
        # Inicializar la tarea
        self.update_state(
                state='STARTED',
                meta={
                    'current': 0,
                    'total': 0,
                    'message': 'Iniciando procesamiento...'
                }
            )
        resumen = ResumenMensual(cliente_id)
        resumen.archivo = f'resumen_mensual_{cliente_id}.pdf'
        print(f'Generando resumen mensual para {cliente_id}')
        pdf_file = resumen.generar_pdf(self)

        progress = {
            'cliente_id': cliente_id, 
            'pdf_path': resumen.archivo
        }
        # También actualizar en la base de datos
        TaskResult.objects.filter(task_id=self.request.id).update(
            status='SUCCESS',
            result=json.dumps(progress)
        )
        # Generar PDF 
        # Marcar tarea como completada 
        self.update_state(state='SUCCESS', meta={'cliente_id': cliente_id, 'pdf_file': resumen.archivo}) 
        return resumen.archivo
        # return ResumenMensual(cliente_id).generar_pdf()

    except SoftTimeLimitExceeded:
        logger.warning('Task timed out', exc_info=True)
    except Exception as e:
        logger.error(f"Error generando informe: {str(e)}")
        raise
    finally:
        self.update_state(state='SUCCESS', meta={'cliente_id': cliente_id, 'pdf_file': resumen.archivo})