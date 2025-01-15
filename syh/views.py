from email import message
from multiprocessing import context
import os
from venv import logger
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from celery.result import AsyncResult
from django.core.mail import send_mail

from core_an import settings
from syh.serializers import ClientesSerializer
from syh.tasks import task_resumen_mensual
from .models import ExcesosVelocidad
import json

from usuarios.models import AreasProfile, Profile
from utiles.impresiones import ImprimeHallazgos
from django_celery_results.models import TaskResult


from rest_framework import viewsets

# Create your views here.
from .models import Movimientos, Cliente, Area

def visualizar_movimientos(request):

    try:
        profile = Profile.objects.get(user=request.user)
        cliente = profile.cliente  # Obtener el cliente asociado al perfil
        areas_profile = AreasProfile.objects.filter(user=request.user)
    except Profile.DoesNotExist:
        # Si no tiene un perfil, puedes manejar el caso con un mensaje de error o redirección
        cliente = None
        areas_profile = None
    
    if cliente:
        clientes = Cliente.objects.filter(id = cliente.id)
        if not areas_profile:
            areas = Area.objects.filter(cliente = cliente.id)
        else:
            areas = Area.objects.filter(id__in=[area.area.id for area in areas_profile])
        queryset = Movimientos.objects.filter(cliente = cliente.id)
    else:
        clientes = Cliente.objects.all()
        areas = Area.objects.all()
        queryset = Movimientos.objects.all()


    estados = ['Gestión en Curso', 'Cumplido', 'Incumplido', 'Cerrado']

    filtro_cliente = request.GET.get('cliente')
    filtro_area = request.GET.get('area')
    filtro_estados = request.GET.getlist('estado')

    if filtro_cliente:
        queryset = queryset.filter(cliente_id=filtro_cliente)
    
    if filtro_area:
        queryset = queryset.filter(area_id=filtro_area)

    if filtro_estados:
        queryset = queryset.filter(estado__in=filtro_estados)

    paginator = Paginator(queryset, 10)  # 10 elementos por página
    page = request.GET.get('page', 1)
    
    try:
        movimientos = paginator.page(page)
    except PageNotAnInteger:
        movimientos = paginator.page(1)
    except EmptyPage:
        movimientos = paginator.page(paginator.num_pages)
    
    # Crear el rango de páginas para la paginación
    index = movimientos.number - 1  # Page index starts from 0
    max_index = len(paginator.page_range)
    start_index = index - 2 if index >= 2 else 0
    end_index = index + 3 if index <= max_index - 3 else max_index
    page_range = paginator.page_range[start_index:end_index]
    context = {
        'clientes': clientes,
        'areas': areas,
        'estados': estados,
        'movimientos': movimientos,
        'page_range': page_range,  # Añadir el rango de páginas al contexto
        'filtro_estados': filtro_estados
    }
    return render(request, 'pages/syh/visualizar_movimientos.html', context)

def imprimir_movimientos(request):
    
    filtro_cliente = request.GET.get('cliente', None)
    filtro_area = request.GET.get('area', None)
    filtro_estados = request.GET.getlist('estado', None)

    queryset = Movimientos.objects.all()

    if filtro_cliente:
        queryset = queryset.filter(cliente=filtro_cliente)
    
    if filtro_area:
        queryset = queryset.filter(area=filtro_area)

    if filtro_estados:
        queryset = queryset.filter(estado__in=filtro_estados)

    print(queryset.query)    
    # Si el queryset está vacío, redirigir a la vista 'visualizar_movimientos'
    if not queryset.exists():
        return redirect('syh:visualizar_movimientos')

    queryset = queryset.order_by('-estado', '-fecha')
    impresion = ImprimeHallazgos()
    return impresion.imprime_hallazgo(queryset=queryset, filtro_cliente=filtro_cliente, filtro_area=filtro_area)
        


def obtener_areas(request):
    cliente_id = request.GET.get('cliente')
    if not request.user.is_superuser:
        areas_profile = AreasProfile.objects.filter(user=request.user)
    else:
        areas_profile = None
    
    if cliente_id:
        if not areas_profile:
            areas = Area.objects.filter(cliente_id=cliente_id)
        else:
            areas = Area.objects.filter(id__in=[area.area.id for area in areas_profile])
    else:
        areas = Area.objects.all()
    areas_data = {area.id: area.detalle for area in areas}
    return JsonResponse(areas_data)

def obtener_areas_vue(request):
    cliente_id = request.GET.get('cliente')
    print(cliente_id)
    if cliente_id:
        areas = Area.objects.filter(cliente=cliente_id).values('id', 'detalle')
    else:
        areas = []
    print(areas)
    return JsonResponse(list(areas), safe=False)

@csrf_exempt
def excesos_list(request):

    if request.method == 'GET':

        if request.user.is_superuser:
            cliente = None
        else:
            try:
                profile = Profile.objects.get(user=request.user)
                cliente = profile.cliente  # Obtener el cliente asociado al perfil
            except Profile.DoesNotExist:
                # Si no tiene un perfil, puedes manejar el caso con un mensaje de error o redirección
                cliente = None
    
        excesos = list(ExcesosVelocidad.objects.all().values('id', 'cliente', 'anio', 'mes','excesos', 'cliente__nombre',)[:100])
        if cliente:
            excesos = list(ExcesosVelocidad.objects.filter(cliente=cliente.id).values('id', 'cliente', 'anio', 'mes','excesos', 'cliente__nombre',)[:100])
            
        return JsonResponse(excesos, safe=False)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(data)
            exceso = ExcesosVelocidad.objects.create(
                cliente_id=data['cliente'],
                anio=data['anio'],
                mes=data['mes'],
                excesos=data['excesos']
            )
            return JsonResponse({'id': exceso.id}, status=201)
        except Exception as e:
            print(e)
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def excesos_detail(request, id):
    try:
        exceso = ExcesosVelocidad.objects.get(id=id)
    except ExcesosVelocidad.DoesNotExist:
        return JsonResponse({'error': 'No encontrado'}, status=404)

    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            exceso.cliente_id = data['cliente']
            exceso.anio = data['anio']
            exceso.mes = data['mes']
            exceso.excesos = data['excesos']
            exceso.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        exceso.delete()
        return JsonResponse({'success': True})


def clientes_list(request):
    # Consultamos todos los clientes y seleccionamos los campos que queremos enviar como JSON
    clientes = Cliente.objects.all().values('id', 'nombre', 'celular', 'email')
    
    # Convertimos el QuerySet en una lista y devolvemos una respuesta JSON
    return JsonResponse(list(clientes), safe=False)

def excesos_plantilla(request):
    return render(request, 'pages/syh/excesos_velocidad.html')

def plantilla_resumen_mensual(request):
    try:
        profile = Profile.objects.get(user=request.user)
        cliente = profile.cliente  # Obtener el cliente asociado al perfil
        cliente_id = cliente.id
    except Profile.DoesNotExist:
        # Si no tiene un perfil, puedes manejar el caso con un mensaje de error o redirección
        cliente = None
    
    if request.user.is_superuser:
        cliente = 'Todos'
        nombre = 'Todos los clientes'
        cliente_id = request.GET.get('cliente', None)
    else:
        nombre = cliente.nombre
    if cliente == 'Todos':
        clientes = Cliente.objects.all()
    else:
        clientes = Cliente.objects.filter(id = cliente_id)

    context = {
        'segment'  : 'resumen_mensual',
        'cliente': nombre,
        'clientes': clientes,
        'cliente_id_selected': cliente_id,
    }
    return render(request, 
                  'pages/syh/resumen_mensual.html', context=context)

#genera resumen mensual
def generar_resumen(request):
    cliente_id = request.GET.get('cliente', None)

    task = task_resumen_mensual.delay(cliente_id)
    return JsonResponse({'task_id': task.id})

def progreso_tarea(request, task_id):
    try:
        # Primero intentar obtener el resultado de la base de datos
        try:
            print(f'Tratando de obtener el resultado de la tarea {task_id} desde la base de datos')
            task_result = TaskResult.objects.get(task_id=task_id)
            stored_result = json.loads(task_result.result) if task_result.result else {}
            
            # Si se obtuvo el resultado, devolverlo
            response = {
                'task_id': task_id,
                'state': task_result.status,
                'status': 'success'
            }
            print(response)

            if isinstance(stored_result, dict):
                response.update({
                    'current': stored_result.get('current', 0),
                    'total': stored_result.get('total', 100),
                    'message': stored_result.get('message', 'Procesando...')
                })
            else:
                response.update({
                    'pdf_file': stored_result,
                    'message': 'Tarea finalizada exitosamente'
                })
                stored_result = response
            # return result
            return JsonResponse(stored_result)
            
        except TaskResult.DoesNotExist:
            # Si no está en la base de datos, usar AsyncResult
            result = AsyncResult(task_id)
            
            response = {
                'task_id': task_id,
                'state': result.state,
                'status': 'success'
            }
            
            if result.state == 'PROGRESS' and result.info:
                response.update(result.info)
            elif result.state == 'SUCCESS':
                response.update({
                    'current': 100,
                    'total': 100,
                    'message': 'Tarea completada'
                })
            elif result.state == 'FAILURE':
                response.update({
                    'state': 'FAILURE',
                    'status': 'error',
                    'message': str(result.info)
                })
            else:
                response.update({
                    'current': 0,
                    'total': 100,
                    'message': 'Tarea en proceso'
                })
            
            return JsonResponse(response)
            
    except Exception as e:
        logger.error(f"Error al verificar progreso: {str(e)}")
        return JsonResponse({
            'state': 'ERROR',
            'status': 'error',
            'message': str(e)
        })
    
def download_file(request, filename):
    # Construir la ruta completa del archivo en el directorio MEDIA_ROOT
    # file_path = os.path.join(settings.MEDIA_ROOT, filename)
    file_path = filename
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    else:
        return HttpResponse("Archivo no encontrado", status=404)
    
    

class ClientesViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClientesSerializer    