from django.core.exceptions import ValidationError
from django.db import models

from syh.models import Area


class ContactoNotificacion(models.Model):
    """
    A quien le llega cada tipo de aviso.

    Esto vive en la base y no en el .env a proposito: el .env se edita
    preciso en el servidor y no se puede cambiar desde el panel. Acá se
    cambia desde el admin, sin reiniciar nada y sin depender de alguien
    con acceso root.

    Los telefonos se guardan normalizados (5493757677124) porque el gateway
    los exige en internacional y solo con digitos.
    """

    nombre = models.CharField(max_length=80, verbose_name="Nombre")
    telefono = models.CharField(
        max_length=32,
        unique=True,
        verbose_name="WhatsApp",
        help_text="Internacional, solo dígitos. Ej: 5493757677124.",
    )
    recibe_evidencias = models.BooleanField(
        default=True,
        verbose_name="Recibe avisos de evidencia",
        help_text="Le avisa cuando un responsable sube una foto de un hallazgo.",
    )
    recibe_alertas_operacion = models.BooleanField(
        default=False,
        verbose_name="Recibe alertas de operación",
        help_text="Le avisa si se cae el sitio, falla el backup o se para el worker.",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contacto de notificación"
        verbose_name_plural = "Contactos de notificación"
        ordering = ("nombre",)

    def __str__(self) -> str:
        roles = []
        if self.recibe_evidencias:
            roles.append("evidencias")
        if self.recibe_alertas_operacion:
            roles.append("operación")
        return f"{self.nombre} ({self.telefono}){' — ' + ', '.join(roles) if roles else ''}"

    def clean(self):
        from utiles.notificaciones import WhatsAppClient, WhatsAppError

        if not self.telefono:
            return
        try:
            self.telefono = WhatsAppClient().normalizar_telefono(self.telefono)
        except WhatsAppError as exc:
            raise ValidationError({"telefono": str(exc)}) from exc


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
    # El link del responsable y el del administrador son de la misma empresa y
    # area, pero NO hacen lo mismo. El del responsable sube evidencia; el del
    # administrador la aprueba o la rechaza, y eso mueve el hallazgo a Cumplido.
    # Si fuera el mismo link, que se filtrara uno permitiria forjar evidencia y
    # cerrar hallazgos con un solo token.
    puede_revisar = models.BooleanField(
        default=False,
        verbose_name="Puede revisar evidencias",
        help_text="Solo para el enlace del administrador.",
    )
    # El enlace de revision es POR CONTACTO, no uno solo por area: cada
    # administrador recibe el suyo y queda registrado quien aprobo o rechazo.
    # Con un link compartido por area no hay forma de saber quien decidio, y
    # `Evidencia.revisado_por` quedaba siempre en "sin identificar".
    # Nullable: los enlaces del responsable, y los de revision anteriores a
    # esto, no tienen contacto.
    contacto = models.ForeignKey(
        ContactoNotificacion,
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="enlaces_revision",
        verbose_name="Contacto administrador",
        help_text="Dueño del enlace de revisión.",
    )

    class Meta:
        verbose_name = "Enlace público de hallazgos"
        verbose_name_plural = "Enlaces públicos de hallazgos"
        ordering = ("-created_at",)

    def __str__(self):
        tipo = "revisión" if self.puede_revisar else "consulta"
        dueno = f" / {self.contacto.nombre}" if self.contacto_id else ""
        return (
            f"{self.cliente_id} / {self.area_id} ({tipo}){dueno}"
            f" — vence {self.expires_at:%d/%m/%Y}"
        )
