from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0006_rename_usuarios_us_fecha_h_2c1d8a_idx_usuarios_us_fecha_h_e126c8_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="areasprofile",
            name="telefono_whatsapp",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Número internacional, por ejemplo 5493764000000.",
                max_length=32,
                verbose_name="WhatsApp del encargado",
            ),
        ),
    ]
