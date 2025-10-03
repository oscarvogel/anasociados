from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from rest_framework.response import Response
from django.db.models import Sum
import django.db.models as models
from django.http import JsonResponse
from datetime import datetime, timedelta
from rest_framework.generics import ListAPIView

# Create your views here.
from moviles.serializer import CargaCombustibleSerializer, CentroCostosSerializer, GastosMovilSerializer, MatafuegosSerializer, MovilSerializer, PersonalSerializer, TipoVencimientosSerializer, VencimientosSerializer
from rest_framework import filters

from syh.models import Area, Cliente
from utiles.BaseViewSet import BaseAppModelViewSet
from .models import CargaCombustible, CentroCostos, GastosMovil, Matafuegos, Movil, Personal, TipoVencimientos, Vencimientos
from .models import Viajes, Predios
from .serializer import ViajesSerializer, PrediosSerializer
from rest_framework.decorators import api_view


class MovilViewSet(BaseAppModelViewSet):
    queryset = Movil.objects.all()
    serializer_class = MovilSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['patente', 'empresa__nombre']  # Asegúrate de que 'nombre' es el campo correcto en el modelo 'Clientes'
    ordering_fields = ['patente']
    

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
        total_viajes = qs.count()
        tn_pulpable = qs.aggregate(sum=Sum('tn_pulpable'))['sum'] or 0
        tn_aserrable = qs.aggregate(sum=Sum('tn_aserrable'))['sum'] or 0
        tn_chip = qs.aggregate(sum=Sum('tn_chip'))['sum'] or 0
        totals = {
            'total_viajes': total_viajes,
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

    total_viajes = qs.count()
    tn_pulpable = qs.aggregate(sum=Sum('tn_pulpable'))['sum'] or 0
    tn_aserrable = qs.aggregate(sum=Sum('tn_aserrable'))['sum'] or 0
    tn_chip = qs.aggregate(sum=Sum('tn_chip'))['sum'] or 0
    totals = {
        'total_viajes': total_viajes,
        'tn_pulpable': float(tn_pulpable),
        'tn_aserrable': float(tn_aserrable),
        'tn_chip': float(tn_chip),
        'tn_total': float(tn_pulpable + tn_aserrable + tn_chip)
    }
    return Response(totals)