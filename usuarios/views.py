from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect

from .forms import UserUpdateForm

@login_required(login_url='/admin/login/')
def user_logout(request):
    logout(request)
    return redirect('/')

@login_required
def update_user(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('/')  # Redirige al perfil del usuario después de actualizar
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'pages/usuarios/update_user.html', {'form': form})
