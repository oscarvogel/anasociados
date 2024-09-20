from django.db import models
from django.db.models import Count

# Create your models here.

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

    id = models.CharField(primary_key=True, max_length=10)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='cliente')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column='area')
    fecha = models.DateField()
    periodo = models.CharField(max_length=20)
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