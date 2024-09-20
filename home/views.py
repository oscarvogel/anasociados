from django.shortcuts import render, redirect
from admin_datta.forms import RegistrationForm, LoginForm, UserPasswordChangeForm, UserPasswordResetForm, UserSetPasswordForm
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetConfirmView, PasswordResetView
from django.views.generic import CreateView
from django.contrib.auth import logout

from django.contrib.auth.decorators import login_required

from usuarios.models import Profile
from syh.models import Movimientos

@login_required(login_url='/admin/login/')
def index(request):
  # Obtener el perfil del usuario autenticado
  try:
      profile = Profile.objects.get(user=request.user)
      cliente = profile.cliente  # Obtener el cliente asociado al perfil
  except Profile.DoesNotExist:
      # Si no tiene un perfil, puedes manejar el caso con un mensaje de error o redirección
      cliente = None
  if request.user.is_superuser:
    cliente = 'Todos'
    nombre = 'Todos los clientes'
    tareas = Movimientos.objects.all().order_by('-periodo')[:10]
  else:
    nombre = cliente.nombre
    tareas = Movimientos.objects.filter(cliente=cliente).order_by('-periodo')[:10]

  # Obtiene los datos de las tareas agrupadas por estado
  tareas_por_estado = Movimientos.contar_tareas_por_estado(cliente)
  print(tareas)
  # Formatea los datos para Morris.js
  datos_grafico = [
        {"label": tarea["estado"], "value": tarea["cantidad"]}
        for tarea in tareas_por_estado
  ]
  context = {
    'segment'  : 'index',
    'datos_grafico': datos_grafico,
    'cliente': nombre,
    'tareas': tareas,
    #'products' : Product.objects.all()
  }
  return render(request, "pages/index.html", context)

def tables(request):
  context = {
    'segment': 'tables'
  }
  return render(request, "pages/dynamic-tables.html", context)
