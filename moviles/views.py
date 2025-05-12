from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from rest_framework.response import Response
from django.db.models import Sum
from django.http import JsonResponse
from datetime import datetime, timedelta

# Create your views here.
from moviles.serializer import CargaCombustibleSerializer, MatafuegosSerializer, MovilSerializer, PersonalSerializer, TipoVencimientosSerializer, VencimientosSerializer
from rest_framework import filters

from syh.models import Area, Cliente
from utiles.BaseViewSet import BaseAppModelViewSet
from .models import CargaCombustible, Matafuegos, Movil, Personal, TipoVencimientos, Vencimientos


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
