from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import UsuarioIngreso


@receiver(user_logged_in)
def registrar_ingreso_usuario(sender, request, user, **kwargs):
    UsuarioIngreso.objects.create(user=user)
