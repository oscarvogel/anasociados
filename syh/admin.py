from django.contrib import admin
from usuarios.models import Profile
from .models import Cliente, Area, Movimientos

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
    list_filter = ('id', 'cliente', 'detalle')
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

@admin.register(Movimientos)
class MovimientosAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'area', 'periodo', 'hallazgo')
    list_per_page = 10
    list_max_show_all = 100
    ordering = ('-fecha', 'cliente', 'estado')
    search_fields = ('id', 'area__detalle', 'periodo', 'hallazgo')

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
            return ('cliente', 'area', 'periodo', 'estado')
        else:
            # Si es un cliente, limitamos los filtros a solo ciertos campos
            return ('area', 'periodo', 'estado')
        
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

    # def changelist_view(self, request, extra_context=None):
    #     response = super().changelist_view(request, extra_context)
    #     if hasattr(response, 'context_data'):
    #         for result in response.context_data['cl']:
    #             if result['estado'] == 'Incumplido':
    #                 result['row_class'] = 'row-incumplido'
    #             elif result['estado'] == 'Gestion':
    #                 result['row_class'] = 'row-en-gestion'
    #             elif result['estado'] == 'Cumplido':
    #                 result['row_class'] = 'row-cumplido'
    #     return response