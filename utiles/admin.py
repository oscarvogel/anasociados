from django import forms
from django.contrib import admin
from django.utils import timezone

from utiles.models import ContactoNotificacion, EnlacePublicoHallazgos


@admin.register(ContactoNotificacion)
class ContactoNotificacionAdmin(admin.ModelAdmin):
    """
    A quien le llega cada aviso. Vive acá y no en el .env para que se pueda
    cambiar desde el panel, sin tocar el servidor ni reiniciar nada.
    """
    list_display = ("nombre", "telefono", "recibe_evidencias", "recibe_alertas_operacion", "activo")
    list_filter = ("activo", "recibe_evidencias", "recibe_alertas_operacion")
    search_fields = ("nombre", "telefono")
    list_editable = ("recibe_evidencias", "recibe_alertas_operacion", "activo")
    list_display_links = ("nombre",)
    list_per_page = 25
    ordering = ("nombre",)
    form = forms.models.ModelForm

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


@admin.register(EnlacePublicoHallazgos)
class EnlacePublicoHallazgosAdmin(admin.ModelAdmin):
    list_display = ("cliente_id", "area", "created_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at", "expires_at")
    search_fields = ("cliente_id", "area__detalle", "area__cliente__nombre")
    readonly_fields = (
        "area", "cliente_id", "token_hash", "created_at", "expires_at", "revoked_at",
    )
    actions = ("revocar_enlaces",)

    @admin.action(description="Revocar enlaces seleccionados")
    def revocar_enlaces(self, request, queryset):
        queryset.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
