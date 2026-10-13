from django.db import models

from syh.models import Area


class AreaWhatsAppContacto(models.Model):
    """WhatsApp del encargado asociado a un área existente."""

    area = models.OneToOneField(
        Area,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="whatsapp_contacto",
    )
    telefono = models.CharField(
        max_length=32,
        help_text="Número internacional del encargado, por ejemplo 5493764000000.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contacto WhatsApp por área"
        verbose_name_plural = "Contactos WhatsApp por área"
        ordering = ("area__cliente__nombre", "area__detalle")

    def __str__(self):
        return f"{self.area.cliente.nombre} - {self.area.detalle}: {self.telefono}"


class EnlacePublicoHallazgos(models.Model):
    """Acceso temporal y revocable al detalle de hallazgos de un área."""

    area = models.ForeignKey(
        Area,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="enlaces_publicos_hallazgos",
    )
    cliente_id = models.CharField(max_length=10, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Enlace público de hallazgos"
        verbose_name_plural = "Enlaces públicos de hallazgos"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.cliente_id} / {self.area_id} — vence {self.expires_at:%d/%m/%Y}"
