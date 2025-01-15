from django.shortcuts import render

# Create your views here.
from moviles.serializer import CargaCombustibleSerializer, MovilSerializer, PersonalSerializer, TipoVencimientosSerializer, VencimientosSerializer
from rest_framework import viewsets, filters
from .models import CargaCombustible, Movil, Personal, TipoVencimientos, Vencimientos

class MovilViewSet(viewsets.ModelViewSet):
    queryset = Movil.objects.all()
    serializer_class = MovilSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['patente', 'empresa__nombre']  # Asegúrate de que 'nombre' es el campo correcto en el modelo 'Clientes'
    ordering_fields = ['patente']
    

class TipoVencimientosViewSet(viewsets.ModelViewSet):
    queryset = TipoVencimientos.objects.all()
    serializer_class = TipoVencimientosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'tipo']  # Asegúrate de que 'nombre' y 'tipo' son los campos correctos en el modelo 'TipoVencimientos'
    ordering_fields = ['nombre']

class VencimientosViewSet(viewsets.ModelViewSet):
    queryset = Vencimientos.objects.all()
    serializer_class = VencimientosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['movil__patente', 'tipo_vencimiento__nombre', 'detalle']  # Asegúrate de que 'patente', 'nombre' y 'detalle' son los campos correctos en los modelos 'Movil' y 'TipoVencimientos'
    ordering_fields = ['-fecha', 'tipo_vencimiento']

class PersonalViewSet(viewsets.ModelViewSet):
    queryset = Personal.objects.all()
    serializer_class = PersonalSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'apellido', 'empresa__nombre']  # Asegúrate de que 'nombre', 'apellido' y 'dni' son los campos correctos en el modelo 'Personal'
    ordering_fields = ['nombre', 'apellido']
    
class CargaCombustibleViewSet(viewsets.ModelViewSet):
    queryset = CargaCombustible.objects.all()
    serializer_class = CargaCombustibleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['movil__patente', 'chofer__nombre', 'chofer__apellido', 'empresa__nombre']
    ordering_fields = ['fecha']    

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