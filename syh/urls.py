from django.urls import path

from . import views

app_name = 'syh'

urlpatterns = [
    path('movimientos/', views.visualizar_movimientos, name='visualizar_movimientos'),
    path('imprimir_movimientos', views.imprimir_movimientos, name='imprimir_movimientos'),
    path('obtener-areas/', views.obtener_areas, name='obtener_areas'),
    path('api/obtener-areas-vue/', views.obtener_areas_vue, name='obtener_areas_vue'),

    path('plantilla-excesos/', views.excesos_plantilla, name='excesos_plantilla'),
    # API para Excesos de Velocidad
    path('api/excesos/', views.excesos_list, name='excesos_list'),  # Listar y crear excesos
    path('api/excesos/<int:id>/', views.excesos_detail, name='excesos_detail'),  # Editar y eliminar excesos

    # API para Clientes
    path('api/clientes/', views.clientes_list, name='clientes_list'),  # Listar clientes

    # API para Áreas por Cliente
    path('api/areas/<int:cliente_id>/', views.obtener_areas_vue, name='areas_by_cliente'),  # Listar áreas de un cliente
]