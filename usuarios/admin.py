from django import forms
from django.contrib import admin
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
    list_display = ('user', 'area')
    search_fields = ('user', 'area')
    list_filter = ('user', 'area')
    list_per_page = 10
    list_max_show_all = 100
    list_editable = ('area',)
    list_display_links = ('user',)
    ordering = ('user',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('user', 'area', 'telefono_whatsapp')
        return ('user', 'area')


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
