from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GastosPorMovilView, MovilViewSet, TipoVencimientosViewSet
from .views import ViajesViewSet, PrediosViewSet

from . import views

app_name = 'moviles'

router = DefaultRouter()
router.register(r'movil', MovilViewSet)
router.register(r'tipo_vencimiento', TipoVencimientosViewSet)
router.register(r'vencimiento', views.VencimientosViewSet)
router.register(r'personal', views.PersonalViewSet)
router.register(r'carga_combustible', views.CargaCombustibleViewSet)
router.register(r'matafuegos', views.MatafuegosViewSet)
router.register(r'gastos_movil', views.GastosMovilViewSet)
router.register(r'centro_costos', views.CentroCostosViewSet)
router.register(r'predios', views.PrediosViewSet)
router.register(r'viajes', views.ViajesViewSet)


urlpatterns = [
    # Rutas específicas de API deben ir ANTES del include del router
    path('api/viajes/kpis/', views.viajes_kpis, name='api_viajes_kpis'),
    path('api/viajes/export/', views.export_viajes_xlsx, name='api_viajes_export'),
    path('api/', include(router.urls)),
    
    # Rutas de vistas HTML
    path('moviles/', views.moviles_list, name='moviles_list'),  # Listar moviles
    path('tipo_vencimientos/', views.tipo_vencimientos_list, name='tipo_vencimientos_list'),  # Listar tipos de vencimientos
    path('vencimientos/', views.vencimientos_list, name='vencimientos_list'),  # Listar vencimientos
    path('personal/', views.personal_list, name='personal_list'),  # Listar personal
    path('carga_combustible/', views.carga_combustible_list, name='carga_combustible_list'),  # Listar carga de combustible
    path('gasto_movil/', views.gastos_movil_list, name='gastos_movil_list'),  # Listar gastos movil
    path('consumo_combustible_por_mes/', views.consumo_combustible_por_mes, name='consumo_combustible_por_mes'),
    path('datos_consumo_combustible', views.datos_consumo_combustible, name='datos_consumo_combustible'),
    path('grafico_gastos_movil/', GastosPorMovilView.as_view(), name='grafico-gastos-movil'),
    path('reporte_gastos_movil/', views.reporte_gastos_view, name='reporte_gastos_movil'),
    path('viajes/', views.viajes_list, name='viajes_list'),

    # URL's para matafuegos
    path('matafuegos/', views.matafuegos_list, name='matafuegos_list'),  # Listar matafuegos
]