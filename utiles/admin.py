from django.contrib import admin
from django.utils import timezone

from utiles.models import EnlacePublicoHallazgos


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
