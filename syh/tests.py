"""Tests de `syh`: porcentajes por área y la pantalla de hallazgos.

El primer test estaba roto y nadie lo había visto: `Area` pasó de `nombre` a
`detalle` y pasó a exigir `cliente`, y los estados que usaba ('No Cumplido')
no están en los que filtra `get_porcentaje_cumplidos_por_area`. Se reescribió
con el modelo actual manteniendo las mismas expectativas: 50% para un área con
un cumplido y uno incumplido, 100% para una con los dos cumplidos.

Los `id` de Movimientos van explícitos porque el campo está declarado como
`default=generate_unique_id(20)`, que se evalúa una sola vez al importar el
módulo: todos los movimientos creados sin id reciben la misma PK y el segundo
choca con Duplicate entry. Y miden 10 caracteres, que es lo que entra en
`syh_evidencia.movimiento` cuando la base se construye desde cero.
"""
import datetime
import io
import re
import tempfile
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from syh.models import Area, Cliente, Evidencia, Movimientos
from syh.views import _filtros_hallazgos
from usuarios.models import AreasProfile, Profile


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


class PlantillaHallazgosTest(TestCase):
    """
    Los comentarios {# ... #} de Django son de UNA linea.

    Uno de varias lineas no es un error: Django lo imprime como texto en la
    pagina. Ya paso dos veces (el sidebar y esta pantalla) y en ningun caso
    hubo excepcion, solo un bloque de comentario visible en pantalla.
    Para comentarios largos esta el bloque {% comment %}...{% endcomment %}.
    """

    PLANTILLAS = [
        "templates/pages/syh/visualizar_movimientos.html",
        "templates/includes/sidebar.html",
        "templates/pages/utiles/evidencias_revision.html",
        "templates/pages/utiles/hallazgos_publicos.html",
    ]

    def test_no_quedan_comentarios_de_varias_lineas(self):
        raiz = Path(__file__).resolve().parent.parent
        sin_cerrar = []
        for relativa in self.PLANTILLAS:
            ruta = raiz / relativa
            self.assertTrue(ruta.exists(), f"no existe {relativa}")
            for numero, linea in enumerate(
                ruta.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if "{#" in linea and "#}" not in linea:
                    sin_cerrar.append(f"{relativa}:{numero}")
        self.assertEqual(
            sin_cerrar, [],
            "comentario {# sin #} en la misma linea: " + ", ".join(sin_cerrar),
        )


class VistaHallazgosTest(TestCase):
    """
    Hallazgos agrupados por empresa, con lo pendiente arriba.

    No es una tabla con filtros: se comprueba el agrupado, el orden por
    urgencia y los contadores, que es lo que hace que la pantalla sirva.
    """

    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLIVIS", nombre="Empresa Alfa", email="alfa@example.com"
        )
        self.area = Area.objects.create(
            id="ARVIS1", cliente=self.cliente, detalle="Mantenimiento", responsable="Ana"
        )
        self.usuario = User.objects.create_user("visor", password="x")
        Profile.objects.create(user=self.usuario, cliente=self.cliente)
        # El agrupado y los contadores son de la vista de AN, que ve todas las
        # empresas. Con un usuario normal solo se veria la suya y el agrupado
        # no tendria sentido.
        self.superusuario = User.objects.create_superuser(
            "an", "an@example.com", "x"
        )
        self.client.force_login(self.usuario)
        self.url = reverse("syh:visualizar_movimientos")
        self._seq = 0

    def ver_todo(self):
        self.client.force_login(self.superusuario)
        return self.client.get(self.url)

    # --- acceso --------------------------------------------------------

    def test_sin_sesion_no_entra(self):
        """Sin login la vista daba 500, no 403.

        `Profile.objects.get(user=AnonymousUser)` tira TypeError, no
        Profile.DoesNotExist, asi que el except de la vista no lo agarraba.
        """
        self.client.logout()
        respuesta = self.client.get(self.url)
        self.assertIn(respuesta.status_code, (302, 403))
        self.assertNotEqual(respuesta.status_code, 500)

    def test_el_endpoint_de_fotos_tambien_pide_sesion(self):
        self.client.logout()
        respuesta = self.client.get(
            reverse("syh:hallazgo_evidencias", args=["mv00000001"])
        )
        self.assertIn(respuesta.status_code, (302, 403))

    def test_pasa_el_segmento_para_que_el_menu_se_resalte(self):
        """Sin 'segment' en el contexto, el item del menu nunca queda activo."""
        c = self.client.get(self.url)
        self.assertEqual(c.context["segment"], "hallazgos")

    # --- filtros -------------------------------------------------------

    def test_filtrar_por_empresa(self):
        beta = self.empresa("CLBETA", "Empresa Beta")
        self.hallazgo(self.cliente, 1, "De Alfa")
        self.hallazgo(beta, 1, "De Beta")
        self.client.force_login(self.superusuario)
        c = self.client.get(self.url, {"empresa": beta.pk}).context
        self.assertEqual(len(c["grupos"]), 1)
        self.assertEqual(c["grupos"][0]["empresa"].nombre, "Empresa Beta")

    def test_usuario_normal_no_puede_ver_otra_empresa(self):
        beta = self.empresa("CLBETA", "Empresa Beta")
        self.hallazgo(beta, 1, "Secreto de Beta")
        c = self.client.get(self.url, {"empresa": beta.pk}).context
        self.assertEqual(c["grupos"], [], "no puede acotar a una empresa que no es suya")

    # --- filtro por area ------------------------------------------------

    def test_filtrar_por_area(self):
        """El area es un filtro de la pantalla: al elegirla quedan solo los
        hallazgos de esa area."""
        taller = Area.objects.create(
            id="ARVIS2", cliente=self.cliente, detalle="Taller", responsable="Beto"
        )
        self.hallazgo(self.cliente, 1, "De Mantenimiento")
        self.hallazgo(self.cliente, 2, "Del Taller", area=taller)
        self.client.force_login(self.superusuario)
        c = self.client.get(self.url, {"area": taller.pk}).context
        self.assertEqual(c["total_general"], 1)
        self.assertEqual(c["grupos"][0]["hallazgos"][0].hallazgo, "Del Taller")
        self.assertEqual(c["area_sel"], taller.pk)
        self.assertEqual(c["area_sel_nombre"], "Taller")

    def test_el_area_y_la_empresa_se_pueden_elegir_juntas(self):
        taller = Area.objects.create(
            id="ARVIS2", cliente=self.cliente, detalle="Taller", responsable="Beto"
        )
        self.hallazgo(self.cliente, 1, "De Mantenimiento")
        self.hallazgo(self.cliente, 2, "Del Taller", area=taller)
        self.client.force_login(self.superusuario)
        c = self.client.get(
            self.url, {"empresa": self.cliente.pk, "area": taller.pk}
        ).context
        self.assertEqual(c["total_general"], 1)
        self.assertEqual(c["grupos"][0]["hallazgos"][0].hallazgo, "Del Taller")

    def test_usuario_normal_no_puede_ver_el_area_de_otra_empresa(self):
        beta = self.empresa("CLBETA", "Empresa Beta")
        area_beta = Area.objects.filter(cliente=beta).first()
        self.hallazgo(beta, 1, "Secreto de Beta")
        c = self.client.get(self.url, {"area": area_beta.pk}).context
        self.assertEqual(c["grupos"], [], "no puede acotar a un area que no es de su empresa")

    def test_las_areas_disponibles_son_las_de_la_empresa_elegida(self):
        """Elegida la empresa, el area se elige dentro de esa empresa."""
        beta = self.empresa("CLBETA", "Empresa Beta")
        self.client.force_login(self.superusuario)
        c = self.client.get(self.url, {"empresa": beta.pk}).context
        self.assertEqual(
            [a["pk"] for a in c["areas_disponibles"]],
            [a.pk for a in Area.objects.filter(cliente=beta)],
        )

    def test_sin_empresa_elegida_el_area_dice_de_quien_es(self):
        """Hay areas que se llaman igual en empresas distintas ("Transporte"),
        asi que sin empresa elegida el nombre tiene que decir de quien es."""
        beta = self.empresa("CLBETA", "Empresa Beta")
        self.client.force_login(self.superusuario)
        c = self.client.get(self.url).context
        nombres = {a["pk"]: a["nombre"] for a in c["areas_disponibles"]}
        area_beta = Area.objects.filter(cliente=beta).first()
        self.assertIn("Empresa Beta", nombres[area_beta.pk])
        self.assertIn("Empresa Alfa", nombres[self.area.pk])

    def test_usuario_con_areas_perfiladas_solo_ve_las_suyas(self):
        Area.objects.create(
            id="ARVIS9", cliente=self.cliente, detalle="Bodega", responsable="Ana"
        )
        AreasProfile.objects.create(user=self.usuario, area=self.area)
        c = self.client.get(self.url).context
        self.assertEqual([a["pk"] for a in c["areas_disponibles"]], [self.area.pk])

    def test_el_link_del_area_conserva_los_otros_filtros(self):
        """El link del area no puede pisar la empresa ni los estados."""
        self.hallazgo(self.cliente, 1, "Algo", dias=-5)
        self.client.force_login(self.superusuario)
        html = self.client.get(
            self.url, {"empresa": self.cliente.pk, "estado": "Gestión en Curso"}
        ).content.decode("utf-8")
        enlaces = {
            texto.strip(): href
            for href, texto in re.findall(r'href="([^"]*)"[^>]*>([^<]*)</a>', html)
        }
        consulta = parse_qs(urlparse(unescape(enlaces["Mantenimiento"])).query)
        self.assertEqual(consulta["area"], [self.area.pk])
        self.assertEqual(consulta["empresa"], [self.cliente.pk])
        self.assertEqual(consulta["estado"], ["Gestión en Curso"])

    def test_el_link_de_empresa_deja_el_area_en_cero(self):
        """El area es de una empresa: al cambiar de empresa deja de aplicar,
        porque puede no existir en la nueva."""
        self.hallazgo(self.cliente, 1, "Algo", dias=-5)
        self.client.force_login(self.superusuario)
        html = self.client.get(self.url, {"area": self.area.pk}).content.decode("utf-8")
        enlaces = {
            texto.strip(): href
            for href, texto in re.findall(r'href="([^"]*)"[^>]*>([^<]*)</a>', html)
        }
        consulta = parse_qs(urlparse(unescape(enlaces["Empresa Alfa"])).query)
        self.assertNotIn("area", consulta)

    def test_el_buscador_conserva_los_filtros(self):
        """El buscador es un formulario GET: si no lleva los filtros
        escondidos, al buscar se pierde la empresa y el area."""
        self.hallazgo(self.cliente, 1, "Algo", dias=-5)
        self.client.force_login(self.superusuario)
        html = self.client.get(
            self.url, {"empresa": self.cliente.pk, "area": self.area.pk}
        ).content.decode("utf-8")
        self.assertIn('name="empresa"', html)
        self.assertIn('name="area"', html)
        self.assertIn(f'value="{self.cliente.pk}"', html)
        self.assertIn(f'value="{self.area.pk}"', html)

    def test_el_pdf_de_la_pantalla_lleva_el_area(self):
        """Lo que se descarga es lo que se esta viendo."""
        self.hallazgo(self.cliente, 1, "Algo", dias=-5)
        self.client.force_login(self.superusuario)
        html = self.client.get(self.url, {"area": self.area.pk}).content.decode("utf-8")
        enlace_pdf = re.search(r'href="([^"]*imprimir_hallazgos[^"]*)"', html)
        self.assertIsNotNone(enlace_pdf, "no se encuentra el boton de descargar el PDF")
        consulta = parse_qs(urlparse(unescape(enlace_pdf.group(1))).query)
        self.assertEqual(consulta["area"], [self.area.pk])

    def test_filtrar_por_estado(self):
        self.hallazgo(self.cliente, 1, "Abierto", dias=-5)
        self.hallazgo(self.cliente, 2, "Cerrado", dias=-900, estado="Cumplido")
        self.client.force_login(self.superusuario)
        c = self.client.get(self.url, {"estado": "Cumplido"}).context
        self.assertEqual(c["total_general"], 1)
        self.assertEqual(c["grupos"][0]["hallazgos"][0].hallazgo, "Cerrado")

    def test_se_pueden_elegir_dos_estados_a_la_vez(self):
        """Los chips de estado se acumulan: elegir "Gestion en Curso" y
        "Incumplido" muestra los dos."""
        self.hallazgo(self.cliente, 1, "Uno en curso", dias=-5, estado="Gestión en Curso")
        self.hallazgo(self.cliente, 2, "Dos incumplidos", dias=-5, estado="Incumplido")
        self.hallazgo(self.cliente, 3, "Tres cumplidos", dias=-900, estado="Cumplido")
        self.client.force_login(self.superusuario)
        c = self.client.get(
            self.url, {"estado": ["Gestión en Curso", "Incumplido"]}
        ).context
        self.assertEqual(c["total_general"], 2)
        self.assertEqual(c["estados_sel"], ["Gestión en Curso", "Incumplido"])

    def test_los_chips_de_estado_se_acumulan(self):
        """El link de un estado que ya esta elegido lo saca del filtro, y el
        de uno que no esta lo agrega dejando los demas como estaban."""
        self.hallazgo(self.cliente, 1, "Algo", dias=-5)
        self.client.force_login(self.superusuario)
        html = self.client.get(self.url, {"estado": "Gestión en Curso"}).content.decode("utf-8")
        enlaces = {
            texto.strip(): href
            for href, texto in re.findall(r'href="([^"]*)"[^>]*>([^<]*)</a>', html)
        }

        def estados_de(texto):
            # Los links salen con `&amp;` (HTML valido): hay que deshacerlo
            # antes de parsear la consulta.
            consulta = urlparse(unescape(enlaces[texto])).query
            return parse_qs(consulta).get("estado", [])

        # El chip del estado que ya esta elegido lo saca del filtro.
        self.assertEqual(estados_de("Gestión en Curso"), [])
        # El de uno que no esta lo agrega y deja al otro como estaba.
        self.assertEqual(
            sorted(estados_de("Incumplido")),
            sorted(["Gestión en Curso", "Incumplido"]),
        )

    def test_estado_inventado_se_ignora(self):
        self.hallazgo(self.cliente, 1, "Algo", dias=-5)
        self.client.force_login(self.superusuario)
        c = self.client.get(self.url, {"estado": "Inventado"}).context
        # Sin estados validos, cae al default de abiertos.
        self.assertEqual(c["total_general"], 1)

    def test_vista_por_vencidos(self):
        self.hallazgo(self.cliente, 1, "Vencido", dias=-3)
        self.hallazgo(self.cliente, 2, "Por vencer", dias=3)
        c = self.client.get(self.url, {"vista": "vencidos"}).context
        self.assertEqual(c["total_general"], 1)
        self.assertEqual(c["grupos"][0]["hallazgos"][0].hallazgo, "Vencido")

    def test_los_contadores_no_cambian_al_filtrar(self):
        """Si no, al filtrar por vencidos el contador de vencidos daria 0."""
        self.hallazgo(self.cliente, 1, "Vencido", dias=-3)
        self.hallazgo(self.cliente, 2, "Por vencer", dias=3)
        base = self.client.get(self.url).context
        filtrado = self.client.get(self.url, {"vista": "vencidos"}).context
        self.assertEqual(filtrado["vencidos_general"], base["vencidos_general"])
        self.assertEqual(filtrado["por_vencer_general"], base["por_vencer_general"])

    def test_vista_inventada_cae_a_la_default(self):
        self.hallazgo(self.cliente, 1, "Algo", dias=-3)
        c = self.client.get(self.url, {"vista": "inventada"}).context
        self.assertEqual(c["vista"], "pendientes")

    # --- edicion -------------------------------------------------------

    def test_actualizar_el_estado(self):
        movimiento = self.hallazgo(self.cliente, 1, "Para cambiar")
        r = self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]),
            {"estado": "Cumplido"},
        )
        self.assertEqual(r.status_code, 200)
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, "Cumplido")

    def test_marcar_cumplido_pone_la_fecha_de_realizado(self):
        """Un hallazgo cerrado sin fecha de cuando se hizo no sirve para el resumen."""
        import django.utils.timezone

        movimiento = self.hallazgo(self.cliente, 1, "Para cerrar")
        self.assertIsNone(movimiento.fecha_realizado)
        self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]),
            {"estado": "Cumplido"},
        )
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.fecha_realizado, django.utils.timezone.localdate())

    def test_actualizar_responsable_observaciones_y_fecha(self):
        movimiento = self.hallazgo(self.cliente, 1, "Para tocar")
        self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]),
            {
                "estado": "Gestión en Curso",
                "responsable": "Marta",
                "fecha_cumplimiento": "2026-12-31",
                "observaciones": "Se hablo con el cliente",
            },
        )
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.responsable, "Marta")
        self.assertEqual(movimiento.observaciones, "Se hablo con el cliente")
        self.assertEqual(movimiento.fecha_cumplimiento, datetime.date(2026, 12, 31))

    def test_estado_inventado_en_la_edicion_se_rechaza(self):
        movimiento = self.hallazgo(self.cliente, 1, "Algo")
        r = self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]),
            {"estado": "Inventado"},
        )
        self.assertEqual(r.status_code, 400)
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, "Incumplido")

    def test_fecha_invalida_se_rechaza(self):
        movimiento = self.hallazgo(self.cliente, 1, "Algo")
        r = self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]),
            {"fecha_cumplimiento": "el jueves que viene"},
        )
        self.assertEqual(r.status_code, 400)

    def test_no_se_actualiza_sin_nada_que_cambiar(self):
        movimiento = self.hallazgo(self.cliente, 1, "Algo")
        r = self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]), {}
        )
        self.assertEqual(r.status_code, 400)

    def test_no_se_edita_un_hallazgo_de_otra_empresa(self):
        beta = self.empresa("CLBETA", "Empresa Beta")
        ajeno = self.hallazgo(beta, 1, "De Beta")
        r = self.client.post(
            reverse("syh:hallazgo_actualizar", args=[ajeno.pk]),
            {"estado": "Cumplido"},
        )
        self.assertEqual(r.status_code, 404)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.estado, "Incumplido")

    def test_la_edicion_pide_sesion(self):
        movimiento = self.hallazgo(self.cliente, 1, "Algo")
        self.client.logout()
        r = self.client.post(
            reverse("syh:hallazgo_actualizar", args=[movimiento.pk]),
            {"estado": "Cumplido"},
        )
        self.assertIn(r.status_code, (302, 403))
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, "Incumplido")

    def hallazgo(self, empresa, secuencia, texto, dias=-10, estado="Incumplido", area=None):
        # El id va con contador, corto a proposito: `syh_evidencia.movimiento`
        # queda en varchar(10) cuando la base se construye desde cero, asi que
        # un id mas largo no deja crear evidencias.
        self._seq += 1
        area = area or Area.objects.filter(cliente=empresa).first()
        return Movimientos.objects.create(
            id=f"mv{self._seq:08d}",
            cliente=empresa, area=area,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo=texto, responsable="Ana", plazo=30, estado=estado,
            fecha_cumplimiento=datetime.date.today() + datetime.timedelta(days=dias),
        )

    def empresa(self, clave, nombre):
        empresa = Cliente.objects.create(id=clave, nombre=nombre, email=f"{clave}@x.com")
        Area.objects.create(id=f"AR{clave}", cliente=empresa, detalle="Mantenimiento",
                            responsable="Ana")
        return empresa

    # --- agrupado ------------------------------------------------------

    def test_agrupa_por_empresa(self):
        otra = self.empresa("CLBETA", "Empresa Beta")
        self.hallazgo(self.cliente, 1, "Alfa vencida")
        self.hallazgo(otra, 1, "Beta vencida")
        grupos = self.ver_todo().context["grupos"]
        self.assertEqual({g["empresa"].nombre for g in grupos},
                         {"Empresa Alfa", "Empresa Beta"})
        for grupo in grupos:
            self.assertEqual(grupo["total"], 1)

    def test_ordena_la_empresa_mas_urgente_arriba(self):
        tranquila = self.empresa("CLBETA", "Zeta tranquila")
        urgente = self.empresa("CLALFA", "Alfa urgente")
        # Zeta tiene 1 que vence en 3 dias (por vencer, no vencido).
        self.hallazgo(tranquila, 1, "Vence pronto", dias=3)
        # Alfa tiene 2 vencidos.
        self.hallazgo(urgente, 1, "Vencido A", dias=-5)
        self.hallazgo(urgente, 2, "Vencido B", dias=-6)
        grupos = self.ver_todo().context["grupos"]
        self.assertEqual(grupos[0]["empresa"].nombre, "Alfa urgente")
        self.assertEqual(grupos[0]["vencidos"], 2)

    def test_empates_se_ordenan_por_nombre(self):
        a = self.empresa("CLA", "Zeta")
        b = self.empresa("CLB", "Alfa")
        self.hallazgo(a, 1, "Uno", dias=-5)
        self.hallazgo(b, 1, "Uno", dias=-5)
        grupos = self.ver_todo().context["grupos"]
        self.assertEqual([g["empresa"].nombre for g in grupos], ["Alfa", "Zeta"])

    # --- contadores ----------------------------------------------------

    def test_cuenta_vencidos_y_por_vencer(self):
        self.hallazgo(self.cliente, 1, "Vencido", dias=-1)
        self.hallazgo(self.cliente, 2, "Por vencer", dias=3)
        self.hallazgo(self.cliente, 3, "Lejos", dias=90)
        grupo = self.ver_todo().context["grupos"][0]
        self.assertEqual(grupo["vencidos"], 1)
        self.assertEqual(grupo["por_vencer"], 1)
        self.assertEqual(grupo["total"], 3)

    def test_cuenta_los_que_esperan_revision(self):
        movimiento = self.hallazgo(self.cliente, 1, "Con foto")
        Evidencia.objects.create(
            movimiento=movimiento, fecha=datetime.date.today(), origen="enlace_publico"
        )
        grupo = self.ver_todo().context["grupos"][0]
        self.assertEqual(grupo["por_revisar"], 1)

    def test_una_evidencia_ya_aceptada_no_cuenta_como_pendiente(self):
        movimiento = self.hallazgo(self.cliente, 1, "Ya revisada")
        Evidencia.objects.create(
            movimiento=movimiento, fecha=datetime.date.today(),
            origen="enlace_publico", estado=Evidencia.ESTADO_ACEPTADA,
        )
        grupo = self.ver_todo().context["grupos"][0]
        self.assertEqual(grupo["por_revisar"], 0)

    def test_los_totales_de_arriba_suman_los_grupos(self):
        beta = self.empresa("CLBETA", "Beta")
        self.hallazgo(self.cliente, 1, "Vencido", dias=-2)
        self.hallazgo(beta, 1, "Otro vencido", dias=-3)
        c = self.ver_todo().context
        self.assertEqual(c["vencidos_general"], 2)
        self.assertEqual(c["total_general"], 2)
        self.assertEqual(c["empresas_con_pendientes"], 2)

    # --- que no entre lo cerrado ----------------------------------------

    def test_lo_cumplido_no_aparece(self):
        self.hallazgo(self.cliente, 1, "Viejo cerrado", dias=-900, estado="Cumplido")
        self.hallazgo(self.cliente, 2, "Abierto", dias=-2)
        c = self.ver_todo().context
        self.assertEqual(c["total_general"], 1)
        self.assertEqual(c["grupos"][0]["hallazgos"][0].hallazgo, "Abierto")

    def test_con_busqueda_si_busca_tambien_los_cerrados(self):
        self.hallazgo(self.cliente, 1, "Fuga en el tanque", dias=-900, estado="Cumplido")
        self.hallazgo(self.cliente, 2, "Otra cosa abierta", dias=-2)
        c = self.client.get(self.url, {"q": "Fuga"}).context
        self.assertEqual(
            c["total_general"], 1,
            "si estas buscando algo, lo tenes que encontrar este o no",
        )
        # Y el filtro de estado explicito sigue mandando sobre la busqueda.
        solo_abiertos = self.client.get(self.url, {"q": "Fuga", "estado": "Incumplido"}).context
        self.assertEqual(solo_abiertos["total_general"], 0)

    # --- recorte --------------------------------------------------------

    def test_recorta_la_lista_cada_empresa(self):
        for i in range(12):
            self.hallazgo(self.cliente, i, f"Hallazgo {i}", dias=-i)
        grupo = self.ver_todo().context["grupos"][0]
        self.assertEqual(len(grupo["hallazgos"]), 8)
        self.assertEqual(grupo["ocultos"], 4)

    def test_con_todos_no_recorta(self):
        for i in range(12):
            self.hallazgo(self.cliente, i, f"Hallazgo {i}", dias=-i)
        self.client.force_login(self.superusuario)
        grupo = self.client.get(self.url, {"todos": "1"}).context["grupos"][0]
        self.assertEqual(len(grupo["hallazgos"]), 12)
        self.assertEqual(grupo["ocultos"], 0)

    # --- buscador -------------------------------------------------------

    def test_busca_por_texto(self):
        self.hallazgo(self.cliente, 1, "Falta el matafuego")
        self.hallazgo(self.cliente, 2, "Luminaria fundida")
        c = self.client.get(self.url, {"q": "matafuego"}).context
        self.assertEqual(c["total_general"], 1)

    def test_busqueda_larga_se_recorta(self):
        c = self.client.get(self.url, {"q": "x" * 500}).context
        self.assertLessEqual(len(c["busqueda"]), 100)

    def test_sin_resultados_no_rompe(self):
        self.hallazgo(self.cliente, 1, "Algo")
        respuesta = self.client.get(self.url, {"q": "no-existe-esto"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["grupos"], [])

    # --- endpoint de fotos ----------------------------------------------

    def test_el_endpoint_devuelve_las_evidencias(self):
        movimiento = self.hallazgo(self.cliente, 1, "Con evidencia")
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                buffer = io.BytesIO()
                Image.new("RGB", (16, 16), (10, 120, 60)).save(buffer, format="JPEG")
                evidencia = Evidencia.objects.create(
                    movimiento=movimiento, fecha=datetime.date.today(),
                    origen="enlace_publico", subido_por="5493757677124",
                    motivo_rechazo="No se ve",
                )
                evidencia.archivo.save(
                    "foto.jpg", SimpleUploadedFile("foto.jpg", buffer.getvalue()),
                    save=True,
                )
                respuesta = self.client.get(
                    reverse("syh:hallazgo_evidencias", args=[movimiento.pk])
                )
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()["evidencias"]
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["motivo_rechazo"], "No se ve")
        self.assertEqual(datos[0]["estado_legible"], "Pendiente de revisión")

    def test_no_se_ven_evidencias_de_otra_empresa(self):
        otra = self.empresa("CLOTRA", "Otra")
        ajeno = self.hallazgo(otra, 1, "Ajeno")
        respuesta = self.client.get(reverse("syh:hallazgo_evidencias", args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 403)

    def test_hallazgo_inexistente_da_404(self):
        respuesta = self.client.get(reverse("syh:hallazgo_evidencias", args=["noexiste"]))
        self.assertEqual(respuesta.status_code, 404)


class ImprimirHallazgosTest(TestCase):
    """
    El PDF de los pendientes: la version descargable de la pantalla.

    Este reporte existio para el boton "Imprimir" del Tablero y desaparecio con
    el rediseño de la pantalla de hallazgos. Lo que se comprueba aca es que
    vuelve, que sale con los filtros de la pantalla y que no se lo baja
    cualquiera.
    """

    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLIPDF", nombre="Empresa Alfa", email="alfa@example.com"
        )
        self.area = Area.objects.create(
            id="ARPDF01", cliente=self.cliente, detalle="Mantenimiento", responsable="Ana"
        )
        self.superusuario = User.objects.create_superuser("an", "an@example.com", "x")
        self.usuario = User.objects.create_user("visor", password="x")
        Profile.objects.create(user=self.usuario, cliente=self.cliente)
        self.client.force_login(self.superusuario)
        self.url = reverse("syh:imprimir_hallazgos")
        self._seq = 0

    def hallazgo(self, empresa, texto, dias=-10, estado="Incumplido"):
        self._seq += 1
        area = Area.objects.filter(cliente=empresa).first()
        return Movimientos.objects.create(
            id=f"mv{self._seq:08d}",
            cliente=empresa, area=area,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo=texto, responsable="Ana", plazo=30, estado=estado,
            fecha_cumplimiento=datetime.date.today() + datetime.timedelta(days=dias),
        )

    def test_el_pdf_se_descarga(self):
        self.hallazgo(self.cliente, "Falta el matafuego")
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertTrue(respuesta.content.startswith(b"%PDF"))

    def test_sin_sesion_no_entra(self):
        """La URL vieja no pedia sesion: con la URL se leia el PDF con los
        hallazgos de todas las empresas sin entrar al sistema."""
        self.client.logout()
        respuesta = self.client.get(self.url)
        self.assertIn(respuesta.status_code, (302, 403))
        respuesta = self.client.get(reverse("syh:imprimir_movimientos"))
        self.assertIn(respuesta.status_code, (302, 403))

    def test_sin_filtro_no_revienta(self):
        """Sin empresa ni area el reporte antiguo reventaba con AttributeError."""
        self.hallazgo(self.cliente, "Falta el matafuego")
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")

    def test_el_nombre_del_archivo_dice_de_que_empresa_es(self):
        self.hallazgo(self.cliente, "Falta el matafuego")
        respuesta = self.client.get(self.url, {"empresa": str(self.cliente.id)})
        self.assertIn("empresa-alfa", respuesta["Content-Disposition"])

    def test_solo_los_abiertos(self):
        """Lo que esta cerrado es historia: al PDF van los pendientes."""
        self.hallazgo(self.cliente, "Este va", estado="Incumplido")
        self.hallazgo(self.cliente, "Este no", estado="Cumplido")
        respuesta = self.client.get(self.url, {"empresa": str(self.cliente.id)})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")

    def test_el_resumen_cuenta_todos_los_estados(self):
        """Los chips de estado recortan la lista, no el resumen.

        Al filtrar por "Gestion en Curso" e "Incumplido" los porcentajes del
        resumen daban 100% entre esos dos y los cumplidos desaparecian. El
        resumen tiene que contar los tres estados del mismo recorte.
        """
        self.hallazgo(self.cliente, "Uno en curso", estado="Gestión en Curso")
        self.hallazgo(self.cliente, "Dos incumplidos", estado="Incumplido")
        self.hallazgo(self.cliente, "Tres cumplidos", estado="Cumplido")

        request = RequestFactory().get(
            self.url,
            {
                "empresa": str(self.cliente.id),
                "estado": ["Gestión en Curso", "Incumplido"],
            },
        )
        request.user = self.superusuario
        filtros = _filtros_hallazgos(request)

        self.assertEqual(len(filtros["base"]), 2)
        self.assertEqual(
            sorted({movimiento.estado for movimiento in filtros["resumen"]}),
            ["Cumplido", "Gestión en Curso", "Incumplido"],
        )

    def test_la_url_vieja_sigue_andando(self):
        """El Tablero y los enlaces guardados usan la URL vieja."""
        self.hallazgo(self.cliente, "Falta el matafuego")
        respuesta = self.client.get(
            reverse("syh:imprimir_movimientos"),
            {"cliente": str(self.cliente.id), "area": str(self.area.id)},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")

    def test_sin_hallazgos_vuelve_a_la_pantalla(self):
        respuesta = self.client.get(self.url, {"empresa": "CLINEXIS"})
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("syh:visualizar_movimientos"), respuesta["Location"])


class CerrarHallazgosMasivoTest(TestCase):
    """
    Cerrar varios hallazgos de una vez.

    Es lo que se usa al terminar una visita: los que ya se resolvieron se
    marcan juntos. Marcar de a uno en el celular es abrir el editor, elegir el
    estado, guardar y esperar que se recargue la pagina.
    """

    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLIMAS", nombre="Empresa Alfa", email="alfa@example.com"
        )
        self.area = Area.objects.create(
            id="ARMAS01", cliente=self.cliente, detalle="Mantenimiento", responsable="Ana"
        )
        self.superusuario = User.objects.create_superuser("an", "an@example.com", "x")
        self.usuario = User.objects.create_user("operador", password="x")
        Profile.objects.create(user=self.usuario, cliente=self.cliente)
        self.url = reverse("syh:hallazgos_cerrar_masivo")
        self._seq = 0

    def hallazgo(self, empresa, texto, estado="Incumplido"):
        self._seq += 1
        area = Area.objects.filter(cliente=empresa).first()
        return Movimientos.objects.create(
            id=f"ms{self._seq:08d}",
            cliente=empresa, area=area,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo=texto, responsable="Ana", plazo=30, estado=estado,
            fecha_cumplimiento=datetime.date.today() - datetime.timedelta(days=5),
        )

    def test_cierra_los_elegidos(self):
        primero = self.hallazgo(self.cliente, "Uno")
        segundo = self.hallazgo(self.cliente, "Dos")
        self.client.force_login(self.superusuario)
        respuesta = self.client.post(self.url, {"ids": [primero.pk, segundo.pk]})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["cerrados"], 2)
        primero.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(primero.estado, "Cumplido")
        self.assertEqual(segundo.estado, "Cumplido")

    def test_pone_la_fecha_de_realizado(self):
        """Un hallazgo cerrado sin fecha de cuando se hizo no sirve para el
        resumen mensual."""
        movimiento = self.hallazgo(self.cliente, "Uno")
        self.client.force_login(self.superusuario)
        self.client.post(self.url, {"ids": [movimiento.pk]})
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.fecha_realizado, datetime.date.today())

    def test_no_cierra_lo_de_otra_empresa(self):
        otro = Cliente.objects.create(id="CLOTMA", nombre="Empresa Beta")
        Area.objects.create(id="AROTMA1", cliente=otro, detalle="Taller")
        ajeno = self.hallazgo(otro, "De Beta")
        propio = self.hallazgo(self.cliente, "De Alfa")
        self.client.force_login(self.usuario)
        respuesta = self.client.post(self.url, {"ids": [ajeno.pk, propio.pk]})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["cerrados"], 1)
        ajeno.refresh_from_db()
        propio.refresh_from_db()
        self.assertEqual(ajeno.estado, "Incumplido")
        self.assertEqual(propio.estado, "Cumplido")

    def test_sin_sesion_no_entra(self):
        movimiento = self.hallazgo(self.cliente, "Uno")
        self.client.logout()
        respuesta = self.client.post(self.url, {"ids": [movimiento.pk]})
        self.assertIn(respuesta.status_code, (302, 403))
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, "Incumplido")

    def test_sin_elegir_nada_da_error(self):
        self.client.force_login(self.superusuario)
        respuesta = self.client.post(self.url, {"ids": []})
        self.assertEqual(respuesta.status_code, 400)

    def test_ya_cumplido_no_se_cuenta(self):
        movimiento = self.hallazgo(self.cliente, "Uno", estado="Cumplido")
        self.client.force_login(self.superusuario)
        respuesta = self.client.post(self.url, {"ids": [movimiento.pk]})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["cerrados"], 0)

    def test_la_pantalla_trae_la_casilla(self):
        self.hallazgo(self.cliente, "Uno")
        self.client.force_login(self.superusuario)
        respuesta = self.client.get(reverse("syh:visualizar_movimientos"))
        self.assertContains(respuesta, "hl-marcar__casilla")
        self.assertContains(respuesta, "hl-cerrar-masivo")
