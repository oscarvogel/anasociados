from django.contrib import admin
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from syh.forms import MovimientosForm
from usuarios.models import Profile
from utiles.funciones_usuario import FormatoFecha, dividir_texto
from utiles.impresiones import Impresiones
from .models import Cliente, Area, Evidencia, Movimientos, ParametroSistema
import io
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors

# Register your models here.
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'celular', 'email')
    search_fields = ('id', 'nombre', 'celular', 'email')
    list_filter = ('id', 'nombre', 'celular', 'email')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('nombre', 'celular', 'email')
    list_display_links = ('id',)
    ordering = ('id',)
    readonly_fields = ('id',)
    fieldsets = (
        (None, {
            'fields': ('id', 'nombre', 'celular', 'email')
        }),
    )
    add_fieldsets = (
        (None, {
            'fields': ('id', 'nombre', 'celular', 'email')
        }),
    )

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'detalle')
    search_fields = ('id', 'cliente', 'detalle')
    list_filter = ('cliente',)
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('cliente', 'detalle')
    list_display_links = ('id',)
    ordering = ('id',)
    readonly_fields = ('id',)
    fieldsets = (
        (None, {
            'fields': ('id', 'cliente', 'detalle')
        }),
    )
    add_fieldsets = (
        (None, {
            'fields': ('id', 'cliente', 'detalle')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Si el objeto ya existe (es una instancia existente)
            return ['parametro'] + self.readonly_fields
        return self.readonly_fields


# Creamos un filtro personalizado para filtrar áreas según el cliente del usuario
class AreaClienteFilter(SimpleListFilter):
    title = 'Área'  # Nombre que se mostrará en el filtro
    parameter_name = 'area'  # Parámetro que se usará en la URL

    def lookups(self, request, model_admin):
        # Si el usuario es superusuario, mostramos todas las áreas
        if request.user.is_superuser:
            return [(area.id, area.detalle) for area in Area.objects.all()]
        
        # Si no es superusuario, solo mostramos las áreas asociadas al cliente del usuario
        try:
            profile = Profile.objects.get(user=request.user)
            areas = Area.objects.filter(cliente=profile.cliente)
            return [(area.id, area.detalle) for area in areas]
        except Profile.DoesNotExist:
            return []  # Si no tiene perfil, no mostramos ninguna área

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(area__id=self.value())
        return queryset

# @admin.register(Evidencia)
class EvidenciaAdmin(admin.TabularInline):
    model = Evidencia
    extra = 1
    readonly_fields = ('imagen_thumbnail',)
    fields = ('fecha', 'detalle', 'imagen_thumbnail', 'archivo')

@admin.register(Movimientos)
class MovimientosAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'area', 'periodo', 'hallazgo')
    list_per_page = 10
    list_max_show_all = 100
    ordering = ('-fecha', 'cliente', 'estado')
    search_fields = ('id', 'area__detalle', 'periodo', 'hallazgo')
    inlines = [EvidenciaAdmin]
    # form = MovimientosForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Si el usuario es superuser, puede ver todos los registros
        if request.user.is_superuser:
            return qs
        # Si no es superuser, filtra los registros por el cliente asociado al usuario
        try:
            profile = Profile.objects.get(user=request.user)
            return qs.filter(cliente=profile.cliente)
        except Profile.DoesNotExist:
            return qs.none()  # Si el usuario no tiene un perfil, no verá ningún registro
    
    def get_list_filter(self, request):
        if request.user.is_superuser:
            # Si es superusuario, mostramos todos los filtros disponibles
            return ('cliente', AreaClienteFilter, ('fecha', DateFieldListFilter), 'periodo', 'estado')
        else:
            # Si es un cliente, limitamos los filtros a solo ciertos campos
            return (AreaClienteFilter, ('fecha', DateFieldListFilter), 'periodo', 'estado')
    
    # Acción para exportar a PDF
    actions = ['export_to_pdf']

    def export_to_pdf(self, request, queryset):
        impresion = Impresiones()
        impresion.inicia()
        impresion.ubicacion = {
            'Fecha': 10,
            'Periodo': 65,
            'Hallazgo': 120,
            'Estado': 500
        }
        # Obtener el cliente y el área para el título
        if queryset.exists():
            cliente = queryset.first().cliente
            area = queryset.first().area
            titulo = f"Reporte de Movimientos para {cliente} - Área: {area}"
        else:
            titulo = "Reporte de Movimientos"

        impresion.titulo = titulo
        # Crear el PDF
        impresion.cabecera()

        # Crear la tabla
        data = [
            ['Fecha', 'Periodo', 'Hallazgo', 'Estado']
        ]
        for movimiento in queryset:
            impresion.fila -=10
            impresion.pdf.drawString(x=impresion.ubicacion['Fecha'], y=impresion.fila, text=FormatoFecha(movimiento.fecha, formato='dma'))
            impresion.pdf.drawString(x=impresion.ubicacion['Periodo'], y=impresion.fila, text=str(movimiento.periodo))
            impresion.pdf.drawString(x=impresion.ubicacion['Estado'], y=impresion.fila, text=str(movimiento.estado))
            lineas = dividir_texto(movimiento.hallazgo, 80)
            for linea in lineas:
                impresion.pdf.drawString(x=impresion.ubicacion['Hallazgo'], y=impresion.fila, text=linea)
                impresion.fila -= 10
            # Paragraph(movimiento.hallazgo, getSampleStyleSheet()['BodyText'])
            data.append([
                str(movimiento.fecha),
                movimiento.periodo,
                movimiento.hallazgo,
                movimiento.estado
            ])
        impresion.finaliza()
        return impresion.response
        

    export_to_pdf.short_description = "Exportar a PDF"

    def get_list_display(self, request):
        if request.user.is_superuser:
            # Si es superusuario, mostramos todos los campos
            return ('id', 'cliente', 'area', 'periodo', 'hallazgo', 'estado', 'fecha')
        else:
            # Si es cliente, mostramos una vista reducida
            return ('id', 'area', 'periodo', 'hallazgo', 'estado')
        
    def get_list_display(self, request):
        if request.user.is_superuser:
            return ('id', 'cliente', 'area', 'periodo', 'hallazgo', 'estado', 'fecha')
        else:
            return ('id', 'area', 'periodo', 'hallazgo', 'estado')

@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ('parametro', 'valor', 'detalle')
    search_fields = ('parametro', 'valor', 'detalle')
    list_filter = ('parametro',)
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('parametro',)
