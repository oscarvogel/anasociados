from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MovilViewSet, TipoVencimientosViewSet

from . import views

app_name = 'moviles'

router = DefaultRouter()
router.register(r'movil', MovilViewSet)
router.register(r'tipo_vencimiento', TipoVencimientosViewSet)
router.register(r'vencimiento', views.VencimientosViewSet)
router.register(r'personal', views.PersonalViewSet)
router.register(r'carga_combustible', views.CargaCombustibleViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('moviles/', views.moviles_list, name='moviles_list'),  # Listar moviles
    path('tipo_vencimientos/', views.tipo_vencimientos_list, name='tipo_vencimientos_list'),  # Listar tipos de vencimientos
    path('vencimientos/', views.vencimientos_list, name='vencimientos_list'),  # Listar vencimientos
    path('personal/', views.personal_list, name='personal_list'),  # Listar personal
    path('carga_combustible/', views.carga_combustible_list, name='carga_combustible_list'),  # Listar carga de combustible
]