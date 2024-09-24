import datetime
from django.db import models
from django.db.models import Count
from django.utils.html import mark_safe
from django.utils import timezone

# Create your models here.

from django.db import models

class ParametroSistema(models.Model):
    parametro = models.CharField(max_length=30, default='', primary_key=True)
    valor = models.CharField(max_length=80, default='')
    detalle = models.TextField(default='')

    def __str__(self) -> str:
        return self.parametro
    
    class Meta:
        db_table = 'parametro_sistema'
        verbose_name_plural = "Parámetros del sistema"

class Cliente(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    nombre = models.CharField(max_length=100)
    celular = models.CharField(max_length=80)
    email = models.EmailField(max_length=200)

    def __str__(self):
        return self.nombre
    
    class Meta:
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]
        managed = False

class Area(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='cliente')
    detalle = models.CharField(max_length=100)
    responsable = models.CharField(max_length=80)

    def __str__(self):
        return self.detalle
    
    class Meta:
        db_table = "areas"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        ordering = ["detalle"]
        managed = False

class Movimientos(models.Model):

    ESTADO_CHOICES = [
        ('Gestion', 'Gestion'),
        ('Cumplido', 'Cumplido'),
        ('Incumplido', 'Incumplido'),
        ('Cerrado', 'Cerrado'),
    ]
    PERIODO_CHOICES = [
        ('Enero', 'Enero'),
        ('Febrero', 'Febrero'),
        ('Marzo', 'Marzo'),
        ('Abril', 'Abril'),
        ('Mayo', 'Mayo'),
        ('Junio', 'Junio'),
        ('Julio', 'Julio'),
        ('Agosto', 'Agosto'),
        ('Septiembre', 'Septiembre'),
        ('Octubre', 'Octubre'),
        ('Noviembre', 'Noviembre'),
        ('Diciembre', 'Diciembre'),
    ]

    id = models.CharField(primary_key=True, max_length=10)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='cliente')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column='area')
    fecha = models.DateField()
    periodo = models.CharField(max_length=20, choices=PERIODO_CHOICES)
    hallazgo = models.TextField()
    responsable = models.CharField(max_length=80)
    plazo = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='GESTION')
    fecha_cumplimiento = models.DateField(null=True, blank=True)
    ubicacion = models.CharField(max_length=100, null=True, blank=True)
    fecha_realizado = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.cliente.nombre} - {self.fecha}'
    
    class Meta:
        db_table = "movimientos"
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ["cliente", "fecha"]
        managed = False

    @classmethod
    def contar_tareas_por_estado(cls, cliente):
        """
        Devuelve la cantidad de tareas según el estado para un cliente específico.
        """
        if cliente == 'Todos':
            return cls.objects.all().values('estado').annotate(cantidad=Count('estado'))
        else:
            return cls.objects.filter(cliente=cliente).values('estado').annotate(cantidad=Count('estado'))

class Evidencia(models.Model):
    id = models.AutoField(primary_key=True)
    movimiento = models.ForeignKey(Movimientos, on_delete=models.CASCADE, db_column='movimiento')
    fecha = models.DateField(default=timezone.now, blank=True)
    detalle = models.TextField(blank=True)
    archivo = models.ImageField(upload_to='evidencias/', blank=True)

    def __str__(self):
        return f'{self.movimiento.cliente.nombre} - {self.movimiento.fecha}'

    def imagen_thumbnail(self):
        if self.imagen:
            return mark_safe(f'<img src="{self.imagen.url}" width="50" height="50" />')
        return ""
    imagen_thumbnail.short_description = 'Imagen'
