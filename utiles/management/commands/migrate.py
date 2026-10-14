"""`migrate` que crea las tablas `managed = False` cuando corre bajo `test`.

Fuera de los tests este comando se comporta exactamente como el de Django: en
produccion esas tablas ya existen y las tiene que crear el proceso externo, no
Django. La condicion es explicita (`test` en sys.argv) para que nunca se
confunda una cosa con la otra.

Vive en la app `utiles` porque es la que ya aporta comandos de gestion y es la
unica forma de que Django lo encuentre: los comandos se buscan solo dentro de
apps instaladas.
"""
import sys

from django.core.management.commands.migrate import Command as MigrateBase

from core_an.tablas_externas import DDL_ANTES_DE_MIGRAR, DDL_DESPUES_DE_MIGRAR, ejecutar


class Command(MigrateBase):
    def handle(self, *args, **options):
        bajo_test = "test" in sys.argv
        if bajo_test:
            ejecutar(DDL_ANTES_DE_MIGRAR)
        resultado = super().handle(*args, **options)
        if bajo_test:
            ejecutar(DDL_DESPUES_DE_MIGRAR)
        return resultado