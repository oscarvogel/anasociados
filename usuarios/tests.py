from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from syh.models import Area, Cliente
from .models import AreasProfile, Profile


class UserManagementEditTests(TestCase):
    """Reproduce el guardado de la pantalla 'Gestion de usuarios'.

    El caso que importa es el que reporta el usuario: desmarcar 'Cuenta
    habilitada' y guardar tiene que dejar la cuenta con is_active=False.
    """

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root", email="root@an.com.ar", password="ClaveSegura123"
        )
        self.cliente = Cliente.objects.create(id="FG01", nombre="Forestal Garuhape", email="fg@an.com.ar")
        self.area = Area.objects.create(
            id="A001", cliente=self.cliente, detalle="Tala", responsable="Garuhape", email="area@an.com.ar"
        )
        self.usuario = User.objects.create_user(
            username="fg", first_name="Forestal", last_name="Garuhape", password="ClaveSegura123"
        )
        Profile.objects.create(user=self.usuario, cliente=self.cliente)
        AreasProfile.objects.create(
            user=self.usuario, area=self.area, telefono_whatsapp="5493764000000"
        )
        self.client.force_login(self.superuser)

    def _post(self, **extra):
        datos = {
            "username": self.usuario.username,
            "first_name": self.usuario.first_name,
            "last_name": self.usuario.last_name,
            "email": "",
            "cliente": str(self.cliente.pk),
            "password1": "",
            "password2": "",
            "areas-TOTAL_FORMS": "1",
            "areas-INITIAL_FORMS": "1",
            "areas-MIN_NUM_FORMS": "0",
            "areas-MAX_NUM_FORMS": "1000",
            "areas-0-area": str(self.area.pk),
            "areas-0-telefono_whatsapp": "5493764000000",
        }
        datos.update(extra)
        return self.client.post(
            reverse("usuarios:management_user_edit", args=[self.usuario.pk]), datos
        )

    def test_desmarcar_cuenta_habilitada_se_guarda(self):
        self.assertTrue(self.usuario.is_active)
        # El checkbox desmarcado NO viaja en el POST, asi que este caso prueba
        # justamente el gesto que hace el operador.
        self._post()
        self.usuario.refresh_from_db()
        self.assertFalse(
            self.usuario.is_active,
            "La cuenta quedo habilitada: is_active no llego a la base.",
        )

    def test_marcar_cuenta_habilitada_se_guarda(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])
        self._post(**{"is_active": "on"})
        self.usuario.refresh_from_db()
        self.assertTrue(
            self.usuario.is_active,
            "La cuenta quedo inhabilitada: is_active=1 no llego a la base.",
        )

    def test_editar_con_empresa_conserva_areas_y_perfil(self):
        """No-regresion del fix: empresa vacia = no cambiar, no borrar."""
        respuesta = self._post(cliente="")
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            Profile.objects.filter(user=self.usuario).exists(), "Se perdio el perfil."
        )
        self.assertTrue(
            AreasProfile.objects.filter(user=self.usuario, area=self.area).exists(),
            "Se perdio el area asignada por dejar la empresa vacia.",
        )


class UsuarioSinEmpresaTests(TestCase):
    """El caso de la captura: cuenta sin `Profile`, o sea sin empresa.

    Ahi el formulario se abre con 'Empresa' vacio. Si el operador solo quiere
    deshabilitar la cuenta y toca guardar sin elegir empresa, el POST es
    invalido, no se guarda NADA y la pagina vuelve con 'Este campo es
    requerido'. El cambio de 'Cuenta habilitada' se pierde en silencio, que es
    justo lo que se reporta.
    """

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="root", email="root@an.com.ar", password="ClaveSegura123"
        )
        self.usuario = User.objects.create_user(
            username="fg", first_name="Forestal", last_name="Garuhape", password="ClaveSegura123"
        )
        self.client.force_login(self.superuser)

    def _post_sin_empresa(self):
        datos = {
            "username": "fg",
            "first_name": "Forestal",
            "last_name": "Garuhape",
            "email": "",
            "cliente": "",
            "password1": "",
            "password2": "",
            "areas-TOTAL_FORMS": "1",
            "areas-INITIAL_FORMS": "0",
            "areas-MIN_NUM_FORMS": "0",
            "areas-MAX_NUM_FORMS": "1000",
            "areas-0-area": "",
            "areas-0-telefono_whatsapp": "",
        }
        return self.client.post(
            reverse("usuarios:management_user_edit", args=[self.usuario.pk]), datos
        )

    def test_deshabilitar_sin_elegir_empresa_se_guarda(self):
        """El gesto del usuario: desmarcar y guardar, sin tocar empresa."""
        self._post_sin_empresa()
        self.usuario.refresh_from_db()
        self.assertFalse(
            self.usuario.is_active,
            "La cuenta quedo habilitada: elegir empresa no deberia ser obligatorio "
            "para cambiar el estado de la cuenta.",
        )

    def test_deshabilitar_sin_elegir_empresa_no_crea_perfil(self):
        """Sin empresa no se inventa un perfil: la tabla es preexistente."""
        self._post_sin_empresa()
        self.assertFalse(
            Profile.objects.filter(user=self.usuario).exists(),
            "Se creo un perfil sin empresa.",
        )