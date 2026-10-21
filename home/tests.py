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
        """La mascara del menu abierto se paints sobre el boton que la cierra:
        sin esto la X no se puede apretar."""
        archivo = Path(settings.BASE_DIR) / "static" / "src" / "css" / "an-custom.css"
        texto = archivo.read_text(encoding="utf-8")
        self.assertIn(
            ".an-app .pcoded-header .mobile-menu { z-index: 2; }",
            texto.replace("\n", " ").replace("  ", " "),
        )
