import uuid

from django.db.models import Avg, Q

from datetime import date, datetime, timedelta
from django.db import models
from django.db.models import Count
from django.utils.html import mark_safe
from django.utils import timezone
import matplotlib.pyplot as plt

# Create your models here.

from django.db import models

from core_an import settings
from utiles.funciones_usuario import clean_filename


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

    @classmethod
    def obtener_parametro(cls, parametro_deseado, valor_por_defecto):
        try:
            # Intenta obtener el parámetro existente
            parametro = cls.objects.get(parametro=parametro_deseado).valor
        except cls.DoesNotExist:
            # Si no existe, crea uno nuevo
            parametro = cls.objects.create(parametro=parametro_deseado, valor=valor_por_defecto).valor

        return parametro

class Cliente(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    nombre = models.CharField(max_length=100)
    celular = models.CharField(max_length=80, blank=True, null=True)
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
    email = models.EmailField()

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


class NaturalezaHallazgo(models.Model):
    id = models.AutoField(primary_key=True)
    naturaleza = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.naturaleza

    class Meta:
        verbose_name = "Naturaleza Hallazgo"
        verbose_name_plural = "Naturaleza Hallazgos"
        ordering = ["naturaleza"]

class Movimientos(models.Model):

    ESTADO_CHOICES = [
        ('Gestión en Curso', 'Gestión en Curso'),
        ('Cumplido', 'Cumplido'),
        ('Incumplido', 'Incumplido'),
        ('Desafectado', 'Desafectado'),
    ]
    
    ESTADO_LISTADO = [
        ('Gestión en Curso', 'Gestión en Curso'),
        ('Cumplido', 'Cumplido'),
        ('Incumplido', 'Incumplido'),
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

    # Estados relevantes (mantenemos ambas versiones para comparar)
    ESTADOS_A_MOSTRAR = {
        'cumplido': 'Cumplido',
        'incumplido': 'Incumplido',
        'gestion en curso': 'Gestion en Curso',
    }
    
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
    # ubicacion = models.CharField(max_length=100, null=True, blank=True)
    fecha_realizado = models.DateField(null=True, blank=True)
    naturaleza_hallazgo = models.ForeignKey(NaturalezaHallazgo, on_delete=models.CASCADE, default=1)
    observaciones = models.TextField(null=True, blank=True)

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
    def contar_tareas_por_estado_vista(cls, cliente, area):
        """
        Devuelve la cantidad de tareas según el estado para un cliente específico.
        """
        if cliente == 'Todos':
            queryset = cls.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_LISTADO]).values('estado').order_by('estado').annotate(cantidad=Count('estado'))
        else:
            queryset = cls.objects.filter(cliente=cliente,estado__in=[estado[0] for estado in cls.ESTADO_LISTADO]).values('estado').order_by('estado').annotate(cantidad=Count('estado'))
        
        if area:
            queryset = queryset.filter(area=area)
        
        return queryset
    
    @classmethod
    def obtener_hallazgos_por_estado_y_mes(cls, cliente):
        # Obtener la fecha de hace 12 meses a partir de hoy
        hace_un_anio = datetime.now() - timedelta(days=365)
        if cliente == 'Todos':
            datos = cls.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_LISTADO], fecha__gte=hace_un_anio).values('periodo', 'estado').annotate(cantidad=Count('id')).order_by('fecha', 'estado')
        else:
            datos = cls.objects.filter(cliente=cliente, estado__in=[estado[0] for estado in cls.ESTADO_LISTADO], fecha__gte=hace_un_anio).values('periodo', 'estado').annotate(cantidad=Count('id')).order_by('fecha', 'estado')
        
        datos_mes_estado = {}
        for dato in datos:
            if dato['periodo']:
                mes = dato['periodo']
            else:
                mes = 'No disponible'
            if mes not in datos_mes_estado:
                datos_mes_estado[mes] = {estado: 0 for estado, _ in cls.ESTADO_LISTADO}
            datos_mes_estado[mes][dato['estado'].capitalize()] = dato['cantidad']
        # Convertir los datos en un formato adecuado para Chart.js
        labels = list(datos_mes_estado.keys())
        estados = [estado for estado, _ in cls.ESTADO_LISTADO]

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
        if cliente == 'Todos':
            promedio_general = Movimientos.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_LISTADO]).aggregate(promedio=Avg('plazo'))['promedio']
            promedios_por_cliente = Movimientos.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_LISTADO]).values('cliente__nombre').annotate(promedio_plazo=Avg('plazo'))
        else:
            promedios_por_cliente = Movimientos.objects.filter(cliente=cliente).values('cliente__nombre').annotate(promedio_plazo=Avg('plazo'))
            promedio_general = Movimientos.objects.filter(estado__in=[estado[0] for estado in cls.ESTADO_LISTADO], cliente=cliente).aggregate(promedio=Avg('plazo'))['promedio']
        return promedios_por_cliente, promedio_general
    
    
    @classmethod
    def contar_tareas_por_estado(cls, cliente, area):
        """
        Devuelve la cantidad de tareas según el estado para un cliente específico,
        normalizando los estados de manera simple.
        """
        # Crear el queryset base
        if cliente == 'Todos':
            queryset = cls.objects.all()
        else:
            queryset = cls.objects.filter(cliente=cliente)
            
        if area:
            queryset = queryset.filter(area=area)
            
        # Filtrar por los estados que nos interesan
        estados_lower = list(cls.ESTADOS_A_MOSTRAR.keys())
        queryset = (
            queryset
            # .filter(estado__iregex=r'^(' + '|'.join(estados_lower) + ')$')
            .filter(estado__in=[estado[0] for estado in cls.ESTADO_LISTADO])
            .values('estado')
            .annotate(cantidad=Count('id'))
            .order_by('estado')
        )
        return queryset

    @classmethod
    def obtener_datos_tareas(cls, cliente, area=None):
        datos = cls.contar_tareas_por_estado(cliente, area)
        return datos
    
    @classmethod
    def generar_grafico_torta(cls, cliente, area=None):
        """
        Genera y guarda un gráfico de torta basado en el conteo de tareas por estado.
        Retorna la ruta del archivo guardado.
        """
        # Obtener los datos usando el método existente
        datos = cls.contar_tareas_por_estado(cliente, area)
        
        # Preparar los datos para el gráfico
        estados = []
        cantidades = []
        
        # Definir colores específicos para cada estado
        colores = {
            'cumplido': '#99FF99',     # Verde claro
            'incumplido': '#FF9999',   # Rojo claro
            'gestion en curso': '#66B2FF',  # Azul claro
            'desafectado': '#FF9999',   # Rojo claro
        }
        
        # Convertir datos para el gráfico
        for item in datos:
            estado_original = unidecode(item['estado'].lower())
            # Usar el nombre para mostrar si existe, si no usar el original
            estado_mostrar = cls.ESTADOS_A_MOSTRAR.get(estado_original, item['estado'])
            estados.append(estado_mostrar)
            cantidades.append(item['cantidad'])

        # Si no hay datos, crear un gráfico vacío
        if not cantidades:
            fig = plt.figure(figsize=(10, 8))
            plt.text(0.5, 0.5, 'No hay datos disponibles', 
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=plt.gca().transAxes)
        else:
            # Crear el gráfico
            fig = plt.figure(figsize=(10, 8))
            patches, texts, autotexts = plt.pie(
                cantidades, 
                labels=estados,
                colors=[colores[estado.lower()] for estado in estados], 
                autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100.*sum(cantidades)):d})',
                startangle=90
            )
            
            # Mejorar la legibilidad de las etiquetas
            plt.setp(autotexts, size=9, weight="bold")
            plt.setp(texts, size=9)
        
        # Añadir título
        titulo = f'Distribución de Tareas'
        if area:
            titulo += f' - {area}'
        plt.title(titulo, pad=20, size=12, weight="bold")
        
        # Ajustar el diseño
        plt.axis('equal')
        
        # # Crear directorio para gráficos si no existe
        # graficos_dir = os.path.join(settings.MEDIA_ROOT, 'graficos')
        # os.makedirs(graficos_dir, exist_ok=True)
                
        # # En el método generar_grafico_torta:
        # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # nombre_base = f'tareas_torta_{cliente}'
        # if area:
        #     nombre_archivo = f'tareas_torta_{cliente}_{area}_{timestamp}.png'
        
        # nombre_base = clean_filename(nombre_base)
        # nombre_archivo = f'{nombre_base}_{timestamp}.png'
        nombre_archivo = f'grafico_torta.png'

        # Limpiar caracteres no válidos para nombre de archivo
        # nombre_archivo = "".join(x for x in nombre_archivo if x.isalnum() or x in ['_', '-', '.'])
        # ruta_archivo = os.path.join(graficos_dir, nombre_archivo)
        
        # Guardar el gráfico
        plt.savefig(nombre_archivo, bbox_inches='tight', dpi=300, facecolor='white')
        plt.close(fig)  # Cerrar la figura para liberar memoria
        
        # Retornar la ruta relativa para acceder desde la URL
        # return os.path.join('graficos', nombre_archivo)
        return nombre_archivo
        # return datos

    @classmethod
    def obtener_url_grafico(cls, cliente, area=None):
        """
        Genera el gráfico y retorna su URL.
        """
        ruta_relativa = cls.generar_grafico_torta(cliente, area)
        # return os.path.join(settings.MEDIA_URL, ruta_relativa)
        return ruta_relativa
    
    @classmethod
    def get_porcentaje_cumplidos_por_area(cls, cliente, fecha_desde, fecha_hasta):
        """
        Devuelve el porcentaje de cumplidos por área para un cliente dado y un rango de fechas.
        """
        movimientos = cls.objects.filter(
            cliente=cliente, 
            fecha__range=(fecha_desde, fecha_hasta),
            estado__in=['Cumplido', 'Incumplido', 'Gestion en curso']
        )
        areas = movimientos.values('area__detalle').distinct()

        resultados = {}
        for area in areas:
            area_nombre = area['area__detalle']
            total_movimientos = movimientos.filter(area__detalle=area_nombre).count()
            cumplidos = movimientos.filter(area__detalle=area_nombre, estado='Cumplido').count()
            porcentaje_cumplidos = round((cumplidos / total_movimientos) * 100 if total_movimientos > 0 else 0, 2)

            resultados[area_nombre] = porcentaje_cumplidos
        print(resultados)
        return resultados
    
    @classmethod
    def obtener_grafico_cumplidos_por_area(cls, cliente_id):
        # Obtén los datos
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(cliente_id, 
                                                                   fecha_desde=date(2024,1,1), fecha_hasta=date.today())

        # Ordena los datos de mayor a menor
        ordenados = sorted(resultados.items(), key=lambda x: x[1], reverse=True)

        # Separa las etiquetas y los valores
        etiquetas = [item[0] for item in ordenados]
        valores = [item[1] for item in ordenados]

        # Crea el gráfico
        plt.figure(figsize=(10, 6))
        plt.bar(etiquetas, valores, color='green', alpha=0.5)
        plt.xlabel('Área')
        plt.ylabel('Porcentaje de cumplidos')
        plt.title('Porcentaje de cumplidos por área')
        plt.xticks(rotation=90)  # Rota las etiquetas para que sean más legibles

        nombre_archivo = 'grafico_porcentaje_cumplidos.png'
        # Guarda el gráfico como una imagen
        plt.savefig(nombre_archivo, bbox_inches='tight')

        # Cierra la figura para liberar recursos
        plt.close()
        return nombre_archivo

    
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
    
    @classmethod
    def generar_grafico_emisiones(cls, cliente_id=None):
        datos = cls.calcular_emisiones(cliente_id)
        
        # Extraer los datos de los períodos y emisiones
        periodos = [item[0] for item in datos]
        emisiones = [item[1] for item in datos]

        # Crear el gráfico
        fig = plt.figure(figsize=(10, 6))
        plt.plot(periodos, emisiones, marker='o')
        plt.title('Emisiones de CO2 por Periodo')
        plt.xlabel('Periodo')
        plt.ylabel('Emisiones (CO2/litro)')
        plt.grid(True)

        nombre_archivo = f'grafico_emisiones.png'
        # Guardar el gráfico
        plt.savefig(nombre_archivo, bbox_inches='tight', dpi=300, facecolor='white')
        plt.close(fig)  # Cerrar la figura para liberar memoria
        
        # Retornar la ruta relativa para acceder desde la URL
        # return os.path.join('graficos', nombre_archivo)
        return nombre_archivo


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
    
    @staticmethod
    def calcular_indices(cliente):
        hoy = timezone.now().date()
        hace_doce_meses = hoy - timedelta(days=365)

        # Crear una lista de (anio, mes) en el rango de los últimos 12 meses
        meses = []
        for i in range(12):
            mes = hoy.month - i
            anio = hoy.year
            if mes <= 0:
                mes += 12
                anio -= 1
            meses.append((anio, mes))
        
        # Filtrar los datos que coincidan con los (anio, mes) generados
        query = Q()
        for anio, mes in meses:
            query |= Q(anio=anio, mes=mes)
        
        registros = IndiceAccidentabilidad.objects.filter(query)
        if cliente:
            registros = registros.filter(cliente=cliente)

        total_ACTP = sum([r.ACTP for r in registros])
        total_ASTP = sum([r.ASTP for r in registros])
        total_TPA = sum([r.TPA for r in registros])
        total_horas_hombre = sum([r.hrs_hombres for r in registros])
        total_personal = sum([r.personal for r in registros])

        print(registros.query)
        if total_horas_hombre == 0:
            indice_frecuencia = 0
            indice_gravedad = 0
            tasa_riesgo = 0
        else:
            indice_frecuencia = (total_ACTP / total_horas_hombre) * 1000000
            indice_gravedad = (total_TPA / total_horas_hombre) * 1000000
            tasa_riesgo = (total_ASTP / total_horas_hombre) * 1000000

        if total_personal == 0:
            indice_accidentabilidad = 0
        else:
            indice_accidentabilidad = (total_ACTP / total_personal) * 1000

        return {
            'indice_frecuencia': indice_frecuencia,
            'indice_gravedad': indice_gravedad,
            'indice_accidentabilidad': indice_accidentabilidad,
            'tasa_riesgo': tasa_riesgo
        }

class ExcesosVelocidad(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, default='')
    # area = models.ForeignKey(Area, on_delete=models.CASCADE, default='')
    anio = models.IntegerField(default=0, verbose_name="Año")
    mes = models.IntegerField(default=0)
    semana = models.IntegerField(default=0)
    excesos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Excesos de Velocidad"
        verbose_name_plural = "Excesos de Velocidad"

    @classmethod
    def chart_view(cls, cliente_id):

        if cliente_id:
            data = cls.objects.filter(cliente_id=cliente_id).values('mes').annotate(total_excesos=models.Sum('excesos')).order_by('mes')
        else:
            data = cls.objects.values('mes').annotate(total_excesos=models.Sum('excesos')).order_by('mes')

        return data
    
    @classmethod
    def genera_grafico_excesos(cls, cliente_id):
        datos = cls.chart_view(cliente_id)
        
        # Extraer los datos de los períodos y emisiones
        periodos = [item['mes'] for item in datos]
        excesos = [item['total_excesos'] for item in datos]

        # Crear el gráfico
        fig = plt.figure(figsize=(10, 6))
        plt.plot(periodos, excesos, marker='o')
        plt.title('Excesos de velocidad')
        plt.xlabel('Periodo')
        plt.ylabel('Excesos (km/h)')
        plt.grid(True)

        nombre_archivo = f'grafico_excesos.png'
        # Guardar el gráfico
        plt.savefig(nombre_archivo, bbox_inches='tight', dpi=300, facecolor='white')
        plt.close(fig)  # Cerrar la figura para liberar memoria
        
        # Retornar la ruta relativa para acceder desde la URL
        return nombre_archivo
