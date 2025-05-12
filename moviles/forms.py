# forms.py
from django import forms
from .models import Matafuegos, Cliente, Area

class MatafuegosForm(forms.ModelForm):
    # Opcional: Puedes hacer que el campo 'area' sea inicialmente vacío
    # y se llene dinámicamente con JavaScript.
    # Sin embargo, el ModelForm por defecto manejará la relación FK correctamente.
    # Si quieres forzar la selección después de elegir cliente, podrías hacer esto
    # area = forms.ModelChoiceField(queryset=Area.objects.none(), required=False)

    class Meta:
        model = Matafuegos
        fields = '__all__' # O especifica los campos que quieres en el formulario
        widgets = {
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_baja': forms.DateInput(attrs={'type': 'date'}),
        }

    # Si hiciste 'area = forms.ModelChoiceField(queryset=Area.objects.none()...)'
    # necesitas sobrescribir __init__ para filtrar las áreas si se edita un objeto existente
    # def __init__(self, *args, **kwargs):
    #     instance = kwargs.get('instance', None)
    #     super().__init__(*args, **kwargs)
    #     if instance and instance.cliente:
    #         self.fields['area'].queryset = Area.objects.filter(cliente=instance.cliente)
    #     elif 'cliente' in self.initial: # Si se pasa un cliente inicial (ej: al crear desde la lista filtrada)
    #          self.fields['area'].queryset = Area.objects.filter(cliente_id=self.initial['cliente'])