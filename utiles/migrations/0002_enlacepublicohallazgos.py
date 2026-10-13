# Generated for temporary public links to WhatsApp finding summaries.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("utiles", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnlacePublicoHallazgos",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cliente_id", models.CharField(db_index=True, max_length=10)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "area",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="enlaces_publicos_hallazgos",
                        to="syh.area",
                    ),
                ),
            ],
            options={
                "verbose_name": "Enlace público de hallazgos",
                "verbose_name_plural": "Enlaces públicos de hallazgos",
                "ordering": ("-created_at",),
            },
        ),
    ]
