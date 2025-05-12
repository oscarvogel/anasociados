from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.utils import timezone

from syh.models import Area, Cliente

# Create your models here.

class TipoVencimientos(models.Model):
    
    TIPO_VENCIMIENTO = (
        ('Personal', 'Personal'),
        ('Moviles', 'Moviles'),
    )
    nombre = models.CharField(max_length=50)
    tipo = models.CharField(max_length=50, choices=TIPO_VENCIMIENTO, default='Personal')
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'Tipo de Vencimiento'
        verbose_name_plural = 'Tipos de Vencimientos'
        ordering = ['nombre']


class Movil(models.Model):
    
    empresa = models.ForeignKey('syh.Cliente', on_delete=models.CASCADE)
    patente = models.CharField(max_length=10)
    marca = models.CharField(max_length=30)
    modelo = models.CharField(max_length=30)
    anio = models.IntegerField()
    baja = models.BooleanField(default=False)

    def __str__(self):
        return self.patente
    
    class Meta:
        verbose_name = 'Movil'
        verbose_name_plural = 'Moviles'
        ordering = ['patente']
    
    def clean(self):
        
        ultimo_km = CargaCombustible.objects.filter(
            movil=self.movil
        ).aggregate(
            Max('km_hora')
        )['km_hora__max']
        
        if ultimo_km and self.km_hora <= ultimo_km:
            raise ValidationError({
                'km_hora': f'El kilometraje debe ser mayor al último registro ({ultimo_km})'
            })
        
class Vencimientos(models.Model):
    
    movil = models.ForeignKey(Movil, on_delete=models.CASCADE)
    tipo_vencimiento = models.ForeignKey(TipoVencimientos, on_delete=models.CASCADE, default=1)
    detalle = models.CharField(max_length=50)
    fecha = models.DateField()
    
    def __str__(self):
        return self.vencimiento
    
    class Meta:
        verbose_name = 'Vencimiento'
        verbose_name_plural = 'Vencimientos'
        ordering = ['-fecha', 'tipo_vencimiento']
        

class Personal(models.Model):
    
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    dni = models.CharField(max_length=8)
    cuit = models.CharField(max_length=13)
    baja = models.BooleanField(default=False)
    empresa = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_nacimiento = models.DateField()
    
    def __str__(self):
        return self.nombre + ' ' + self.apellido
    
    class Meta:
        verbose_name = 'Personal'
        verbose_name_plural = 'Personal'
        ordering = ['apellido', 'nombre']
        
class CargaCombustible(models.Model):
    
    TIPOS_COMBUSTIBLE = (
        ('Super', 'Super'),
        ('Infinia Nafta', 'Infinia Nafta'),
        ('Ultra', 'Ultra'),
        ('Infinia Diesel', 'Infinia Diesel'),
        ('Urea', 'Urea'),
    )
    
    chofer = models.ForeignKey(Personal, on_delete=models.CASCADE)
    movil = models.ForeignKey(Movil, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Cliente, on_delete=models.CASCADE, blank=True, null=True)
    fecha = models.DateField()
    litros = models.DecimalField(max_digits=10, decimal_places=2)
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    km_hora = models.IntegerField(verbose_name="Km/Hora")
    tipo_combustible = models.CharField(max_length=50, choices=TIPOS_COMBUSTIBLE, default='Ultra')
    
    def save(self, *args, **kwargs):
        # Validamos si el movil tiene un valor en el campo 'empresa'
        if self.movil and hasattr(self.movil, 'empresa') and self.movil.empresa:
            self.empresa = self.movil.empresa
        else:
            self.empresa = None  # Opcional: Si no hay empresa, podrías dejarlo en None o lanzar un error
        super(CargaCombustible, self).save(*args, **kwargs)

    
    def __str__(self):
        return str(self.fecha)
    
    class Meta:
        verbose_name = 'Carga de Combustible'
        verbose_name_plural = 'Cargas de Combustible'
        ordering = ['-fecha']
        
    
class Matafuegos(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, default='')
    area = models.ForeignKey(Area, on_delete=models.RESTRICT, default='')
    codigo_interno = models.CharField(max_length=20, default='')
    fecha_vencimiento = models.DateField(default=timezone.now)
    cantidad = models.IntegerField(default=0)
    ubicacion = models.CharField(max_length=100, default='')
    observaciones = models.TextField(blank=True, null=True, default='')
    capacidad = models.IntegerField(default=0)
    baja = models.BooleanField(default=False)
    fecha_baja = models.DateField(null=True, blank=True)
    mail_responsable = models.EmailField(max_length=254, blank=True, null=True)

    class Meta:
        verbose_name = "Matafuegos"
        verbose_name_plural = "Matafuegos"        
    
    def __str__(self):
        return f"{self.codigo_interno} - {self.cliente.nombre} - {self.area.nombre}"        