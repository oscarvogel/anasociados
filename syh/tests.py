"""Tests de los porcentajes de cumplimiento por área.

Este archivo estaba roto y nadie lo había visto: `Area` pasó de `nombre` a
`detalle` y pasó a exigir `cliente`, y los estados que usaba ('No Cumplido')
no están en los que filtra `get_porcentaje_cumplidos_por_area`. Se reescribió
con el modelo actual manteniendo las mismas expectativas: 50% para un área con
un cumplido y uno incumplido, 100% para una con los dos cumplidos.

Los `id` de Movimientos van explícitos porque el campo está declarado como
`default=generate_unique_id(20)`, que se evalúa una sola vez al importar el
módulo: todos los movimientos creados sin id reciben la misma PK y el segundo
choca con Duplicate entry.
"""
import datetime
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from syh.models import Area, Cliente, Evidencia, Movimientos
from usuarios.models import Profile


class TestGetPorcentajeCumplidosPorArea(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLIPOR", nombre="Cliente de prueba", email="prueba@example.com"
        )

        self.area1 = Area.objects.create(
            id="ARP01", cliente=self.cliente, detalle="Área 1", responsable="Ana"
        )
        self.area2 = Area.objects.create(
            id="ARP02", cliente=self.cliente, detalle="Área 2", responsable="Beto"
        )

        self.movimiento1 = self.crear("ARP01", datetime.date(2022, 1, 1), "Cumplido", 1)
        self.movimiento2 = self.crear("ARP01", datetime.date(2022, 1, 15), "Incumplido", 2)
        self.movimiento3 = self.crear("ARP02", datetime.date(2022, 2, 1), "Cumplido", 3)
        self.movimiento4 = self.crear("ARP02", datetime.date(2022, 2, 15), "Cumplido", 4)

    def crear(self, area_id, fecha, estado, secuencia):
        return Movimientos.objects.create(
            id=f"movpor{secuencia:07d}",
            cliente=self.cliente,
            area_id=area_id,
            fecha=fecha,
            periodo="Enero" if fecha.month == 1 else "Febrero",
            hallazgo="Prueba de porcentaje",
            responsable="Ana",
            plazo=30,
            estado=estado,
            fecha_cumplimiento=fecha,
        )

    def test_get_porcentaje_cumplidos_por_area(self):
        # Rango completo: un área con 1 de 2 cumplidos y otra con 2 de 2.
        fecha_desde = datetime.date(2022, 1, 1)
        fecha_hasta = datetime.date(2022, 2, 28)
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(
            self.cliente, fecha_desde, fecha_hasta
        )
        self.assertEqual(resultados["Área 1"], 50.0)
        self.assertEqual(resultados["Área 2"], 100.0)

        # Solo enero: aparece el área 1, no el área 2.
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(
            self.cliente, datetime.date(2022, 1, 1), datetime.date(2022, 1, 31)
        )
        self.assertEqual(resultados["Área 1"], 50.0)
        self.assertNotIn("Área 2", resultados)

        # Solo febrero: aparece el área 2, no el área 1.
        resultados = Movimientos.get_porcentaje_cumplidos_por_area(
            self.cliente, datetime.date(2022, 2, 1), datetime.date(2022, 2, 28)
        )
        self.assertEqual(resultados["Área 2"], 100.0)
        self.assertNotIn("Área 1", resultados)


class VistaHallazgosTest(TestCase):
    """
    La pantalla de trabajo de hallazgos: buscar, filtrar y ver las evidencias
    sin entrar al admin.
    """

    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLIVIS", nombre="Empresa Vista", email="vista@example.com"
        )
        self.area = Area.objects.create(
            id="ARVIS1", cliente=self.cliente, detalle="Mantenimiento", responsable="Ana"
        )
        self.usuario = User.objects.create_user("visor", password="x")
        Profile.objects.create(user=self.usuario, cliente=self.cliente)
        self.client.force_login(self.usuario)
        self.url = reverse("syh:visualizar_movimientos")

    def hallazgo(self, secuencia, texto, responsable="Ana", dias=-10):
        return Movimientos.objects.create(
            id=f"mv{secuencia:08d}",
            cliente=self.cliente, area=self.area,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo=texto, responsable=responsable, plazo=30,
            estado="Incumplido",
            fecha_cumplimiento=datetime.date.today() + datetime.timedelta(days=dias),
        )

    def ids_en_la_pagina(self, respuesta):
        return {m.pk for m in respuesta.context["movimientos"]}

    # --- búsqueda ------------------------------------------------------

    def test_busca_por_texto_del_hallazgo(self):
        self.hallazgo(1, "Falta el matafuego en el deposito")
        self.hallazgo(2, "Luminaria fundida en la oficina")
        respuesta = self.client.get(self.url, {"q": "matafuego"})
        self.assertEqual(self.ids_en_la_pagina(respuesta), {"mv00000001"})

    def test_busca_por_responsable(self):
        self.hallazgo(1, "Algo", responsable="Marta")
        self.hallazgo(2, "Otra cosa", responsable="Beto")
        respuesta = self.client.get(self.url, {"q": "Marta"})
        self.assertEqual(self.ids_en_la_pagina(respuesta), {"mv00000001"})

    def test_la_busqueda_no_se_pisa_con_los_otros_filtros(self):
        self.hallazgo(1, "Falta el matafuego", dias=-10)
        self.hallazgo(2, "Falta el matafuego otra vez", dias=-5)
        # Termino + estado: el AND entre filtros tiene que reducir el resultado.
        ambos = self.client.get(self.url, {"q": "matafuego", "estado": "Incumplido"})
        self.assertEqual(len(self.ids_en_la_pagina(ambos)), 2)
        sin_coincidir = self.client.get(self.url, {"q": "matafuego", "estado": "Cumplido"})
        self.assertEqual(self.ids_en_la_pagina(sin_coincidir), set())

    def test_sin_resultados_no_rompe(self):
        self.hallazgo(1, "Algo")
        respuesta = self.client.get(self.url, {"q": "no-existe-esto"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.ids_en_la_pagina(respuesta), set())

    def test_la_busqueda_larga_se_recorta(self):
        # Sin tope, un LIKE de 5000 caracteres trava la consulta.
        respuesta = self.client.get(self.url, {"q": "x" * 500})
        self.assertEqual(respuesta.status_code, 200)
        self.assertLessEqual(len(respuesta.context["busqueda"]), 100)

    # --- filtro de pendientes ------------------------------------------

    def test_filtrar_por_pendientes_de_revision(self):
        con_pendiente = self.hallazgo(1, "Con evidencia")
        self.hallazgo(2, "Sin evidencia")
        ya_aceptada = self.hallazgo(3, "Ya revisada")
        Evidencia.objects.create(
            movimiento=con_pendiente, fecha=datetime.date.today(),
            origen="enlace_publico",
        )
        Evidencia.objects.create(
            movimiento=ya_aceptada, fecha=datetime.date.today(),
            origen="enlace_publico", estado=Evidencia.ESTADO_ACEPTADA,
        )
        respuesta = self.client.get(self.url, {"pendientes": "1"})
        self.assertEqual(self.ids_en_la_pagina(respuesta), {"mv00000001"})

    def test_el_badge_dice_cuantas_faltan_revisar(self):
        movimiento = self.hallazgo(1, "Con evidencia")
        Evidencia.objects.create(
            movimiento=movimiento, fecha=datetime.date.today(), origen="enlace_publico"
        )
        Evidencia.objects.create(
            movimiento=movimiento, fecha=datetime.date.today(), origen="enlace_publico"
        )
        respuesta = self.client.get(self.url)
        fila = next(m for m in respuesta.context["movimientos"] if m.pk == movimiento.pk)
        self.assertEqual(fila.evidencias_pendientes, 2)
        self.assertEqual(fila.total_evidencias, 2)

    # --- orden ---------------------------------------------------------

    def test_ordena_por_vencimiento(self):
        self.hallazgo(1, "Vence lejos", dias=100)
        self.hallazgo(2, "Vence ya", dias=-100)
        self.hallazgo(3, "Vence medio", dias=-1)
        respuesta = self.client.get(self.url)
        orden = [m.pk for m in respuesta.context["movimientos"]]
        self.assertEqual(orden, ["mv00000002", "mv00000003", "mv00000001"])

    # --- endpoint de evidencias ----------------------------------------

    def test_el_endpoint_devuelve_las_evidencias(self):
        movimiento = self.hallazgo(1, "Con evidencia")
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                buffer = __import__("io").BytesIO()
                Image.new("RGB", (16, 16), (10, 120, 60)).save(buffer, format="JPEG")
                evidencia = Evidencia.objects.create(
                    movimiento=movimiento, fecha=datetime.date.today(),
                    origen="enlace_publico", subido_por="5493757677124",
                    motivo_rechazo="No se ve",
                )
                evidencia.archivo.save(
                    "foto.jpg", SimpleUploadedFile("foto.jpg", buffer.getvalue()), save=True
                )
                respuesta = self.client.get(
                    reverse("syh:hallazgo_evidencias", args=[movimiento.pk])
                )
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(len(datos["evidencias"]), 1)
        self.assertTrue(datos["evidencias"][0]["tiene_foto"])
        self.assertEqual(datos["evidencias"][0]["subido_por"], "5493757677124")
        self.assertEqual(datos["evidencias"][0]["motivo_rechazo"], "No se ve")

    def test_no_se_ven_evidencias_de_otra_empresa(self):
        otro = Cliente.objects.create(
            id="CLOTRO", nombre="Otra", email="otra@example.com"
        )
        area_ajena = Area.objects.create(
            id="AROTRO", cliente=otro, detalle="Mantenimiento", responsable="Zoe"
        )
        ajeno = Movimientos.objects.create(
            id="movajeno01", cliente=otro, area=area_ajena,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo="Ajeno", responsable="Zoe", plazo=10, estado="Incumplido",
            fecha_cumplimiento=datetime.date.today(),
        )
        respuesta = self.client.get(reverse("syh:hallazgo_evidencias", args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 403)

    def test_hallazgo_inexistente_da_404(self):
        respuesta = self.client.get(reverse("syh:hallazgo_evidencias", args=["noexiste"]))
        self.assertEqual(respuesta.status_code, 404)