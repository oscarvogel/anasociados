"""Tests de `home`: el Tablero y, con el, el boton de menu del celular.

El boton de menu no es un detalle de moda: es la unica forma de llegar al
menu desde el celular. Si el boton no se ve, desde el telefono no hay forma de
entrar al resumen por WhatsApp ni al PDF de los pendientes.
"""
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase


class MenuMovilTest(TestCase):
    """
    Las tres rayas del boton de menu.

    En el tema de Colorlib son blancas, porque su header es azul oscuro. El
    diseno AN tiene el header blanco: las rayas quedaron blancas sobre blanco
    y el boton no se veia. Desde el celular no se abria el menu.
    """

    def setUp(self):
        self.superusuario = User.objects.create_superuser("an", "an@example.com", "x")
        self.peticion = RequestFactory().get("/")
        self.peticion.user = self.superusuario

    def test_el_header_tiene_el_boton_de_menu(self):
        html = render_to_string("includes/navigation.html", request=self.peticion)
        self.assertIn('id="mobile-collapse1"', html)

    def test_las_rayas_del_boton_no_son_blancas(self):
        """Ninguna regla puede dejar las rayas en blanco sobre el header blanco."""
        archivo = Path(settings.BASE_DIR) / "static" / "src" / "css" / "an-custom.css"
        texto = archivo.read_text(encoding="utf-8")
        reglas = re.findall(r"([^{}]+)\{([^{}]*)\}", texto)
        rayas = [
            cuerpo
            for selector, cuerpo in reglas
            if ".mobile-menu" in selector
            and "span" in selector
            and ".pcoded-header" in selector
        ]
        self.assertTrue(
            rayas, "No hay ninguna regla para las rayas del boton de menu del header."
        )
        for cuerpo in rayas:
            self.assertNotIn("#fff", cuerpo.lower())
            self.assertNotIn("white", cuerpo.lower())

    def test_el_boton_queda_por_encima_de_la_mascara(self):
        """La mascara del menu abierto se pinta sobre el boton que la cierra:
        sin esto la X no se puede apretar."""
        archivo = Path(settings.BASE_DIR) / "static" / "src" / "css" / "an-custom.css"
        texto = archivo.read_text(encoding="utf-8")
        self.assertIn(
            ".an-app .pcoded-header .mobile-menu { z-index: 2; }",
            texto.replace("\n", " ").replace("  ", " "),
        )


class EstaticosVersionadosTest(TestCase):
    """
    Los estaticos llevan la version del archivo en la URL.

    Nginx los sirve sin Cache-Control, asi que el navegador se queda con el
    archivo viejo por horas. Fue lo que paso con el boton de menu: el servidor
    ya servia el CSS nuevo y el telefono seguia sin ver las rayas.
    """

    def setUp(self):
        self.superusuario = User.objects.create_superuser("an", "an@example.com", "x")
        self.peticion = RequestFactory().get("/")
        self.peticion.user = self.superusuario

    def test_el_css_de_an_lleva_la_version(self):
        html = render_to_string("includes/head.html", request=self.peticion)
        self.assertIn("an-custom.css?v=", html)

    def test_el_js_de_an_lleva_la_version(self):
        html = render_to_string("includes/scripts.html", request=self.peticion)
        self.assertIn("an-autocomplete.js?v=", html)

    def test_la_version_es_la_del_archivo(self):
        """La version sale de la fecha de modificacion: cambia sola en cada
        despliegue, sin que nadie se acuerde de subirla a mano."""
        archivo = Path(settings.BASE_DIR) / "static" / "src" / "css" / "an-custom.css"
        version = int(archivo.stat().st_mtime)
        html = render_to_string("includes/head.html", request=self.peticion)
        self.assertIn(f"an-custom.css?v={version}", html)
