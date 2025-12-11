from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from rest_framework.response import Response
from django.db.models import Sum
import django.db.models as models
from django.http import JsonResponse
from datetime import datetime, timedelta
from rest_framework.generics import ListAPIView
from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
import io

# Create your views here.
from moviles.serializer import CargaCombustibleSerializer, CentroCostosSerializer, GastosMovilSerializer, MatafuegosSerializer, MovilSerializer, PersonalSerializer, TipoVencimientosSerializer, VencimientosSerializer
from rest_framework import filters

from syh.models import Area, Cliente
from utiles.BaseViewSet import BaseAppModelViewSet
from .models import CargaCombustible, CentroCostos, GastosMovil, Matafuegos, Movil, Personal, TipoVencimientos, Vencimientos
from .models import Viajes, Predios
from .serializer import ViajesSerializer, PrediosSerializer
from rest_framework.decorators import api_view
from django.http import HttpResponse
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter


class MovilViewSet(BaseAppModelViewSet):
    queryset = Movil.objects.all()
    serializer_class = MovilSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['patente', 'empresa__nombre']  # Asegúrate de que 'nombre' es el campo correcto en el modelo 'Clientes'
    ordering_fields = ['patente']
    ordering = ['patente']
    

class TipoVencimientosViewSet(BaseAppModelViewSet):
    queryset = TipoVencimientos.objects.all()
    serializer_class = TipoVencimientosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'tipo']  # Asegúrate de que 'nombre' y 'tipo' son los campos correctos en el modelo 'TipoVencimientos'
    ordering_fields = ['nombre']

class VencimientosViewSet(BaseAppModelViewSet):
    queryset = Vencimientos.objects.all()
    serializer_class = VencimientosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['movil__patente', 'tipo_vencimiento__nombre', 'detalle']  # Asegúrate de que 'patente', 'nombre' y 'detalle' son los campos correctos en los modelos 'Movil' y 'TipoVencimientos'
    ordering_fields = ['-fecha', 'tipo_vencimiento']

class PersonalViewSet(BaseAppModelViewSet):
    queryset = Personal.objects.all()
    serializer_class = PersonalSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'apellido', 'empresa__nombre']  # Asegúrate de que 'nombre', 'apellido' y 'dni' son los campos correctos en el modelo 'Personal'
    ordering_fields = ['nombre', 'apellido']
    
class CargaCombustibleViewSet(BaseAppModelViewSet):
    queryset = CargaCombustible.objects.all()
    serializer_class = CargaCombustibleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['movil__patente', 'chofer__nombre', 'chofer__apellido', 'empresa__nombre']
    ordering_fields = ['fecha']

class MatafuegosViewSet(BaseAppModelViewSet):
    queryset = Matafuegos.objects.all()
    serializer_class = MatafuegosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['empresa__nombre', 'area_nombre']
    ordering_fields = ['fecha_vencimiento']

class GastosMovilViewSet(BaseAppModelViewSet):
    queryset = GastosMovil.objects.all()
    serializer_class = GastosMovilSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['movil__patente', 'cliente__nombre', 'area__detalle', 'centro_costos__descripcion']
    ordering_fields = ['fecha']

class CentroCostosViewSet(BaseAppModelViewSet):
    queryset = CentroCostos.objects.all()
    serializer_class = CentroCostosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['descripcion']
    ordering_fields = ['descripcion']


class PrediosViewSet(BaseAppModelViewSet):
    queryset = Predios.objects.all()
    serializer_class = PrediosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']
    ordering_fields = ['nombre']


class ViajesViewSet(BaseAppModelViewSet):
    queryset = Viajes.objects.all()
    serializer_class = ViajesSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['movil__patente', 'cliente__nombre', 'origen__nombre', 'destino', 'producto']
    ordering_fields = ['-fecha']
    ordering = ['-fecha', '-id']  # Ordenar por fecha descendente y luego por ID

    def get_queryset(self):
        qs = super().get_queryset()
        # filtros opcionales por rango de fecha y movil
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        movil = self.request.query_params.get('movil')
        chofer = self.request.query_params.get('chofer')
        producto = self.request.query_params.get('producto')
        destino = self.request.query_params.get('destino')
        if start_date:
            qs = qs.filter(fecha__gte=start_date)
        if end_date:
            qs = qs.filter(fecha__lte=end_date)
        if movil:
            qs = qs.filter(movil_id=movil)
        if chofer:
            # filtrar por personal/chofer (campo personal en Viajes)
            qs = qs.filter(personal_id=chofer)
        if producto:
            qs = qs.filter(producto=producto)
        if destino:
            qs = qs.filter(destino=destino)
        return qs.order_by('-fecha', '-id')  # Asegurar orden consistente

    # endpoint extra para KPIs
    def kpis(self, request):
        qs = self.filter_queryset(self.get_queryset())
        total_viajes_sin_actividad = qs.filter(sin_actividad=False).count()  # Solo contar viajes realizados
        total_viajes_total = qs.count()  # Total incluyendo días sin actividad
        print(f"[KPIS] Total registros: {total_viajes_total}, Viajes realizados: {total_viajes_sin_actividad}")
        
        tn_pulpable = qs.aggregate(sum=Sum('tn_pulpable'))['sum'] or 0
        tn_aserrable = qs.aggregate(sum=Sum('tn_aserrable'))['sum'] or 0
        tn_chip = qs.aggregate(sum=Sum('tn_chip'))['sum'] or 0
        totals = {
            'total_viajes': total_viajes_sin_actividad,  # Cambiado para excluir días sin actividad
            'tn_pulpable': float(tn_pulpable),
            'tn_aserrable': float(tn_aserrable),
            'tn_chip': float(tn_chip),
            'tn_total': float(tn_pulpable + tn_aserrable + tn_chip)
        }
        return Response(totals)
    
def moviles_list(request):
    return render(request, 'pages/moviles/movil_list.html')

def tipo_vencimientos_list(request):
    return render(request, 'pages/moviles/tipo_vencimientos_list.html')

def vencimientos_list(request):
    return render(request, 'pages/moviles/vencimientos_list.html')

def personal_list(request):
    return render(request, 'pages/moviles/personal_list.html')

def carga_combustible_list(request):
    return render(request, 'pages/moviles/carga_combustible_list.html')

def gastos_movil_list(request):
    return render(request, 'pages/moviles/gastos_moviles_list.html')

def consumo_combustible_por_mes(request):
    empresas = Cliente.objects.all()
    fecha_inicio = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    fecha_fin = datetime.now().strftime('%Y-%m-%d')
    return render(request, 
                  'pages/moviles/consumo_combustible_por_mes.html', 
                  {'empresas': empresas, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})

def datos_consumo_combustible(request):
    empresa_id = request.GET.get('empresa')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if not fecha_inicio:
        fecha_inicio = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = datetime.now().strftime('%Y-%m-%d')
    if empresa_id:
        empresa = Cliente.objects.get(id=empresa_id)
        datos = CargaCombustible.objects.filter(empresa=empresa, fecha__range=[fecha_inicio, fecha_fin]).values('movil__patente', 'fecha__month').annotate(consumo=Sum('litros'))
        datos_json = []
        for dato in datos:
            datos_json.append({
              'movil': dato['movil__patente'],
              'mes': dato['fecha__month'],
                'consumo': dato['consumo']
            })
        return JsonResponse(datos_json, safe=False)
    else:
        return JsonResponse([], safe=False)
    

#vistas para el manejo de matafuegos
def matafuegos_list(request):
    return render(request, 'pages/moviles/matafuegos_list.html')

class GastosPorMovilView(ListAPIView):
    serializer_class = GastosMovilSerializer
    
    def get_queryset(self):
        queryset = GastosMovil.objects.all()
        
        # Filtros
        empresa = self.request.query_params.get('empresa')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if empresa:
            queryset = queryset.filter(cliente_id__id=empresa)
        if start_date:
            queryset = queryset.filter(fecha__gte=start_date)
        if end_date:
            queryset = queryset.filter(fecha__lte=end_date)
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Datos para la tabla
        serializer = self.get_serializer(queryset, many=True)
        
        # Datos para el gráfico de torta
        chart_data = queryset.values('centro_costos__descripcion') \
            .annotate(total_importe=Sum('importe')) \
            .order_by('-total_importe')
        
        return Response({
            'gastos': serializer.data,
            'chart_data': list(chart_data)
        })


def reporte_gastos_view(request):
    empresas = Cliente.objects.all()
    # Establecer fechas por defecto (último mes)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    return render(request, 'pages/moviles/reporte_gastos_movil.html', {
        'empresas': empresas,
        'start_date': start_date,
        'end_date': end_date
    })        


def viajes_list(request):
    # página que carga la app Vue para manejar viajes
    return render(request, 'pages/moviles/viajes_list.html')


@api_view(['GET'])
def viajes_kpis(request):
    """Endpoint simple que devuelve KPIs de viajes filtrando por start_date, end_date, movil"""
    qs = Viajes.objects.all()
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    movil = request.query_params.get('movil')
    chofer = request.query_params.get('chofer')
    producto = request.query_params.get('producto')
    destino = request.query_params.get('destino')
    if start_date:
        qs = qs.filter(fecha__gte=start_date)
    if end_date:
        qs = qs.filter(fecha__lte=end_date)
    if movil:
        qs = qs.filter(movil_id=movil)
    if chofer:
        qs = qs.filter(personal_id=chofer)
    if producto:
        qs = qs.filter(producto=producto)
    if destino:
        qs = qs.filter(destino=destino)

    total_viajes_sin_actividad = qs.filter(sin_actividad=False).count()  # Solo contar viajes realizados
    total_viajes_total = qs.count()  # Total incluyendo días sin actividad
    print(f"[KPIS] Total registros: {total_viajes_total}, Viajes realizados: {total_viajes_sin_actividad}")
    
    tn_pulpable = qs.aggregate(sum=Sum('tn_pulpable'))['sum'] or 0
    tn_aserrable = qs.aggregate(sum=Sum('tn_aserrable'))['sum'] or 0
    tn_chip = qs.aggregate(sum=Sum('tn_chip'))['sum'] or 0
    totals = {
        'total_viajes': total_viajes_sin_actividad,  # Cambiado para excluir días sin actividad
        'tn_pulpable': float(tn_pulpable),
        'tn_aserrable': float(tn_aserrable),
        'tn_chip': float(tn_chip),
        'tn_total': float(tn_pulpable + tn_aserrable + tn_chip)
    }
    return Response(totals)


@api_view(['GET'])
def export_viajes_xlsx(request):
    """Exporta los viajes filtrados a un archivo XLSX.

    Aplica los mismos filtros que el endpoint de KPIs/get_queryset: start_date, end_date, movil, chofer, producto, destino
    Incluye viajes con sin_actividad=True incluso si origen es NULL.
    """
    # Usar select_related solo en movil (obligatorio) y personal (nullable)
    # No usar select_related en origen para evitar problemas con NULL en viajes sin actividad
    qs = Viajes.objects.all()
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    movil = request.query_params.get('movil')
    chofer = request.query_params.get('chofer')
    producto = request.query_params.get('producto')
    destino = request.query_params.get('destino')
    if start_date:
        qs = qs.filter(fecha__gte=start_date)
    if end_date:
        qs = qs.filter(fecha__lte=end_date)
    if movil:
        qs = qs.filter(movil_id=movil)
    if chofer:
        qs = qs.filter(personal_id=chofer)
    if producto:
        qs = qs.filter(producto=producto)
    if destino:
        qs = qs.filter(destino=destino)

    # Ordenar y contar para debug
    qs = qs.order_by('-fecha', '-id')
    total_viajes = qs.count()
    viajes_sin_actividad = qs.filter(sin_actividad=True).count()
    print(f"[EXPORT] Total viajes a exportar: {total_viajes}, con sin_actividad: {viajes_sin_actividad}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Viajes'

    # Construir encabezados tomando verbose_name cuando esté disponible
    model = Viajes

    def label_for(field_name):
        try:
            f = model._meta.get_field(field_name)
            return str(f.verbose_name).title()
        except Exception:
            return field_name.replace('_', ' ').title()


    # Sólo las columnas requeridas por el usuario, en el orden solicitado
    headers = [
        ('fecha', 'Fecha'),
        ('movil_patente', 'Patente'),
        ('personal_nombre', 'Nombre Chofer'),
        ('origen', 'Origen'),
        ('origen_nombre', 'Origen Nombre'),
        ('destino', 'Destino'),
        ('producto', 'Producto'),
        ('tn_pulpable', 'KG Pulpable'),
        ('tn_aserrable', 'KG Aserrable'),
        ('tn_chip', 'KG Chips'),
        ('sin_actividad', 'Sin Actividad'),
        ('motivo_sin_actividad', 'Motivo Sin Actividad'),
        ('observaciones', 'Observaciones'),
    ]

    ws.append([h[1] for h in headers])

    # Iterar y exportar, manejando casos donde origen puede ser NULL
    rows_exported = 0
    for obj in qs:
        fecha = obj.fecha.strftime('%d-%m-%Y') if getattr(obj, 'fecha', None) else ''
        movil_patente = obj.movil.patente if obj.movil else ''
        personal_nombre = f"{obj.personal.apellido} {obj.personal.nombre}" if obj.personal else ''
        # Manejar origen NULL (puede ocurrir en viajes sin actividad)
        try:
            origen_val = obj.origen.id if obj.origen else ''
            origen_nombre = obj.origen.nombre if obj.origen else ''
        except Exception:
            origen_val = ''
            origen_nombre = ''
        destino = obj.get_destino_display() if hasattr(obj, 'get_destino_display') else (obj.destino or '')
        producto = obj.get_producto_display() if hasattr(obj, 'get_producto_display') else (obj.producto or '')
        tn_pulpable = float(obj.tn_pulpable) if obj.tn_pulpable is not None else 0
        tn_aserrable = float(obj.tn_aserrable) if obj.tn_aserrable is not None else 0
        tn_chip = float(obj.tn_chip) if obj.tn_chip is not None else 0
        sin_actividad = bool(obj.sin_actividad)
        motivo = obj.motivo_sin_actividad or ''
        observaciones = obj.observaciones or ''

        row = [
            fecha,
            movil_patente,
            personal_nombre,
            origen_val,
            origen_nombre,
            destino,
            producto,
            tn_pulpable,
            tn_aserrable,
            tn_chip,
            sin_actividad,
            motivo,
            observaciones,
        ]
        ws.append(row)
        rows_exported += 1

    print(f"[EXPORT] Filas exportadas: {rows_exported}")

    # Ajustar anchos de columna
    for i, column_cells in enumerate(ws.columns, 1):
        max_length = 0
        for cell in column_cells:
            try:
                v = str(cell.value) if cell.value is not None else ''
            except Exception:
                v = ''
            if len(v) > max_length:
                max_length = len(v)
        ws.column_dimensions[get_column_letter(i)].width = min(max_length + 2, 50)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"viajes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def viajes_graficos_view(request):
    """Vista que renderiza la página de gráficos interactivos de viajes"""
    return render(request, 'pages/moviles/viajes_graficos.html')


@staff_member_required
@require_POST
def sync_airtable_to_mysql(request):
    """Endpoint para sincronizar registros de Airtable a MySQL"""
    import traceback
    
    try:
        # Capturar la salida del comando
        out = io.StringIO()
        err = io.StringIO()
        
        call_command('sync_airtable', '--mysql', '--confirm', stdout=out, stderr=err)
        
        output = out.getvalue()
        errors = err.getvalue()
        
        response_data = {
            'success': True,
            'message': 'Sincronización completada exitosamente',
            'output': output
        }
        
        if errors:
            response_data['warnings'] = errors
        
        return JsonResponse(response_data)
        
    except Exception as e:
        error_details = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        
        # Intentar obtener más detalles si es un CalledProcessError
        if hasattr(e, '__cause__') and e.__cause__:
            error_details['cause'] = str(e.__cause__)
        
        return JsonResponse(error_details, status=500)


@api_view(['GET'])
def viajes_graficos_data(request):
    """Endpoint que devuelve datos para gráficos de viajes.
    
    Retorna:
    - evolucion_diaria: lista de {fecha, total_kg} para gráfico de línea
    - proporcion_productos: lista de {producto, kg} para gráfico de torta
    
    Filtros: start_date, end_date, producto, movil, chofer
    """
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDate
    
    qs = Viajes.objects.all()
    
    # Aplicar filtros
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    movil = request.query_params.get('movil')
    chofer = request.query_params.get('chofer')
    producto = request.query_params.get('producto')
    
    if start_date:
        qs = qs.filter(fecha__gte=start_date)
    if end_date:
        qs = qs.filter(fecha__lte=end_date)
    if movil:
        qs = qs.filter(movil_id=movil)
    if chofer:
        qs = qs.filter(personal_id=chofer)
    if producto:
        qs = qs.filter(producto=producto)
    
    # Filtrar registros con fecha válida
    qs = qs.filter(fecha__isnull=False)
    
    # Debug: contar registros
    total_registros = qs.count()
    print(f"[GRAFICOS] Total registros con fecha válida: {total_registros}")
    
    # 1. Evolución diaria de kg transportados
    # Usar fecha directamente en lugar de TruncDate si hay problemas
    from collections import defaultdict
    
    # Agrupar manualmente por fecha
    evolucion_data = defaultdict(lambda: {'pulpable': 0, 'aserrable': 0, 'chip': 0})
    
    for viaje in qs:
        fecha_str = viaje.fecha.strftime('%Y-%m-%d')
        evolucion_data[fecha_str]['pulpable'] += float(viaje.tn_pulpable or 0)
        evolucion_data[fecha_str]['aserrable'] += float(viaje.tn_aserrable or 0)
        evolucion_data[fecha_str]['chip'] += float(viaje.tn_chip or 0)
    
    # Convertir a lista ordenada
    evolucion_diaria = []
    for fecha_str in sorted(evolucion_data.keys()):
        datos = evolucion_data[fecha_str]
        total_kg = datos['pulpable'] + datos['aserrable'] + datos['chip']
        evolucion_diaria.append({
            'fecha': fecha_str,
            'total_kg': round(total_kg, 2),
            'pulpable': round(datos['pulpable'], 2),
            'aserrable': round(datos['aserrable'], 2),
            'chip': round(datos['chip'], 2)
        })
    
    print(f"[GRAFICOS] evolucion_diaria length: {len(evolucion_diaria)}")
    if len(evolucion_diaria) > 0:
        print(f"[GRAFICOS] Primera fecha: {evolucion_diaria[0]['fecha']}, Última fecha: {evolucion_diaria[-1]['fecha']}")
    
    # 2. Proporción de kg por tipo de producto (todos los viajes)
    total_pulpable = qs.aggregate(sum=Sum('tn_pulpable'))['sum'] or 0
    total_aserrable = qs.aggregate(sum=Sum('tn_aserrable'))['sum'] or 0
    total_chip = qs.aggregate(sum=Sum('tn_chip'))['sum'] or 0

    proporcion_productos = []
    if total_pulpable > 0:
        proporcion_productos.append({
            'producto': 'Pulpable',
            'kg': round(float(total_pulpable), 2)
        })
    if total_aserrable > 0:
        proporcion_productos.append({
            'producto': 'Aserrable',
            'kg': round(float(total_aserrable), 2)
        })
    if total_chip > 0:
        proporcion_productos.append({
            'producto': 'Chip',
            'kg': round(float(total_chip), 2)
        })

    # KPIs básicos - usar los totales ya calculados
    total_viajes_sin_filtro = qs.count()  # Total incluyendo días sin actividad
    total_viajes = qs.filter(sin_actividad=False).count()  # Solo contar viajes realizados, no días sin actividad
    total_sin_actividad = qs.filter(sin_actividad=True).count()  # Días sin actividad
    
    total_kg = float(total_pulpable) + float(total_aserrable) + float(total_chip)
    
    # Debug: mostrar el total_viajes calculado
    print(f"[GRAFICOS] Total registros: {total_viajes_sin_filtro}, Viajes realizados: {total_viajes}, Días sin actividad: {total_sin_actividad}")
    print(f"[GRAFICOS] Total viajes realizados: {total_viajes} (excluyendo días sin actividad)")
    
    # Debug: mostrar el total_kg calculado
    print(f"[GRAFICOS] Total KG calculado: {total_kg} (Pulpable: {total_pulpable}, Aserrable: {total_aserrable}, Chip: {total_chip})")
    
    # Calcular días totales en el rango con al menos un viaje
    dias_totales = len(set([v.fecha.strftime('%Y-%m-%d') for v in qs if getattr(v, 'fecha', None)]))
    avg_kg_por_dia = round((total_kg / dias_totales), 2) if dias_totales > 0 else 0

    # Viajes marcados sin actividad y móviles únicos sin actividad
    total_sin_actividad_viajes = qs.filter(sin_actividad=True).count()
    moviles_unicos_sin_actividad = qs.filter(sin_actividad=True).values('movil').distinct().count()

    # 3. Proporción de kg por tipo SOLO en viajes con sin_actividad=True
    qs_sin = qs.filter(sin_actividad=True)
    total_pulpable_sin = qs_sin.aggregate(sum=Sum('tn_pulpable'))['sum'] or 0
    total_aserrable_sin = qs_sin.aggregate(sum=Sum('tn_aserrable'))['sum'] or 0
    total_chip_sin = qs_sin.aggregate(sum=Sum('tn_chip'))['sum'] or 0

    proporcion_sin_actividad = []
    if total_pulpable_sin > 0:
        proporcion_sin_actividad.append({'producto': 'Pulpable', 'kg': round(float(total_pulpable_sin), 2)})
    if total_aserrable_sin > 0:
        proporcion_sin_actividad.append({'producto': 'Aserrable', 'kg': round(float(total_aserrable_sin), 2)})
    if total_chip_sin > 0:
        proporcion_sin_actividad.append({'producto': 'Chip', 'kg': round(float(total_chip_sin), 2)})

    # 4. Días con sin_actividad por motivo_sin_actividad (conteo de fechas distintas)
    # Algunas bases pueden devolver resultados inesperados con Count(distinct=fecha).
    # Para asegurar exactitud construimos sets de fechas en Python por motivo.
    from collections import defaultdict

    # Ahora vamos a contar pares (fecha, movil) por motivo. Así si dos moviles
    # están sin actividad el mismo día se cuentan como 2.
    motivo_pairs = defaultdict(set)
    for viaje in qs_sin:
        if not viaje.fecha:
            continue
        motivo = (viaje.motivo_sin_actividad or 'Sin motivo').strip()
        fecha_str = viaje.fecha.strftime('%Y-%m-%d')
        movil_id = viaje.movil.id if getattr(viaje, 'movil', None) else f"movil_none_{getattr(viaje, 'id', '')}"
        # usar la tupla (fecha, movil_id) para diferenciar moviles en mismo dia
        motivo_pairs[motivo].add((fecha_str, movil_id))

    # Construir lista ordenada por cantidad de pares (desc)
    dias_sin_actividad = []
    total_dias_sin = 0
    for motivo, pairs in sorted(motivo_pairs.items(), key=lambda x: -len(x[1])):
        count = len(pairs)
        if count > 0:
            dias_sin_actividad.append({'motivo': motivo, 'dias': count})
            total_dias_sin += count

    # Añadir porcentaje relativo por motivo
    if total_dias_sin > 0:
        for d in dias_sin_actividad:
            d['porcentaje'] = round((d['dias'] / total_dias_sin) * 100, 1)

    # Debug: mostrar listado de pares por motivo en server logs para inspección
    try:
        debug_map = {m: sorted([f"{f}-{mid}" for f, mid in fs]) for m, fs in motivo_pairs.items()}
        print(f"[GRAFICOS] pares (fecha-movil) por motivo (debug): {debug_map}")
    except Exception:
        pass

    # Construir lista de verificación: filas individuales con motivo, fecha y móvil
    verification_rows = []
    for motivo, pairs in motivo_pairs.items():
        for fecha_str, movil_id in sorted(pairs):
            # intentar obtener patente si es posible
            patente = ''
            try:
                mv = Movil.objects.filter(id=movil_id).first() if isinstance(movil_id, int) else None
                if mv:
                    patente = mv.patente
            except Exception:
                patente = ''
            verification_rows.append({'motivo': motivo, 'fecha': fecha_str, 'movil_id': movil_id, 'patente': patente})

    print(f"dias sin actividad {dias_sin_actividad} total de viajes {total_viajes}")
    return Response({
        'evolucion_diaria': evolucion_diaria,
        'proporcion_productos': proporcion_productos,
        'proporcion_sin_actividad': proporcion_sin_actividad,
        'dias_sin_actividad': dias_sin_actividad,
        'verification_rows': verification_rows,
        'kpis': {
            'total_viajes': total_viajes,
            'total_kg': round(total_kg, 2),
            'avg_kg_por_dia': avg_kg_por_dia,
            'total_sin_actividad_viajes': total_sin_actividad_viajes,
            'moviles_unicos_sin_actividad': moviles_unicos_sin_actividad
        }
    })