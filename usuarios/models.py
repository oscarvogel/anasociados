from django.db import models
from django.contrib.auth.models import User
from syh.models import Cliente
# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, db_column="user")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column="cliente")

    def __str__(self):
        return f"{self.user.username} - {self.cliente.nombre}"
    
    class Meta:
        db_table = "perfiles"
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"
        ordering = ["user"]
        managed = False

class AreasProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user")
    area = models.ForeignKey('syh.Area', on_delete=models.CASCADE, db_column="area")
    telefono_whatsapp = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="WhatsApp del encargado",
        help_text="Número internacional, por ejemplo 5493764000000.",
    )

    def __str__(self):
        return f"{self.user.username} - {self.area.detalle}"
    
    class Meta:
        verbose_name = "Área de Perfil"
        verbose_name_plural = "Áreas de Perfiles"
        ordering = ["user"]


class UsuarioIngreso(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ingresos_usuarios")
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ingreso de usuario"
        verbose_name_plural = "Ingresos de usuarios"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["fecha_hora"]),
            models.Index(fields=["user", "fecha_hora"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.fecha_hora:%Y-%m-%d %H:%M}"


class UsuarioMenuAcceso(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accesos_menu")
    menu_codigo = models.CharField(max_length=120)
    menu_nombre = models.CharField(max_length=120)
    path = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Acceso a menú"
        verbose_name_plural = "Accesos a menús"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["fecha_hora"]),
            models.Index(fields=["menu_codigo", "fecha_hora"]),
            models.Index(fields=["user", "fecha_hora"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.menu_nombre} - {self.fecha_hora:%Y-%m-%d %H:%M}"
