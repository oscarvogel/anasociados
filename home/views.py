from datetime import date
from django.shortcuts import render, redirect
from admin_datta.forms import RegistrationForm, LoginForm, UserPasswordChangeForm, UserPasswordResetForm, UserSetPasswordForm
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetConfirmView, PasswordResetView
from django.views.generic import CreateView
from django.contrib.auth import logout

from django.contrib.auth.decorators import login_required

from usuarios.models import AreasProfile, Profile
from syh.models import Area, Cliente, EmisionCarbono, ExcesosVelocidad, IndiceAccidentabilidad, Movimientos

@login_required(login_url='/admin/login/')
def index(request):

  cliente_id = request.GET.get('cliente', None)
  area_id = request.GET.get('area', None)
  # print(f'Cliente ID {cliente_id} Area {area_id}')
  # Obtener el perfil del usuario autenticado
  try:
      profile = Profile.objects.get(user=request.user)
      cliente = profile.cliente  # Obtener el cliente asociado al perfil
      cliente_id = cliente.id
      areas_profile = AreasProfile.objects.filter(user=request.user)
  except Profile.DoesNotExist:
      # Si no tiene un perfil, puedes manejar el caso con un mensaje de error o redirección
      cliente = None
      areas_profile = None
  
  if request.user.is_superuser:
    cliente = 'Todos'
    nombre = 'Todos los clientes'
    tareas = Movimientos.objects.all().order_by('-periodo')[:10]
    cliente_id = request.GET.get('cliente', None)
  else:
    nombre = cliente.nombre
    tareas = Movimientos.objects.filter(cliente=cliente).order_by('-periodo')[:10]
  
  if cliente == 'Todos':
    clientes = Cliente.objects.all()
    if cliente_id:
      if not areas_profile:
        areas = Area.objects.filter(cliente = cliente_id)
      else:
        areas = Area.objects.filter(id__in=[area.area.id for area in areas_profile])
    else:
      areas = Area.objects.all()
  else:
    clientes = Cliente.objects.filter(id = cliente_id)
    if not areas_profile:
      areas = Area.objects.filter(cliente = cliente_id)
    else:
      areas = Area.objects.filter(id__in=[area.area.id for area in areas_profile])
  
  # if cliente_id:
  #    cliente = cliente_id
    
  # Obtiene los datos de las tareas agrupadas por estado
  tareas_por_estado = Movimientos.contar_tareas_por_estado_vista(cliente, area_id)
  # Formatea los datos para Morris.js
  datos_grafico = [
        {"label": tarea["estado"], "value": tarea["cantidad"]}
        for tarea in tareas_por_estado
  ]

  plazo_promedio_clientes, promedio_general = Movimientos.plazo_promedio(cliente)
  emisiones = EmisionCarbono.calcular_emisiones(cliente_id)
    
  periodos = [item[0] for item in emisiones]
  valores = [float(item[1]) for item in emisiones]
        # return {
        #     'indice_frecuencia': indice_frecuencia,
        #     'indice_gravedad': indice_gravedad,
        #     'indice_accidentabilidad': indice_accidentabilidad
        # }
  datos = IndiceAccidentabilidad.calcular_indices(cliente=cliente_id)

  excesos_velocidad = ExcesosVelocidad.chart_view(cliente_id)

  porcentaje_por_area = Movimientos.get_porcentaje_cumplidos_por_area(cliente_id, fecha_desde=date(2020, 1, 1), fecha_hasta=date.today())

  meta_porcentaje = 85

  context = {
    'segment'  : 'index',
    'datos_grafico': datos_grafico,
    'cliente': nombre,
    'tareas': tareas,
    'plazo_promedio_clientes': plazo_promedio_clientes,
    'promedio_general': promedio_general,
    'areas': areas,
    'clientes': clientes,
    'cliente_id_selected': cliente_id,
    'area_id_selected': area_id,
    'periodos': periodos,
    'valores': valores,
    'indice_frecuencia': datos['indice_frecuencia'],
    'indice_gravedad': datos['indice_gravedad'],
    'indice_accidentabilidad': datos['indice_accidentabilidad'],
    'tasa_riesgo': datos['tasa_riesgo'],
    'excesos_velocidad': excesos_velocidad,
    'porcentaje_por_area': porcentaje_por_area,
    'meta_porcentaje': meta_porcentaje,
    #'products' : Product.objects.all()
  }
  return render(request, "pages/index.html", context)

def tables(request):
  context = {
    'segment': 'tables'
  }
  return render(request, "pages/dynamic-tables.html", context)
