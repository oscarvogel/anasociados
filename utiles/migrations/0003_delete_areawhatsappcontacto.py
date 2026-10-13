from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("utiles", "0002_enlacepublicohallazgos"),
        ("usuarios", "0007_add_areasprofile_whatsapp"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AreaWhatsAppContacto",
        ),
    ]
