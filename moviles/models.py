from django.db import models

from syh.models import Cliente

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