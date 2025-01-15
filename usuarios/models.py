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

    def __str__(self):
        return f"{self.user.username} - {self.area.detalle}"
    
    class Meta:
        verbose_name = "Área de Perfil"
        verbose_name_plural = "Áreas de Perfiles"
        ordering = ["user"]
