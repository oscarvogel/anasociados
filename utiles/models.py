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
