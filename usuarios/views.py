from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect


@login_required(login_url='/admin/login/')
def user_logout(request):
    logout(request)
    return redirect('/')
