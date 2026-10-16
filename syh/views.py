from email import message
import datetime
from datetime import date
from multiprocessing import context
import os
import django.utils.timezone
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import models
from django.db.models import Count, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
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


from rest_framework import viewsets

# Create your views here.
from .models import Movimientos, Cliente, Area, Evidencia
from rest_framework.pagination import PageNumberPagination

# Hallazgos que siguen abiertos: lo que hay que hacer.
ESTADOS_ABIERTOS = ("Gestión en Curso", "Incumplido")
# Todos los estados que el filtro acepta. "Cerrado" existe en la vista vieja
# pero el modelo no lo tiene en sus choices: se acepta igual por si hay
# filas viejas con ese texto.
ESTADOS_VALIDOS = ("Gestión en Curso", "Incumplido", "Cumplido", "Cerrado")
# Que franja de la lista se esta mostrando.
VISTAS_VALIDAS = ("pendientes", "vencidos", "por_vencer", "por_revisar", "todos")
# Dias por delante que cuentan como "por vencer", igual que el resumen de
# WhatsApp. Si esta pantalla y el mensaje cuentan distinto, se contradicen.
DIAS_POR_VENCER = 5
# Tope del buscador. Es un LIKE sobre varios campos, no un indice.
MAX_TERMINOS_BUSQUEDA = 100
# Cuantos hallazgos se listan por empresa antes de decir "y N mas".
HALLAZGOS_POR_EMPRESA = 8


def _empresas_visibles(cliente, areas_profile):
    """Empresas que el usuario puede ver, para el selector de empresa."""
    consulta = Cliente.objects.all()
    if cliente:
        consulta = consulta.filter(pk=cliente.pk)
    if areas_profile:
        ids = {a.area.cliente_id for a in areas_profile if a.area_id}
        if ids:
            consulta = consulta.filter(pk__in=ids)
    return {c.pk: c for c in consulta.order_by("nombre")}


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


def _armar_grupo(empresa, hallazgos, hoy, limite, vista):
    """
    Arma el bloque de una empresa: sus contadores y sus hallazgos.

    `vista` decide que se lista:
      - "pendientes" (default): los vencidos y los que vencen en los proximos
        dias. Es el trabajo del momento.
      - "vencidos" / "por_vencer": solo esa franja.
      - "por_revisar": solo los que tienen evidencia esperando.
      - "todos": todo lo que llego, sin recortar por fecha.
    Los contadores se calculan SIEMPRE sobre el grupo completo, no sobre la
    vista: si no, al filtrar por "vencidos" el contador de vencidos daria 0.
    """
    vencidos, por_vencer, por_revisar, otros = [], [], [], []
    limite_vencimiento = hoy + datetime.timedelta(days=DIAS_POR_VENCER)

    for movimiento in hallazgos:
        fecha = movimiento.fecha_cumplimiento
        if fecha and fecha < hoy:
            vencidos.append(movimiento)
        elif fecha and fecha <= limite_vencimiento:
            por_vencer.append(movimiento)
        else:
            otros.append(movimiento)
        if movimiento.evidencias_pendientes:
            por_revisar.append(movimiento)

    if vista == "vencidos":
        visibles = vencidos
    elif vista == "por_vencer":
        visibles = por_vencer
    elif vista == "por_revisar":
        visibles = por_revisar
    elif vista == "todos":
        visibles = hallazgos
    else:
        visibles = vencidos + por_vencer + otros

    return {
        "empresa": empresa,
        "vencidos": len(vencidos),
        "por_vencer": len(por_vencer),
        "por_revisar": len(por_revisar),
        "total": len(hallazgos),
        # Cuantos hay realmente en la lista que se esta viendo. Los contadores
        # de arriba NO cambian con el filtro: si cambiaran, filtrar por
        # "vencidos" dejaria el contador de vencidos en cero.
        "visibles": len(visibles),
        "hallazgos": visibles[:limite],
        "ocultos": max(0, len(visibles) - limite),
    }


@login_required
def visualizar_movimientos(request):
    """
    Hallazgos agrupados por empresa, con lo pendiente arriba.

    La idea es otra que la del admin: se abre y se ve, primero, cuanto hay
    pendiente en total y despues una seccion por empresa ordenada por
    urgencia. Los filtros son los mismos que se necesite (empresa, estado),
    pero son links y no una barra con boton "Aplicar".

    `login_required` no es cosmetico: sin el, un usuario anonimo hacia
    `Profile.objects.get(user=AnonymousUser)`, que tira TypeError (no
    Profile.DoesNotExist) y el except no lo agarraba. La pagina daba 500.
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

    # --- filtros -------------------------------------------------------
    empresa_sel = (request.GET.get("empresa") or "").strip()
    if empresa_sel and not cliente:
        # Solo el superusuario puede ver otra empresa que la suya.
        base = base.filter(cliente_id=empresa_sel)

    busqueda = (request.GET.get("q") or "").strip()[:MAX_TERMINOS_BUSQUEDA]

    estados_sel = [e for e in request.GET.getlist("estado") if e in ESTADOS_VALIDOS]
    if estados_sel:
        base = base.filter(estado__in=estados_sel)
    elif not busqueda:
        # Sin filtro elegido se muestran los abiertos: lo cerrado es historia.
        # Pero si estas BUSCANDO algo puntual, el termino manda: si escribiste
        # el nombre de algo cerrado es porque lo queres encontrar.
        base = base.filter(estado__in=ESTADOS_ABIERTOS)

    if busqueda:
        base = base.filter(
            Q(hallazgo__icontains=busqueda)
            | Q(responsable__icontains=busqueda)
            | Q(id__icontains=busqueda)
        )

    base = _anotar_evidencias(base).order_by(
        models.F("fecha_cumplimiento").asc(nulls_last=True), "pk"
    )

    vista = request.GET.get("vista") or "pendientes"
    if vista not in VISTAS_VALIDAS:
        vista = "pendientes"

    hoy = django.utils.timezone.localdate()
    mostrar_todos = busqueda or request.GET.get("todos") == "1"
    limite = 50 if mostrar_todos else HALLAZGOS_POR_EMPRESA

    # Agrupar en memoria es correcto aca: son los hallazgos ABIERTOS los que
    # llegan (unos pocos cientos), no los 1300 historicos.
    por_empresa = {}
    for movimiento in base:
        por_empresa.setdefault(movimiento.cliente_id, []).append(movimiento)

    empresas_disponibles = _empresas_visibles(cliente, areas_profile)

    grupos = [
        _armar_grupo(empresa, por_empresa[clave], hoy, limite, vista)
        for clave, empresa in empresas_disponibles.items()
        if clave in por_empresa
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

    return render(
        request,
        "pages/syh/visualizar_movimientos.html",
        {
            "grupos": grupos,
            # El sidebar lo usa para resaltar el item de menu activo. Sin esto
            # el link "Hallazgos" nunca se marca, que es lo que pasaba antes.
            "segment": "hallazgos",
            "busqueda": busqueda,
            "total_general": sum(g["visibles"] for g in grupos),
            "vencidos_general": sum(g["vencidos"] for g in grupos),
            "por_vencer_general": sum(g["por_vencer"] for g in grupos),
            "por_revisar_general": sum(g["por_revisar"] for g in grupos),
            "empresas_con_pendientes": len(grupos),
            "mostrar_todos": mostrar_todos,
            "hoy": hoy,
            # Lo que se esta filtrando, para que la pantalla muestre en que
            # estado esta y se pueda volver a cero.
            "vista": vista,
            "vistas": VISTAS_VALIDAS,
            "empresa_sel": empresa_sel,
            "empresas_disponibles": empresas_disponibles,
            "estados_sel": estados_sel,
            "estados_disponibles": ESTADOS_VALIDOS,
            "estados_abiertos": list(ESTADOS_ABIERTOS),
        },
    )


def _hallazgo_permitido(request, movimiento_id):
    """El hallazgo, si el usuario puede tocarlo. Si no, None.

    Mismo corte que la vista: un usuario de una empresa no edita hallazgos de
    otra aunque adivine el id.
    """
    movimiento = Movimientos.objects.filter(pk=movimiento_id).first()
    if movimiento is None:
        return None
    if not request.user.is_superuser:
        perfil = Profile.objects.filter(user=request.user).first()
        if perfil is None or movimiento.cliente_id != perfil.cliente_id:
            return None
    return movimiento


@require_POST
@login_required
def hallazgo_actualizar(request, movimiento_id):
    """
    Edita un hallazgo desde la pantalla de trabajo.

    Se puede cambiar estado, responsable, fecha de vencimiento y la
    observacion. Si se marca como Cumplido y no tiene fecha de realizado, se
    pone la de hoy: un hallazgo cerrado sin fecha de cuando se hizo no sirve
    para el resumen mensual.

    Va con CSRF porque es un usuario logueado en su sesion; el enlace publico
    de evidencias es el caso distinto, y ese si va sin CSRF a proposito.
    """
    movimiento = _hallazgo_permitido(request, movimiento_id)
    if movimiento is None:
        return JsonResponse({"error": "Ese hallazgo no te corresponde."}, status=404)

    campos = []
    # Solo se toca lo que VINO en el POST. Si no, un envio vacio borraria el
    # responsable y las observaciones: el formulario manda siempre los campos,
    # pero una llamada a medias no deberia vaciar nada.
    if "estado" in request.POST:
        estado = request.POST["estado"].strip()
        if estado and estado not in ESTADOS_VALIDOS:
            return JsonResponse({"error": "Ese estado no existe."}, status=400)
        if estado:
            movimiento.estado = estado
            campos.append("estado")
            if estado == "Cumplido" and not movimiento.fecha_realizado:
                movimiento.fecha_realizado = django.utils.timezone.localdate()
                campos.append("fecha_realizado")

    if "responsable" in request.POST:
        responsable = request.POST["responsable"].strip()
        if responsable != movimiento.responsable:
            movimiento.responsable = responsable
            campos.append("responsable")

    if "fecha_cumplimiento" in request.POST:
        fecha = request.POST["fecha_cumplimiento"].strip()
        if fecha:
            try:
                movimiento.fecha_cumplimiento = datetime.date.fromisoformat(fecha)
                campos.append("fecha_cumplimiento")
            except ValueError:
                return JsonResponse({"error": "La fecha no es válida."}, status=400)

    if "observaciones" in request.POST:
        observaciones = request.POST["observaciones"].strip()
        if observaciones != (movimiento.observaciones or ""):
            movimiento.observaciones = observaciones
            campos.append("observaciones")

    if not campos:
        return JsonResponse({"error": "No cambió nada."}, status=400)

    movimiento.save(update_fields=campos)
    return JsonResponse({"ok": True, "estado": movimiento.estado})


@require_GET
@login_required
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

@login_required
def plantilla_resumen_mensual(request):
    """Pantalla del resumen mensual: elige el cliente y dispara la tarea."""
    if request.user.is_superuser:
        clientes = Cliente.objects.all().order_by('nombre')
        cliente_id_selected = request.GET.get('cliente') or None
    else:
        perfil = Profile.objects.filter(user=request.user).select_related('cliente').first()
        cliente = perfil.cliente if perfil else None
        if cliente is None:
            # Sin perfil no hay cliente que resumir: el combo queda vacio y el
            # boton avisa. Antes esta rama reventaba con AttributeError.
            clientes = Cliente.objects.none()
            cliente_id_selected = None
        else:
            clientes = Cliente.objects.filter(pk=cliente.pk)
            cliente_id_selected = cliente.id

    context = {
        'segment': 'resumen_mensual',
        'clientes': clientes,
        'cliente_id_selected': cliente_id_selected,
    }
    return render(request, 'pages/syh/resumen_mensual.html', context=context)


# Genera el resumen mensual de un cliente en segundo plano (Celery).
@login_required
def generar_resumen(request):
    cliente_id = request.GET.get('cliente')
    if not cliente_id:
        return JsonResponse({'error': 'Selecciona un cliente'}, status=400)
    if not Cliente.objects.filter(pk=cliente_id).exists():
        return JsonResponse({'error': 'El cliente no existe'}, status=404)

    task = task_resumen_mensual.delay(cliente_id)
    return JsonResponse({'task_id': task.id})

@login_required
def progreso_tarea(request, task_id):
    """Estado de la tarea, siempre con la misma forma.

    El backend de resultados es ``django-db``, asi que ``AsyncResult`` lee el
    mismo registro que antes se consultaba a mano. Devolvemos siempre ``state``
    para que el front no tenga que adivinar (antes faltaba y el polling se
    quedaba girando para siempre).
    """
    result = AsyncResult(task_id)
    estado = result.state

    payload = {'task_id': task_id, 'state': estado}

    if estado == 'SUCCESS':
        salida = result.result
        pdf_file = salida.get('pdf_file') if isinstance(salida, dict) else salida
        payload.update({
            'current': 100,
            'total': 100,
            'message': 'Tarea completada',
            'pdf_file': pdf_file,
        })
    elif estado == 'FAILURE':
        payload.update({
            'status': 'error',
            'message': str(result.info),
        })
    elif estado in ('PROGRESS', 'STARTED') and isinstance(result.info, dict):
        info = result.info
        payload.update({
            'current': info.get('current', 0),
            'total': info.get('total') or 100,
            'message': info.get('message', 'Procesando...'),
        })
    else:
        payload.update({
            'current': 0,
            'total': 100,
            'message': 'En espera...',
        })

    return JsonResponse(payload)


@login_required
def download_file(request, filename):
    # El navegador manda solo el nombre del archivo: lo resolvemos SIEMPRE
    # dentro de MEDIA_ROOT/resumenes para que no se pueda pedir otra ruta.
    nombre = os.path.basename(filename)
    file_path = os.path.join(settings.MEDIA_ROOT, 'resumenes', nombre)

    if os.path.exists(file_path):
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=nombre,
            content_type='application/pdf',
        )
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
