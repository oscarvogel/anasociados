from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, formset_factory

from .models import Profile
from syh.models import Area, Cliente
from utiles.notificaciones import WhatsAppClient, WhatsAppError


class UserManagementForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.order_by("nombre"),
        label="Empresa",
        empty_label="Seleccioná una empresa",
        required=False,
        help_text=(
            "Opcional. Si la dejas vacía se conserva la empresa actual; "
            "si el usuario no tenía ninguna, se guarda sin perfil."
        ),
    )
    password1 = forms.CharField(
        label="Contraseña inicial o nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Dejala vacía al editar para conservar la contraseña actual.",
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "is_active")
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
            "is_active": "Cuenta habilitada",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"
        if self.instance and self.instance.pk:
            try:
                self.fields["cliente"].initial = Profile.objects.get(user=self.instance).cliente_id
            except Profile.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1") or ""
        password2 = cleaned_data.get("password2") or ""

        if not self.instance.pk and not password1:
            self.add_error("password1", "Ingresá una contraseña inicial.")
        if password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if password1 and password1 == password2:
            password_user = User(
                username=cleaned_data.get("username", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
                email=cleaned_data.get("email", ""),
            )
            try:
                password_validation.validate_password(password1, password_user)
            except ValidationError as exc:
                self.add_error("password1", exc)

        return cleaned_data


class AreaAssignmentForm(forms.Form):
    area = forms.ModelChoiceField(
        queryset=Area.objects.none(),
        label="Área",
        empty_label="Seleccioná un área",
        required=True,
    )
    telefono_whatsapp = forms.CharField(
        label="WhatsApp del encargado",
        max_length=32,
        required=False,
        help_text="Número internacional, por ejemplo 5493764000000.",
    )

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        if cliente:
            self.fields["area"].queryset = Area.objects.filter(cliente=cliente).order_by("detalle")

    def clean_telefono_whatsapp(self):
        telefono = self.cleaned_data.get("telefono_whatsapp", "").strip()
        if not telefono:
            return ""
        try:
            return WhatsAppClient().normalizar_telefono(telefono)
        except WhatsAppError as exc:
            raise ValidationError(str(exc)) from exc


class BaseAreaAssignmentFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_area_ids = set()
        for form in self.forms:
            cleaned_data = getattr(form, "cleaned_data", {})
            if cleaned_data.get("DELETE"):
                continue
            area = cleaned_data.get("area")
            if area is None:
                continue
            if area.pk in seen_area_ids:
                form.add_error("area", "Esa área ya está asignada a este usuario.")
            seen_area_ids.add(area.pk)


AreaAssignmentFormSet = formset_factory(
    AreaAssignmentForm,
    formset=BaseAreaAssignmentFormSet,
    extra=1,
    can_delete=True,
)
