from reportlab.lib.pagesizes import letter
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from reportlab.lib.pagesizes import A4, landscape
from syh.forms import EmisionCarbonoForm, ExcesosVelocidadAdminForm, IndiceAccidentabilidadAdminForm
from usuarios.models import Profile
from utiles.impresiones import Impresiones, ImprimeHallazgos
from .models import Cliente, Area, EmisionCarbono, Evidencia, ExcesosVelocidad, IndiceAccidentabilidad, Movimientos, ParametroSistema
import matplotlib.pyplot as plt
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

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
    readonly_fields = ['id']  # Asegúrate de que el campo 'id' es solo de lectura
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
            return ('estado', 'cliente', AreaClienteFilter)
        else:
            # Si es un cliente, limitamos los filtros a solo ciertos campos
            return ('estado', AreaClienteFilter)
    
    # Acción para exportar a PDF
    actions = ['export_to_pdf']

    def export_to_pdf(self, request, queryset):
        impresion = ImprimeHallazgos()
        # Obtener el cliente y el área para el título
        return impresion.imprime_hallazgo(queryset)
        

    export_to_pdf.short_description = "Exportar a PDF"

    def get_list_display(self, request):
        if request.user.is_superuser:
            # Si es superusuario, mostramos todos los campos
            return ('id', 'cliente', 'area', 'periodo', 'hallazgo', 'estado', 'fecha')
        else:
            # Si es cliente, mostramos una vista reducida
            return ('id', 'area', 'periodo', 'hallazgo', 'estado')



@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ('parametro', 'valor', 'detalle')
    search_fields = ('parametro', 'valor', 'detalle')
    list_filter = ('parametro',)
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('parametro',)

@admin.register(EmisionCarbono)
class EmisionCarbonoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'fe', 'cantidad', 'cliente', 'fecha')
    search_fields = ('id', 'tipo', 'fe', 'cantidad', 'cliente__nombre', 'fecha')
    list_filter = ('cliente',)
    list_per_page = 10
    readonly_fields = ['periodo']
    form = EmisionCarbonoForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and 'fecha' in form.base_fields:
            form.base_fields['fecha'].initial = obj.fecha.strftime('%Y-%m-%d')
            form.base_fields['fecha'].widget.attrs['value'] = obj.fecha.strftime('%Y-%m-%d')
        return form
    
@admin.register(IndiceAccidentabilidad)
class IndiceAccidentabilidadAdmin(admin.ModelAdmin):
    form = IndiceAccidentabilidadAdminForm
    list_display = ('id', 'cliente', 'anio', 'mes', 'ACTP', 'ASTP', 'TPA', 'personal', 'hrs_hombres')
    search_fields = ('id', 'cliente__nombre', 'anio', 'mes', 'ACTP', 'ASTP', 'TPA', 'personal', 'hrs_hombres')
    list_filter = ('cliente', 'anio', 'mes')
    list_per_page = 10
    list_max_show_all = 100
    list_display_links = ('id',)
    ordering = ('-anio', '-mes')
    readonly_fields = ('id',)

# @admin.register(ExcesosVelocidad)
# class ExcesosVelocidadAdmin(admin.ModelAdmin):
#     form = ExcesosVelocidadAdminForm
#     list_display = ('id', 'cliente', 'anio', 'mes', 'semana', 'excesos')
#     search_fields = ('id', 'cliente__nombre', 'anio', 'mes', 'semana', 'excesos')
#     list_filter = ('cliente', 'anio', 'mes', 'semana')
#     list_per_page = 10
#     list_max_show_all = 100
#     list_display_links = ('id',)
#     ordering = ('-anio', '-mes', '-semana')
#     readonly_fields = ('id',)

#     def change_view(self, request, object_id, form_url='', extra_context=None):
#         extra_context = extra_context or {}
#         extra_context['form_template'] = 'admin/syh/excesosvelocidad/change_form.html'
#         return super(ExcesosVelocidadAdmin, self).change_view(
#             request, object_id, form_url, extra_context=extra_context)

#     def add_view(self, request, form_url='', extra_context=None):
#         extra_context = extra_context or {}
#         extra_context['form_template'] = 'admin/syh/excesosvelocidad/change_form.html'
#         return super(ExcesosVelocidadAdmin, self).add_view(
#             request, form_url, extra_context=extra_context)
    
#     class Media:
#         js = ('https://cdn.jsdelivr.net/npm/vue@2', 'admin/js/vue_app.js')