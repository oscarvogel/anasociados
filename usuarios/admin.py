from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import AreasProfile, Profile, UsuarioIngreso, UsuarioMenuAcceso
from utiles.notificaciones import WhatsAppClient, WhatsAppError


class AreasProfileAdminForm(forms.ModelForm):
    class Meta:
        model = AreasProfile
        fields = ('user', 'area', 'telefono_whatsapp')

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        area = cleaned_data.get('area')
        if user and area:
            try:
                perfil = user.profile
            except Profile.DoesNotExist:
                self.add_error('user', 'El usuario debe tener un perfil de empresa asignado.')
            else:
                if perfil.cliente_id != area.cliente_id:
                    self.add_error('area', 'El área debe pertenecer a la empresa asignada al perfil del usuario.')
        return cleaned_data

    def clean_telefono_whatsapp(self):
        telefono = self.cleaned_data['telefono_whatsapp']
        if not telefono.strip():
            return ''
        try:
            return WhatsAppClient().normalizar_telefono(telefono)
        except WhatsAppError as exc:
            raise ValidationError(str(exc)) from exc

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cliente')
    search_fields = ('user', 'cliente')
    list_filter = ('user', 'cliente')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('cliente',)
    list_display_links = ('user',)
    ordering = ('user',)
    
@admin.register(AreasProfile)
class AreasProfileAdmin(admin.ModelAdmin):
    form = AreasProfileAdminForm
    # telefono_whatsapp a la vista: sin esto hay que abrir 8 filas una por
    # una para descubrir quien todavia no tiene numero cargado.
    list_display = ('user', 'area', 'telefono_whatsapp_display')
    search_fields = ('user__username', 'user__first_name', 'area__detalle', 'telefono_whatsapp')
    list_filter = ('user', 'area')
    list_per_page = 25
    list_max_show_all = 200
    list_editable = ('area',)
    list_display_links = ('user',)
    ordering = ('user', 'area')
    actions = ('copiar_whatsapp_a_todas_las_areas', 'borrar_whatsapp_del_usuario')

    @admin.display(description="WhatsApp", ordering="telefono_whatsapp")
    def telefono_whatsapp_display(self, obj):
        return obj.telefono_whatsapp or "— sin cargar —"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop('copiar_whatsapp_a_todas_las_areas', None)
            actions.pop('borrar_whatsapp_del_usuario', None)
        return actions

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('user', 'area', 'telefono_whatsapp')
        return ('user', 'area')

    @admin.action(description="Copiar WhatsApp a TODAS las áreas del usuario")
    def copiar_whatsapp_a_todas_las_areas(self, request, queryset):
        """
        Un encargado con 4 areas tiene el mismo celular en las 4 filas.
        Copiar el numero a mano 4 veces se vuelve un problema cuando el
        numero cambia. Con esto se selecciona UNA fila y se completa el resto.
        """
        if not request.user.is_superuser:
            self.message_user(
                request, "Solo un superusuario puede modificar el WhatsApp.",
                messages.WARNING,
            )
            return

        # Un numero por usuario: el primero de la seleccion que tenga alguno.
        por_usuario = {}
        for asignacion in queryset.select_related("user"):
            telefono = (asignacion.telefono_whatsapp or "").strip()
            if telefono and asignacion.user_id not in por_usuario:
                por_usuario[asignacion.user_id] = telefono

        if not por_usuario:
            self.message_user(
                request,
                "Ninguna de las filas seleccionadas tiene un WhatsApp cargado. "
                "Cargalo primero en una de ellas.",
                messages.WARNING,
            )
            return

        actualizados = 0
        vacios = []
        for user_id, telefono in por_usuario.items():
            areas = AreasProfile.objects.filter(user_id=user_id)
            cambios = areas.exclude(telefono_whatsapp=telefono).update(telefono_whatsapp=telefono)
            actualizados += cambios
            if not areas.filter(telefono_whatsapp__gt="").exists():
                vacios.append(str(user_id))

        mensaje = f"Se actualizaron {actualizados} asignaciones."
        if vacios:
            mensaje += " Sin numero: " + ", ".join(vacios)
        self.message_user(request, mensaje, messages.SUCCESS)

    @admin.action(description="Vaciar el WhatsApp de TODAS las áreas del usuario")
    def borrar_whatsapp_del_usuario(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(
                request, "Solo un superusuario puede modificar el WhatsApp.",
                messages.WARNING,
            )
            return

        user_ids = set(queryset.values_list("user_id", flat=True))
        # QuerySet.update() devuelve un int, no una tupla.
        borrados = AreasProfile.objects.filter(user_id__in=user_ids).update(telefono_whatsapp="")
        self.message_user(
            request,
            f"Se vaciaron {borrados} asignaciones.",
            messages.SUCCESS,
        )


@admin.register(UsuarioIngreso)
class UsuarioIngresoAdmin(admin.ModelAdmin):
    list_display = ('user', 'fecha_hora')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('fecha_hora',)
    ordering = ('-fecha_hora',)


@admin.register(UsuarioMenuAcceso)
class UsuarioMenuAccesoAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu_nombre', 'fecha_hora')
    search_fields = ('user__username', 'menu_nombre', 'menu_codigo', 'path')
    list_filter = ('menu_nombre', 'fecha_hora')
    ordering = ('-fecha_hora',)
