from pydoc import cli
import uuid
from django.db.models import Avg


from datetime import datetime, timedelta
from django.db import models
from django.db.models import Count
from django.utils.html import mark_safe
from django.utils import timezone

# Create your models here.

from django.db import models


ESTADO_CHOICES = [
    ('SI', 'SI'),
    ('NO', 'NO'),
    ('NA', 'NA'),
]

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

def generate_unique_id(longitud=10):
    return str(uuid.uuid4())[:longitud]

class Movimientos(models.Model):

    ESTADO_CHOICES = [
        ('Gestión en Curso', 'Gestión en Curso'),
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

    id = models.CharField(primary_key=True, max_length=20, default=generate_unique_id(20))
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='cliente')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column='area')
    fecha = models.DateField()
    periodo = models.CharField(max_length=20, choices=PERIODO_CHOICES)
    hallazgo = models.TextField()
    responsable = models.CharField(max_length=80)
    plazo = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Gestión en Curso')
    fecha_cumplimiento = models.DateField(null=True, blank=True)
    ubicacion = models.CharField(max_length=100, null=True, blank=True)
    fecha_realizado = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.cliente.nombre} - {self.fecha}'
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "movimientos"
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ["cliente", "fecha"]
        managed = False

    @classmethod
    def contar_tareas_por_estado(cls, cliente, area):
        """
        Devuelve la cantidad de tareas según el estado para un cliente específico.
        """
        if cliente == 'Todos':
            queryset = cls.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_CHOICES]).values('estado').annotate(cantidad=Count('estado'))
        else:
            queryset = cls.objects.filter(cliente=cliente,estado__in=[estado[0] for estado in cls.ESTADO_CHOICES]).values('estado').annotate(cantidad=Count('estado'))
        
        if area:
            queryset = queryset.filter(area=area)
        
        return queryset
    
    @classmethod
    def obtener_hallazgos_por_estado_y_mes(cls, cliente):
        # Obtener la fecha de hace 12 meses a partir de hoy
        hace_un_anio = datetime.now() - timedelta(days=365)
        if cliente == 'Todos':
            datos = cls.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_CHOICES], fecha__gte=hace_un_anio).values('periodo', 'estado').annotate(cantidad=Count('id')).order_by('fecha', 'estado')
        else:
            datos = cls.objects.filter(cliente=cliente, estado__in=[estado[0] for estado in cls.ESTADO_CHOICES], fecha__gte=hace_un_anio).values('periodo', 'estado').annotate(cantidad=Count('id')).order_by('fecha', 'estado')
        
        datos_mes_estado = {}
        for dato in datos:
            if dato['periodo']:
                mes = dato['periodo']
            else:
                mes = 'No disponible'
            if mes not in datos_mes_estado:
                datos_mes_estado[mes] = {estado: 0 for estado, _ in cls.ESTADO_CHOICES}
            datos_mes_estado[mes][dato['estado'].capitalize()] = dato['cantidad']
        # Convertir los datos en un formato adecuado para Chart.js
        labels = list(datos_mes_estado.keys())
        estados = [estado for estado, _ in cls.ESTADO_CHOICES]

        datasets = []
        colores = [
            'rgba(255, 99, 132)',  # Rojo
            'rgba(54, 162, 235)',  # Azul
            'rgba(75, 192, 192)',  # Verde
            'rgba(255, 206, 86)',  # Amarillo
            'rgba(153, 102, 255)', # Morado
            'rgba(255, 159, 64)'   # Naranja
        ]
        for index, estado in enumerate(estados):
            datasets.append({
                'label': estado,
                'data': [datos_mes_estado[mes][estado] for mes in labels],
                'backgroundColor': colores[index % len(colores)]  # Asigna un color de la lista
            })
        return datasets, labels
    
    @classmethod
    def plazo_promedio(cls, cliente):
        promedio_general = Movimientos.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_CHOICES]).aggregate(promedio=Avg('plazo'))['promedio']
        if cliente == 'Todos':
            promedios_por_cliente = Movimientos.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_CHOICES]).values('cliente__nombre').annotate(promedio_plazo=Avg('plazo'))
        else:
            promedios_por_cliente = Movimientos.objects.filter(cliente=cliente).values('cliente__nombre').annotate(promedio_plazo=Avg('plazo'))
        return promedios_por_cliente, promedio_general


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

class EmisionCarbono(models.Model):

    TIPO_CHOICES = [
        ('Diesel', 'Diesel'),
        ('Nafta', 'Nafta'),
        ('Aceite para Motores', 'Aceite para Motores'),
        ('Aceite Hidráulico', 'Aceite Hidráulico'),
        ('Aceite Lubricantes de Cadena', 'Aceite Lubricantes de Cadena'),
    ]
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=80, default='', choices=TIPO_CHOICES)
    fe = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='FE (CO2/litro)')
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Cantidad consumida")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, default='')
    fecha = models.DateField(default=timezone.now)
    periodo = models.CharField(max_length=7, blank=True, editable=False)

    def save(self, *args, **kwargs):
        self.periodo = self.fecha.strftime('%Y-%m')
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.tipo
    
    @classmethod
    def calcular_emisiones(cls, cliente_id=None):
        if cliente_id and cliente_id != 'Todos':
            emisiones = cls.objects.filter(cliente_id=cliente_id)
        else:
            emisiones = cls.objects.all()
        
        datos = {}
        for emision in emisiones:
            periodo = emision.fecha.strftime('%Y-%m')
            if periodo not in datos:
                datos[periodo] = 0
            datos[periodo] += emision.cantidad * emision.fe
        
        return sorted(datos.items())

class CabeceraLCO(models.Model):

    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, default='')


class DetalleLCO(models.Model):
    id = models.AutoField(primary_key=True)
    cabecera_lco = models.ForeignKey(CabeceraLCO, on_delete=models.CASCADE, default='')
    detalle_lco = models.CharField(max_length=100, default='')
    cumplimiento = models.CharField(max_length=80, default='', choices=ESTADO_CHOICES)
    observaciones = models.CharField(max_length=100, default='', null=True, blank=True)
    cantidad = models.IntegerField(default=0)


class CabMovLCO(models.Model):

    ESTADO_CHOICES_CAB = [
        ('PENDIENTE', 'PENDIENTE'),
        ('CERRADO', 'CERRADO'),
    ]

    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, default='')
    fecha_lco = models.DateField(default=timezone.now)
    cabecera_lco = models.ForeignKey(CabeceraLCO, on_delete=models.CASCADE, default='')
    estado = models.CharField(max_length=80, choices=ESTADO_CHOICES_CAB, default='PENDIENTE')

class MovimientosLCO(models.Model):

    id = models.AutoField(primary_key=True)
    cabecera_lco = models.ForeignKey(CabMovLCO, on_delete=models.CASCADE, default='')
    detalle_lco = models.ForeignKey(DetalleLCO, on_delete=models.CASCADE, default='')
    plazo = models.IntegerField(default=0)
    cumplimiento = models.CharField(max_length=80, default='', choices=ESTADO_CHOICES)
    observaciones = models.CharField(max_length=250, default='', null=True, blank=True)
    cantidad = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.cabecera_lco.nombre} - {self.detalle_lco.detalle_lco}'

    class Meta:
        verbose_name = "Movimiento LCO"
        verbose_name_plural = "Movimientos LCO"
        ordering = ["cabecera_lco", "detalle_lco"]


class IndiceAccidentabilidad(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, default='')
    anio = models.IntegerField(default=0, verbose_name="Año")
    mes = models.IntegerField(default=0)
    ACTP = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Accidentes con Tiempo Perdido (ACTP)")
    ASTP = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Accidentes Sin Tiempo Perdido (ASTP)")
    TPA = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tiempo Perdido por Accidente (TPA)")
    personal = models.IntegerField(default=0, verbose_name="Número Total de Trabajadores (T)")
    hrs_hombres = models.IntegerField(default=0, verbose_name="Total de Horas Hombre (HH)")

    class Meta:
        verbose_name = "Indice de Accidentabilidad"
        verbose_name_plural = "Indices de Accidentabilidad"


class ExcesosVelocidad(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, default='')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, default='')
    anio = models.IntegerField(default=0, verbose_name="Año")
    mes = models.IntegerField(default=0)
    semana = models.IntegerField(default=0)
    excesos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Excesos de Velocidad"
        verbose_name_plural = "Excesos de Velocidad"