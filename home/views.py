from django.shortcuts import render, redirect
from admin_datta.forms import RegistrationForm, LoginForm, UserPasswordChangeForm, UserPasswordResetForm, UserSetPasswordForm
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetConfirmView, PasswordResetView
from django.views.generic import CreateView
from django.contrib.auth import logout

from django.contrib.auth.decorators import login_required

from usuarios.models import Profile
from syh.models import Area, Cliente, EmisionCarbono, Movimientos

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
  except Profile.DoesNotExist:
      # Si no tiene un perfil, puedes manejar el caso con un mensaje de error o redirección
      cliente = None
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
      areas = Area.objects.filter(cliente = cliente_id)
    else:
      areas = Area.objects.all()
  else:
    clientes = Cliente.objects.filter(id = cliente_id)
    areas = Area.objects.filter(cliente = cliente_id)
  
  print(f'Cliente seleccionado {cliente_id}')
  # if cliente_id:
  #    cliente = cliente_id
    
  # Obtiene los datos de las tareas agrupadas por estado
  tareas_por_estado = Movimientos.contar_tareas_por_estado(cliente, area_id)
  # Formatea los datos para Morris.js
  datos_grafico = [
        {"label": tarea["estado"], "value": tarea["cantidad"]}
        for tarea in tareas_por_estado
  ]

  plazo_promedio_clientes, promedio_general = Movimientos.plazo_promedio(cliente)
  emisiones = EmisionCarbono.calcular_emisiones(cliente_id)
    
  periodos = [item[0] for item in emisiones]
  valores = [float(item[1]) for item in emisiones]

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
    #'products' : Product.objects.all()
  }
  return render(request, "pages/index.html", context)

def tables(request):
  context = {
    'segment': 'tables'
  }
  return render(request, "pages/dynamic-tables.html", context)
