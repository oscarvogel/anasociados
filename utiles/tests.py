"""Tests del enlace público de hallazgos (subida de evidencia y marcas de estado).

Las tablas `clientes`, `areas` y `movimientos` son `managed = False`. Las crea
`core_an.runtests.RunnerConTablasExternas` antes de migrar, asi que aca no hay
que volver a definirlas.
"""
import datetime
import hashlib
import io
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from syh.models import Area, Cliente, Evidencia, Movimientos
from utiles.alertas_hallazgos import crear_enlaces_revision_admin
from utiles.models import ContactoNotificacion, EnlacePublicoHallazgos

TOKEN = "token-de-prueba-para-el-link-publico"


def imagen_en_memoria(nombre="foto.jpg"):
    """Un JPEG real y chico: ImageField valida el contenido, no la extensión."""
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 120, 60)).save(buffer, format="JPEG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/jpeg")


def cuerpo_multipart(campos, archivos, boundary="BOUNDARY"):
    """Arma un POST multipart con N archivos bajo el MISMO nombre de campo.

    El test client no lo puede hacer con un dict: dos claves 'archivos' no
    caben, y la segunda pisa a la primera. Es justo el caso que necesita el
    endpoint, que lee `request.FILES.getlist('archivos')`.
    """
    partes = []
    for nombre, valor in campos:
        partes.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{nombre}"\r\n\r\n'
            f"{valor}\r\n".encode("utf-8")
        )
    for indice, contenido in enumerate(archivos, start=1):
        partes.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="archivos"; '
            f'filename="foto{indice}.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
            .encode("utf-8")
            + contenido
            + b"\r\n"
        )
    partes.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(partes)


class BaseEnlacePublico(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            id="CLI01", nombre="Cliente de prueba", email="prueba@example.com"
        )
        self.area = Area.objects.create(
            id="ARE01", cliente=self.cliente, detalle="Sistemas", responsable="Ana"
        )
        self.otra_area = Area.objects.create(
            id="ARE02", cliente=self.cliente, detalle="Seguridad", responsable="Beto"
        )
        EnlacePublicoHallazgos.objects.create(
            area=self.area,
            cliente_id=self.cliente.pk,
            token_hash=hashlib.sha256(TOKEN.encode()).hexdigest(),
            expires_at=timezone.now() + datetime.timedelta(days=14),
            puede_revisar=False,
        )
        self.url_datos = reverse("utiles:hallazgos_publicos_datos")
        self.url_subir = reverse("utiles:hallazgos_publicos_subir")
        self._secuencia = 0

    def movimiento(self, descripcion="Falta el matafuego", **kwargs):
        self._secuencia += 1
        valores = {
            # El id va explicito y de 10 caracteres, que es lo que produce
            # `Movimientos.save()` -> generate_unique_id(). Además coincide con
            # el ancho de la columna en una base migrada desde cero
            # (`syh_evidencia.movimiento` varchar(10)); ver la nota sobre
            # Movimientos.id en el informe de esta tanda.
            "id": f"mov{self._secuencia:07d}",
            "cliente": self.cliente,
            "area": self.area,
            "fecha": datetime.date.today(),
            "periodo": "Octubre",
            "hallazgo": descripcion,
            "responsable": "Ana",
            "plazo": 30,
            "estado": "Incumplido",
            # Vencido de verdad: el resumen solo mete en "vencidos" lo que tiene
            # fecha_cumplimiento anterior a hoy. Con la fecha de hoy caeria en
            # "por_vencer" y las listas que se chequean saldrian vacias.
            "fecha_cumplimiento": datetime.date.today() - datetime.timedelta(days=10),
        }
        valores.update(kwargs)
        return Movimientos.objects.create(**valores)

    def marcar(self, movimiento):
        return Evidencia.objects.create(
            movimiento=movimiento, fecha=datetime.date.today(), origen="enlace_publico"
        )

    def obtener_datos(self, token=TOKEN):
        respuesta = self.client.get(
            self.url_datos, HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()

    def subir(self, movimiento, archivos, token=TOKEN, detalle="Recién hecho"):
        """POST multipart con N archivos bajo el mismo nombre de campo."""
        cuerpo = cuerpo_multipart(
            campos=[("movimiento_id", movimiento.pk), ("detalle", detalle)],
            archivos=[a.read() for a in archivos],
        )
        with mock.patch(
            "utiles.views.notificar_admin_evidencia", return_value={"detalle": "sin envío"}
        ):
            return self.client.post(
                self.url_subir,
                data=cuerpo,
                content_type="multipart/form-data; boundary=BOUNDARY",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )


class MarcasDeEvidenciaTest(BaseEnlacePublico):
    """El campo `evidencia` es lo que dibuja el badge y el sufijo del selector."""

    def vencidos(self):
        """Los vencidos, con la precondition de que no vengan vacios.

        Sin este assert el test pasa en falso: si el filtro por fecha deja la
        lista vacia, el for no recorre nada y todo 'ok'.
        """
        datos = self.obtener_datos()
        self.assertTrue(
            datos["vencidos"],
            "la lista de vencidos vino vacia: el test pasaria sin comprobar nada",
        )
        return datos["vencidos"]

    def test_sin_evidencia_todas_vienen_en_false(self):
        self.movimiento("Sin foto")
        self.movimiento("Otro sin foto")
        self.assertEqual(len(self.vencidos()), 2)
        for hallazgo in self.vencidos():
            self.assertIs(hallazgo["evidencia"], False)

    def test_solo_el_hallazgo_con_evidencia_va_marcado(self):
        self.marcar(self.movimiento("Con foto"))
        self.movimiento("Sin foto")
        marcados = [h["evidencia"] for h in self.vencidos()]
        self.assertEqual(sorted(marcados), [False, True])

    def test_una_evidencia_no_contamina_a_los_demas(self):
        self.marcar(self.movimiento("Con foto"))
        for descripcion in ("Dos", "Tres", "Cuatro"):
            self.movimiento(descripcion)
        vencidos = self.vencidos()
        self.assertEqual(len(vencidos), 4)
        self.assertEqual(sum(1 for h in vencidos if h["evidencia"]), 1)

    def test_hallazgo_de_otra_empresa_no_se_marca(self):
        otro = Cliente.objects.create(
            id="CLI02", nombre="Otra empresa", email="otra@example.com"
        )
        area_ajena = Area.objects.create(
            id="ARE03", cliente=otro, detalle="Mantenimiento", responsable="Caro"
        )
        self.marcar(
            Movimientos.objects.create(
                id="mov9999999",
                cliente=otro,
                area=area_ajena,
                fecha=datetime.date.today(),
                periodo="Octubre",
                hallazgo="Ajeno",
                responsable="Caro",
                plazo=10,
                estado="Incumplido",
                fecha_cumplimiento=datetime.date.today(),
            )
        )
        self.movimiento("Nuestro")
        vencidos = self.vencidos()
        self.assertEqual(len(vencidos), 1)
        for hallazgo in vencidos:
            self.assertIs(hallazgo["evidencia"], False)

    def test_sin_token_no_devuelve_hallazgos(self):
        self.movimiento("Sin foto")
        self.assertEqual(self.client.get(self.url_datos).status_code, 404)


class PaginaPublicaTest(BaseEnlacePublico):
    """La pagina se renderiza siempre: el token va en el fragmento (#)."""

    def test_la_pagina_renderiza(self):
        respuesta = self.client.get(reverse("utiles:hallazgos_publicos"))
        self.assertEqual(respuesta.status_code, 200)

    def test_tra_el_modal_de_confirmacion(self):
        """Sin este markup el JS no tiene donde mostrar que llego la foto."""
        contenido = self.client.get(reverse("utiles:hallazgos_publicos")).content.decode()
        self.assertIn('id="modal-evidencia"', contenido)
        self.assertIn('id="modal-cerrar"', contenido)
        self.assertIn("Evidencia recibida", contenido)

    def test_tra_el_css_del_modal(self):
        contenido = self.client.get(reverse("utiles:hallazgos_publicos")).content.decode()
        self.assertIn(".modal-card", contenido)
        self.assertIn(".finding-evidencia", contenido)


class SubidaDeEvidenciaTest(BaseEnlacePublico):
    """La subida: conteo de `guardadas` (lo que muestra el modal), origen y archivo."""

    def test_una_foto_devuelve_guardadas_1(self):
        movimiento = self.movimiento()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                respuesta = self.subir(movimiento, [imagen_en_memoria()])
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["guardadas"], 1)

    def test_varias_fotos_devuelve_el_conteo_del_modal(self):
        movimiento = self.movimiento()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                respuesta = self.subir(
                    movimiento, [imagen_en_memoria("a.jpg"), imagen_en_memoria("b.jpg")]
                )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["guardadas"], 2)
        self.assertEqual(Evidencia.objects.count(), 2)

    def test_la_evidencia_queda_con_origen_enlace_publico(self):
        movimiento = self.movimiento()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                self.subir(movimiento, [imagen_en_memoria()])
        evidencia = Evidencia.objects.get(movimiento=movimiento)
        self.assertEqual(evidencia.origen, "enlace_publico")
        self.assertTrue(evidencia.archivo.name.startswith("evidencias/"))

    def test_subir_la_foto_no_cierra_el_hallazgo(self):
        movimiento = self.movimiento()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                self.subir(movimiento, [imagen_en_memoria()])
        movimiento.refresh_from_db()
        self.assertEqual(
            movimiento.estado, "Incumplido", "subir la foto no debe cerrar el hallazgo"
        )

    def test_tras_subir_el_hallazgo_ya_aparece_marcado(self):
        """Cierra el circuito: lo que sube el responsable vuelve marcado."""
        movimiento = self.movimiento()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                self.subir(movimiento, [imagen_en_memoria()])
        vencidos = self.obtener_datos()["vencidos"]
        self.assertEqual(
            len(vencidos), 1, "el hallazgo deberia seguir abierto y vencido"
        )
        self.assertIs(
            vencidos[0]["evidencia"],
            True,
            "despues de subir la foto el hallazgo tiene que salir marcado",
        )

    def test_hallazgo_de_otra_area_se_rechaza(self):
        ajeno = Movimientos.objects.create(
            cliente=self.cliente,
            area=self.otra_area,
            fecha=datetime.date.today(),
            periodo="Octubre",
            hallazgo="De seguridad",
            responsable="Beto",
            plazo=10,
            estado="Incumplido",
            fecha_cumplimiento=datetime.date.today(),
        )
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                respuesta = self.subir(ajeno, [imagen_en_memoria()])
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Evidencia.objects.count(), 0)

    def test_token_invalido_no_guarda_nada(self):
        movimiento = self.movimiento()
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                respuesta = self.subir(movimiento, [imagen_en_memoria()], token="no-es")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(Evidencia.objects.count(), 0)


TOKEN_REVISION = "token-de-prueba-para-la-bandeja"


class BandejaRevisionTest(BaseEnlacePublico):
    """
    La bandeja del administrador: ver la foto, aceptar o rechazar.

    El enlace del responsable y el del administrador son del mismo modelo y
    mismo alcance, pero `puede_revisar` los separa. Si no, un link filtrado
    permitiria subir evidencia Y cerrar hallazgos.
    """

    def setUp(self):
        super().setUp()
        EnlacePublicoHallazgos.objects.create(
            area=self.area,
            cliente_id=self.cliente.pk,
            token_hash=hashlib.sha256(TOKEN_REVISION.encode()).hexdigest(),
            expires_at=timezone.now() + datetime.timedelta(days=14),
            puede_revisar=True,
        )
        self.url_cola = reverse("utiles:evidencias_revision_datos")
        self.url_responder = reverse("utiles:evidencias_revision_responder")
        self.url_pagina = reverse("utiles:evidencias_revision_page")

    def evidencia(self, movimiento, con_foto=True):
        evidencia = Evidencia.objects.create(
            movimiento=movimiento,
            fecha=datetime.date.today(),
            origen="enlace_publico",
            subido_por="5493757677124",
        )
        if con_foto:
            with tempfile.TemporaryDirectory() as media:
                with override_settings(MEDIA_ROOT=media):
                    evidencia.archivo.save("foto.jpg", imagen_en_memoria(), save=True)
        return evidencia

    def cola(self, token=TOKEN_REVISION):
        respuesta = self.client.get(
            self.url_cola, HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        return respuesta

    def responder(self, evidencia, accion, motivo="", token=TOKEN_REVISION):
        datos = {"evidencia_id": evidencia.pk, "accion": accion,
                 "revisor": "Oscar"}
        if motivo:
            datos["motivo"] = motivo
        return self.client.post(
            self.url_responder, datos,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    # --- la cola -------------------------------------------------------

    def test_la_cola_muestra_las_pendientes(self):
        movimiento = self.movimiento()
        evidencia = self.evidencia(movimiento)
        respuesta = self.cola()
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["empresa"], "Cliente de prueba")
        self.assertEqual(datos["area"], "Sistemas")
        self.assertEqual(len(datos["pendientes"]), 1)
        self.assertEqual(datos["pendientes"][0]["id"], evidencia.pk)

    def test_lo_ya_revisado_sale_de_la_cola(self):
        movimiento = self.movimiento()
        evidencia = self.evidencia(movimiento)
        self.responder(evidencia, "aceptar")
        self.assertEqual(self.cola().json()["pendientes"], [])

    def test_la_cola_no_muestra_lo_que_no_tiene_foto(self):
        self.evidencia(self.movimiento(), con_foto=False)
        self.assertEqual(self.cola().json()["pendientes"], [])

    def test_la_pagina_de_revision_se_renderiza(self):
        respuesta = self.client.get(self.url_pagina)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Evidencias por validar", respuesta.content.decode())

    # --- seguridad -----------------------------------------------------

    def test_el_enlace_del_responsable_no_abre_la_bandeja(self):
        """Si el link de subir sirviera para revisar, alcanza para cerrar hallazgos."""
        self.evidencia(self.movimiento())
        self.assertEqual(self.cola(token=TOKEN).status_code, 404)

    def test_sin_token_no_hay_cola(self):
        self.evidencia(self.movimiento())
        self.assertEqual(self.client.get(self.url_cola).status_code, 404)

    def test_no_se_ve_la_foto_de_otra_area(self):
        ajeno = Movimientos.objects.create(
            id="mov9999999", cliente=self.cliente, area=self.otra_area,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo="De seguridad", responsable="Beto", plazo=10,
            estado="Incumplido",
            fecha_cumplimiento=datetime.date.today() - datetime.timedelta(days=10),
        )
        evidencia = self.evidencia(ajeno)
        url = reverse("utiles:evidencias_revision_imagen", args=[evidencia.pk])
        respuesta = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {TOKEN_REVISION}")
        self.assertEqual(respuesta.status_code, 403)

    def test_no_se_responde_sobre_evidencia_de_otra_area(self):
        ajeno = Movimientos.objects.create(
            id="mov9999999", cliente=self.cliente, area=self.otra_area,
            fecha=datetime.date.today(), periodo="Octubre",
            hallazgo="De seguridad", responsable="Beto", plazo=10,
            estado="Incumplido",
            fecha_cumplimiento=datetime.date.today() - datetime.timedelta(days=10),
        )
        evidencia = self.evidencia(ajeno)
        self.assertEqual(self.responder(evidencia, "aceptar").status_code, 400)
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.estado, Evidencia.ESTADO_PENDIENTE)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.estado, "Incumplido")

    # --- aceptar -------------------------------------------------------

    def test_aceptar_cierra_el_hallazgo(self):
        movimiento = self.movimiento()
        evidencia = self.evidencia(movimiento)
        with mock.patch("utiles.views.notificar_responsable_rechazo"):
            respuesta = self.responder(evidencia, "aceptar")
        self.assertEqual(respuesta.status_code, 200)
        movimiento.refresh_from_db()
        evidencia.refresh_from_db()
        self.assertEqual(movimiento.estado, "Cumplido")
        self.assertEqual(movimiento.fecha_realizado, timezone.localdate())
        self.assertEqual(evidencia.estado, Evidencia.ESTADO_ACEPTADA)
        self.assertEqual(evidencia.revisado_por, "Oscar")
        self.assertIsNotNone(evidencia.revisado_at)

    # --- rechazar ------------------------------------------------------

    def test_rechazar_exige_motivo(self):
        movimiento = self.movimiento()
        evidencia = self.evidencia(movimiento)
        respuesta = self.responder(evidencia, "rechazar", motivo="")
        self.assertEqual(respuesta.status_code, 400)
        movimiento.refresh_from_db()
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.estado, Evidencia.ESTADO_PENDIENTE)
        self.assertEqual(movimiento.estado, "Incumplido", "el hallazgo sigue abierto")

    def test_rechazar_avisa_al_responsable_con_el_motivo(self):
        movimiento = self.movimiento()
        evidencia = self.evidencia(movimiento)
        with mock.patch(
            "utiles.views.notificar_responsable_rechazo",
            return_value={"ok": True, "detalle": "notificado a 1"},
        ) as aviso:
            respuesta = self.responder(
                evidencia, "rechazar", motivo="No se ve el matafuego"
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(aviso.call_count, 1)
        movimiento.refresh_from_db()
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.estado, Evidencia.ESTADO_RECHAZADA)
        self.assertEqual(evidencia.motivo_rechazo, "No se ve el matafuego")
        self.assertEqual(movimiento.estado, "Incumplido", "rechazar no cierra el hallazgo")

    def test_no_se_revisa_dos_veces(self):
        evidencia = self.evidencia(self.movimiento())
        with mock.patch("utiles.views.notificar_responsable_rechazo"):
            self.responder(evidencia, "aceptar")
        segunda = self.responder(evidencia, "aceptar")
        self.assertEqual(segunda.status_code, 409)

    def test_accion_desconocida_se_rechaza(self):
        evidencia = self.evidencia(self.movimiento())
        self.assertEqual(self.responder(evidencia, "borrar").status_code, 400)


class EnlacePorContactoTest(BaseEnlacePublico):
    """
    El enlace de revision es POR ADMINISTRADOR, no uno solo por area.

    Con un link compartido no hay forma de saber quien aprobo: `revisado_por`
    quedaba siempre en "sin identificar".
    """

    def setUp(self):
        super().setUp()
        self.contacto = ContactoNotificacion.objects.create(
            nombre="Oscar Vogel", telefono="5493743667526",
            recibe_evidencias=True, activo=True,
        )
        ContactoNotificacion.objects.create(
            nombre="Otro admin", telefono="5493743667527",
            recibe_evidencias=True, activo=True,
        )
        ContactoNotificacion.objects.create(
            nombre="Admin apagado", telefono="5493743667528",
            recibe_evidencias=True, activo=False,
        )
        ContactoNotificacion.objects.create(
            nombre="Solo operacion", telefono="5493743667529",
            recibe_evidencias=False, recibe_alertas_operacion=True, activo=True,
        )

    def enlaces_de(self):
        return crear_enlaces_revision_admin(self.cliente.pk, self.area.pk)

    def test_cada_contacto_recibe_su_propio_enlace(self):
        enlaces = self.enlaces_de()
        self.assertEqual(len(enlaces), 2, "solo los dos activos con el rol")
        contactos = [contacto for contacto, _url in enlaces]
        self.assertEqual(
            len(set(contactos)), 2, "cada administrador recibe el suyo"
        )
        self.assertNotEqual(
            enlaces[0][1], enlaces[1][1], "los dos deben recibir links distintos"
        )

        # Y los enlaces existen de verdad, con su dueno y con permiso de revisar.
        duenos = set(
            EnlacePublicoHallazgos.objects.filter(puede_revisar=True)
            .values_list("contacto_id", flat=True)
        )
        self.assertEqual(duenos, {c.pk for c in contactos})

    def test_los_apagados_y_sin_rol_no_entran(self):
        nombres = {contacto.nombre for contacto, _url in self.enlaces_de()}
        self.assertEqual(nombres, {"Oscar Vogel", "Otro admin"})

    def test_la_decision_queda_firmada_con_el_contacto(self):
        contacto, url = self.enlaces_de()[0]
        token = url.split("#")[1]
        evidencia = Evidencia.objects.create(
            movimiento=self.movimiento(), fecha=datetime.date.today(),
            origen="enlace_publico",
        )

        respuesta = self.client.post(
            reverse("utiles:evidencias_revision_responder"),
            # "revisor" con un nombre falso: el que manda es el del link.
            {"evidencia_id": evidencia.pk, "accion": "aceptar", "revisor": "MENTIRA"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(respuesta.status_code, 200)
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.revisado_por, contacto.nombre)

    def test_el_nombre_va_tambien_en_la_bandeja(self):
        _contacto, url = self.enlaces_de()[0]
        datos = self.client.get(
            reverse("utiles:evidencias_revision_datos"),
            HTTP_AUTHORIZATION=f"Bearer {url.split('#')[1]}",
        ).json()
        self.assertEqual(datos["revisor"], "Oscar Vogel")

    def test_sin_contactos_no_hay_enlaces_pero_no_rompe(self):
        ContactoNotificacion.objects.all().delete()
        self.assertEqual(self.enlaces_de(), [])