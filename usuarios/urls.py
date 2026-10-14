from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
  path(''       , views.user_logout, name='logout'),
  path('update/', views.update_user, name='update_user'),
  path('reporte-accesos/', views.reporte_accesos, name='reporte_accesos'),
  path('gestion/', views.management_users, name='management_users'),
  path('gestion/nuevo/', views.management_user_edit, name='management_user_create'),
  path('gestion/<int:user_id>/editar/', views.management_user_edit, name='management_user_edit'),
]
