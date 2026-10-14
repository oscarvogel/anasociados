"""
Envia el resumen de hallazgos por WhatsApp a los encargados de cada area.

Se usa desde cron, los lunes a las 8:

    /var/www/venv_an/bin/python manage.py enviar_resumenes_whatsapp

Recorre las asignaciones de AreasProfile que tengan WhatsApp cargado, arma el
resumen con la misma logica que la pantalla manual y lo manda.

Notas de diseno:

- Un fallo individual no corta el resto. Si un numero esta mal o el gateway
  se cae para uno, los demas areas igual se notifican. Perder el aviso de 6
  de 7 encargados por un numero malo seria peor que un error.

- Sin WhatsApp cargado no se avisa a nadie de esa area, y queda anotado en la
  salida del comando para que se note al leer el log.

- Por defecto manda siempre, aunque no haya novedades (es lo que se pidio:
  un resumen semanal fijo). Con --solo-con-novedades solo escribe cuando hay
  algo vencido o proximo a vencer, que es lo que evita que el encargado
  termine ignorando el mensaje.
"""

import time
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from utiles.alertas_hallazgos import (
    SeleccionEmpresaAreaInvalida,
    construir_resumen_hallazgos_whatsapp,
    crear_enlace_hallazgos,
)
from utiles.notificaciones import WhatsAppClient, WhatsAppError
from usuarios.models import AreasProfile


class Command(BaseCommand):
    help = "Envia el resumen semanal de hallazgos por WhatsApp a los encargados de cada area."

    def add_arguments(self, parser):
        parser.add_argument("--fecha", help="Fecha de corte (YYYY-MM-DD). Default: hoy.")
        parser.add_argument(
            "--solo-con-novedades",
            action="store_true",
            help="Solo escribir a las areas que tengan hallazgos vencidos o por vencer.",
        )
        parser.add_argument("--cliente", help="Enviar solo a esta empresa (id).")
        parser.add_argument("--area", help="Enviar solo a esta area (id).")
        parser.add_argument(
            "--espera",
            type=float,
            default=2.0,
            help="Segundos de pausa entre envios (default: 2). El gateway tiene cola interna, asi que no es critico.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostrar que se enviaria sin enviar nada.",
        )

    def handle(self, *args, **opciones):
        fecha = self._parse_fecha(opciones["fecha"])
        solo_novedades = opciones["solo_con_novedades"]
        dry_run = opciones["dry_run"]

        cliente = WhatsAppClient()
        if not dry_run and not cliente.habilitado:
            raise CommandError(
                "WhatsApp esta deshabilitado o sin API key.\n"
                "  Revisar WHATSAPP_ENABLED y WHATSAPP_API_KEY en el .env.\n"
                "  Para ver que se enviaria sin enviar: agregar --dry-run."
            )

        destinatarios = self._destinatarios(opciones["cliente"], opciones["area"])

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Resumen de hallazgos - {fecha:%d/%m/%Y} - {'DRY RUN' if dry_run else 'envio real'}"
        ))

        if not destinatarios:
            self.stdout.write(self.style.WARNING(
                "  No hay ninguna asignacion con WhatsApp cargado."
            ))
            self.stdout.write("  Cargalos en el admin: Usuarios > Asignaciones de perfil.")
            return

        # Un area puede tener mas de un encargado con numero. Se agrupa por
        # area para no mandar el mismo resumen dos veces si un usuario esta
        # repetido por error en dos filas.
        por_area = {}
        for asignacion in destinatarios:
            por_area.setdefault(
                (asignacion.area.cliente_id, asignacion.area_id), []
            ).append(asignacion.telefono_whatsapp)

        enviados, omitidos, sin_numero, errores = [], [], [], []

        for (cliente_id, area_id), telefonos in sorted(por_area.items()):
            unicos = sorted(set(t for t in telefonos if t.strip()))
            if not unicos:
                sin_numero.append(f"{cliente_id}/{area_id}")
                continue

            try:
                resumen = construir_resumen_hallazgos_whatsapp(cliente_id, area_id, hoy=fecha)
            except SeleccionEmpresaAreaInvalida as exc:
                errores.append(f"{cliente_id}/{area_id}: {exc}")
                continue

            if solo_novedades and not resumen.hay_novedades:
                omitidos.append(f"{resumen.cliente} / {resumen.area}")
                self.stdout.write(f"  [omitido] {resumen.cliente} / {resumen.area}: sin novedades")
                continue

            etiqueta = f"{resumen.cliente} / {resumen.area}"
            self.stdout.write("")
            self.stdout.write(f"  {etiqueta}")
            self.stdout.write(f"    vencidos: {resumen.total_vencidos} | por vencer: {resumen.total_por_vencer}")
            self.stdout.write(f"    destinos: {', '.join(unicos)}")

            for telefono in unicos:
                if dry_run:
                    print(f"    [dry-run] mandaria a {telefono}")
                    enviados.append(telefono)
                    continue

                try:
                    _enlace, _token, url = crear_enlace_hallazgos(cliente_id, area_id)
                    mensaje = f"{resumen.mensaje}\n\nVer todos los hallazgos: {url}"
                    cliente.enviar_texto(telefono, mensaje, external_ref="an:resumen-semanal")
                    enviados.append(telefono)
                    self.stdout.write(f"    [ok] {telefono}")
                except WhatsAppError as exc:
                    errores.append(f"{telefono}: {exc}")
                    self.stdout.write(self.style.ERROR(f"    [error] {telefono}: {exc}"))
                except Exception as exc:  # noqa: BLE001
                    errores.append(f"{telefono}: {exc}")
                    self.stdout.write(self.style.ERROR(f"    [error inesperado] {telefono}: {exc}"))

                if opciones["espera"] > 0:
                    time.sleep(opciones["espera"])

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Resumen"))
        total_numeros = sum(len(set(t for t in v if t.strip())) for v in por_area.values())
        self.stdout.write(f"  areas con destino:        {len(por_area)}")
        self.stdout.write(f"  numeros a enviar:        {total_numeros}")
        self.stdout.write(f"  enviados:                {len(enviados)}")
        if omitidos:
            self.stdout.write(f"  omitidos sin novedades:  {len(omitidos)}")
        if sin_numero:
            self.stdout.write(self.style.WARNING(
                f"  areas sin numero cargado: {len(sin_numero)}  ({', '.join(sin_numero)})"
            ))
        if errores:
            self.stdout.write(self.style.ERROR(f"  con error:              {len(errores)}"))
            for e in errores:
                self.stdout.write(f"      {e}")

        if errores and not enviados:
            raise CommandError(f"Fallaron todos los envios ({len(errores)}).")

        self.stdout.write("")
        if not errores:
            self.stdout.write(self.style.SUCCESS("Listo."))
        else:
            self.stdout.write(self.style.WARNING(
                "Termino con errores. Un fallo de uno no impidio avisar a los demas."
            ))

    def _parse_fecha(self, valor):
        if not valor:
            return timezone.localdate()
        try:
            return date.fromisoformat(valor)
        except ValueError:
            raise CommandError(f"--fecha invalido: '{valor}'. Formato esperado: YYYY-MM-DD.")

    def _destinatarios(self, cliente_id, area_id):
        """Asignaciones con WhatsApp cargado, con el area y la empresa resueltas."""
        qs = (
            AreasProfile.objects.exclude(telefono_whatsapp="")
            .exclude(area__isnull=True)
            .select_related("area", "area__cliente", "user")
            .order_by("area__cliente__nombre", "area__detalle")
        )
        if cliente_id:
            qs = qs.filter(area__cliente_id=str(cliente_id))
        if area_id:
            qs = qs.filter(area_id=str(area_id))
        return list(qs)