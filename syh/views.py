from email import message
import datetime
from datetime import date
from multiprocessing import context
import os
from venv import logger
import django.utils.timezone
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import models
from django.db.models import Count, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from celery.result import AsyncResult
from django.core.mail import send_mail

from core_an import settings
from syh.serializers import AreaSerializer, ClientesSerializer
from syh.tasks import task_resumen_mensual
from utiles.BaseViewSet import BaseAppModelViewSet
from .models import ExcesosVelocidad
import json

from usuarios.models import AreasProfile, Profile
from utiles.impresiones import ImprimeHallazgos
from django_celery_results.models import TaskResult


from rest_framework import viewsets

# Create your views here.
from .models import Movimientos, Cliente, Area, Evidencia
from rest_framework.pagination import PageNumberPagination

# Hallazgos que siguen abiertos: lo que hay que hacer.
ESTADOS_ABIERTOS = ("Gestión en Curso", "Incumplido")
# Dias por delante que cuentan como "por vencer", igual que el resumen de
# WhatsApp. Si esta pantalla y el mensaje cuentan distinto, se contradicen.
DIAS_POR_VENCER = 5
# Tope del buscador. Es un LIKE sobre varios campos, no un indice.
MAX_TERMINOS_BUSQUEDA = 100
# Cuantos hallazgos se listan por empresa antes de decir "y N mas".
HALLAZGOS_POR_EMPRESA = 8


def _anotar_evidencias(queryset):
    """Cuantas evidencias tiene cada hallazgo y cuantas esperan revision.

    Dos Subquery y no traer las evidencias a memoria: son miles de hallazgos y
    un group-by en Python no escala.
    """
    pendientes = Evidencia.objects.filter(
        movimiento=OuterRef("pk"), estado=Evidencia.ESTADO_PENDIENTE
    )
    return queryset.annotate(
        total_evidencias=Count("evidencia"),
        evidencias_pendientes=Coalesce(
            Subquery(
                pendientes.values("movimiento").annotate(c=Count("pk")).values("c")
            ),
            Value(0),
        ),
    )


def _armar_grupo(empresa, hallazgos, hoy, limite):
    """Arma el bloque de una empresa: sus contadores y sus hallazgos."""
    vencidos, por_vencer = [], []
    limite_vencimiento = hoy + datetime.timedelta(days=DIAS_POR_VENCER)

    for movimiento in hallazgos:
        fecha = movimiento.fecha_cumplimiento
        if fecha and fecha < hoy:
            vencidos.append(movimiento)
        elif fecha and fecha <= limite_vencimiento:
            por_vencer.append(movimiento)

    visibles = vencidos + por_vencer
    return {
        "empresa": empresa,
        "vencidos": len(vencidos),
        "por_vencer": len(por_vencer),
        "por_revisar": sum(1 for m in hallazgos if m.evidencias_pendientes),
        "total": len(hallazgos),
        "hallazgos": visibles[:limite],
        "ocultos": max(0, len(visibles) - limite),
    }


def visualizar_movimientos(request):
    """
    Hallazgos agrupados por empresa, con lo pendiente arriba.

    La pantalla NO es una tabla con filtros del admin. La idea es otra: se
    abre y se ve, primero, cuanto hay pendiente en total y despues una
    seccion por empresa ordenada por urgencia, con sus hallazgos abiertos y
    las fotos a un click. El buscador existe para encontrar algo puntual, no
    para filtrar la tabla.
    """
    try:
        profile = Profile.objects.get(user=request.user)
        cliente = profile.cliente
        areas_profile = AreasProfile.objects.filter(user=request.user)
    except Profile.DoesNotExist:
        cliente = None
        areas_profile = None

    base = Movimientos.objects.select_related("cliente", "area")
    if cliente:
        areas_permitidas = None
        if areas_profile:
            areas_permitidas = [a.area_id for a in areas_profile]
        base = base.filter(cliente_id=cliente.pk)
        if areas_permitidas is not None:
            base = base.filter(area_id__in=areas_permitidas)
    else:
        # Superusuario: puede acotar a una empresa desde la URL.
        empresa = request.GET.get("empresa")
        if empresa:
            base = base.filter(cliente_id=empresa)

    busqueda = (request.GET.get("q") or "").strip()[:MAX_TERMINOS_BUSQUEDA]

    # Con busqueda se mira TODO (incluido lo cumplido), porque si estas
    # buscando algo puntual lo queras encontrar este o no. Sin busqueda, solo
    # lo abierto: lo cerrado es historia, no trabajo.
    if busqueda:
        base = _anotar_evidencias(base).filter(
            Q(hallazgo__icontains=busqueda)
            | Q(responsable__icontains=busqueda)
            | Q(id__icontains=busqueda)
        )
    else:
        base = _anotar_evidencias(base).filter(estado__in=ESTADOS_ABIERTOS)

    base = base.order_by(
        models.F("fecha_cumplimiento").asc(nulls_last=True), "pk"
    )

    hoy = django.utils.timezone.localdate()
    # Con busqueda o con ?todos=1 no se recorta la lista de cada empresa.
    mostrar_todos = busqueda or request.GET.get("todos") == "1"
    limite = 50 if mostrar_todos else HALLAZGOS_POR_EMPRESA

    # Agrupar en memoria es correcto aca: son los hallazgos ABIERTOS los que
    # llegan (unos pocos cientos), no los 1300 historicos.
    por_empresa = {}
    for movimiento in base:
        por_empresa.setdefault(movimiento.cliente_id, []).append(movimiento)

    empresas = {m.cliente_id: m.cliente for m in base}
    grupos = [
        _armar_grupo(empresa, por_empresa[clave], hoy, limite)
        for clave, empresa in empresas.items()
    ]

    # Mas urgente arriba: la que tiene vencidos, despues la que tiene algo por
    # revisar, despues la que mas vence pronto. El nombre desempata.
    grupos.sort(
        key=lambda g: (
            -g["vencidos"],
            -g["por_revisar"],
            -g["por_vencer"],
            g["empresa"].nombre.upper(),
        )
    )
    grupos = [g for g in grupos if g["total"] > 0]

    return render(
        request,
        "pages/syh/visualizar_movimientos.html",
        {
            "grupos": grupos,
            "busqueda": busqueda,
            "total_general": sum(g["total"] for g in grupos),
            "vencidos_general": sum(g["vencidos"] for g in grupos),
            "por_vencer_general": sum(g["por_vencer"] for g in grupos),
            "por_revisar_general": sum(g["por_revisar"] for g in grupos),
            "empresas_con_pendientes": len(grupos),
            "incluye_cerrados": bool(busqueda),
            "mostrar_todos": mostrar_todos,
            "hoy": hoy,
        },
    )


@require_GET
def hallazgo_evidencias(request, movimiento_id):
    """Las evidencias de un hallazgo, para verlas sin entrar al admin."""
    movimiento = Movimientos.objects.filter(pk=movimiento_id).select_related(
        "cliente"
    ).first()
    if movimiento is None:
        return JsonResponse({"error": "El hallazgo no existe."}, status=404)

    if not request.user.is_superuser:
        perfil = Profile.objects.filter(user=request.user).first()
        if perfil is None or movimiento.cliente_id != perfil.cliente_id:
            return JsonResponse({"error": "No corresponde a tu empresa."}, status=403)

    evidencias = Evidencia.objects.filter(movimiento=movimiento).order_by("fecha", "id")
    return JsonResponse({
        "evidencias": [
            {
                "estado": e.estado,
                "estado_legible": e.get_estado_display(),
                "fecha": e.fecha.strftime("%d/%m/%Y"),
                "detalle": e.detalle,
                "subido_por": e.subido_por or "no identificado",
                "revisado_por": e.revisado_por,
                "motivo_rechazo": e.motivo_rechazo,
                "url": e.archivo.url if e.archivo else "",
            }
            for e in evidencias
        ]
    })

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


def api_estados_mensuales(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cliente_id = request.GET.get('cliente')
    area_id = request.GET.get('area')
    fecha_desde_raw = request.GET.get('fecha_desde')
    fecha_hasta_raw = request.GET.get('fecha_hasta')

    def parse_fecha(valor, nombre_parametro):
        if not valor:
            return None
        try:
            return date.fromisoformat(valor)
        except ValueError:
            raise ValueError(f'{nombre_parametro} debe tener formato YYYY-MM-DD')

    try:
        fecha_desde = parse_fecha(fecha_desde_raw, 'fecha_desde')
        fecha_hasta = parse_fecha(fecha_hasta_raw, 'fecha_hasta')
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    if request.user.is_superuser:
        if cliente_id and area_id and not Area.objects.filter(id=area_id, cliente_id=cliente_id).exists():
            return JsonResponse({'error': 'El área no pertenece al cliente seleccionado'}, status=400)
    else:
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return JsonResponse({'error': 'No tiene perfil asociado para consultar este informe'}, status=403)

        cliente_permitido = str(profile.cliente_id)
        if cliente_id and str(cliente_id) != cliente_permitido:
            return JsonResponse({'error': 'No tiene permiso para el cliente seleccionado'}, status=403)

        cliente_id = cliente_permitido

        areas_profile = AreasProfile.objects.filter(user=request.user)
        if areas_profile.exists():
            area_ids_permitidas = set(str(area_pk) for area_pk in areas_profile.values_list('area_id', flat=True))
        else:
            area_ids_permitidas = set(str(area_pk) for area_pk in Area.objects.filter(cliente_id=cliente_id).values_list('id', flat=True))

        if area_id and str(area_id) not in area_ids_permitidas:
            return JsonResponse({'error': 'No tiene permiso para el área seleccionada'}, status=403)

    data = Movimientos.obtener_porcentaje_estados_mensual(
        cliente_id=cliente_id,
        area_id=area_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    return JsonResponse(data)

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
    
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class ClientesViewSet(BaseAppModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClientesSerializer    
    pagination_class = StandardResultsSetPagination
    
class AreasViewSet(BaseAppModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    pagination_class = StandardResultsSetPagination
