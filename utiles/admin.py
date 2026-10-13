from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from utiles.models import AreaWhatsAppContacto
from utiles.notificaciones import WhatsAppClient, WhatsAppError


class AreaWhatsAppContactoForm(forms.ModelForm):
    class Meta:
        model = AreaWhatsAppContacto
        fields = ("area", "telefono")

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"]
        try:
            return WhatsAppClient().normalizar_telefono(telefono)
        except WhatsAppError as exc:
            raise ValidationError(str(exc)) from exc


@admin.register(AreaWhatsAppContacto)
class AreaWhatsAppContactoAdmin(admin.ModelAdmin):
    form = AreaWhatsAppContactoForm
    list_display = ("area", "mostrar_empresa", "telefono", "updated_at")
    list_select_related = ("area", "area__cliente")
    search_fields = ("area__detalle", "area__cliente__nombre", "telefono")
    readonly_fields = ("updated_at",)
    fields = ("area", "telefono", "updated_at")

    @admin.display(description="Empresa")
    def mostrar_empresa(self, obj):
        return obj.area.cliente.nombre

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
