from dataclasses import fields
from random import choice
from django import forms
from .models import Area, Cliente, EmisionCarbono, ExcesosVelocidad, IndiceAccidentabilidad, Movimientos

class MovimientosForm(forms.ModelForm):
    class Meta:
        model = Movimientos
        fields = '__all__'
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'periodo': forms.TextInput(attrs={'class': 'form-control'}),
            'hallazgo': forms.Textarea(attrs={'class': 'form-control'}),
            'responsable': forms.Select(attrs={'class': 'form-control'}),
            'plazo': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'fecha_cumplimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_realizado': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre']

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['id', 'cliente', 'detalle', 'responsable']

class EmisionCarbonoForm(forms.ModelForm):

    class Meta:
        TIPO_CHOICES = [
            ('Diesel', 'Diesel'),
            ('Nafta', 'Nafta'),
            ('Aceite para Motores', 'Aceite para Motores'),
            ('Aceite Hidráulico', 'Aceite Hidráulico'),
            ('Aceite Lubricantes de Cadena', 'Aceite Lubricantes de Cadena'),
        ]
        model = EmisionCarbono
        fields = '__all__'
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}, choices=TIPO_CHOICES),
            'fe': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
        }

class IndiceAccidentabilidadAdminForm(forms.ModelForm):
    ANIOS_CHOICES = [(r, r) for r in range(2023, 2050)]
    MESES_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]

    anio = forms.ChoiceField(choices=ANIOS_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    mes = forms.ChoiceField(choices=MESES_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = IndiceAccidentabilidad
        fields = ['cliente', 'anio', 'mes', 'ACTP', 'ASTP', 'TPA', 'personal', 'hrs_hombres']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'ACTP': forms.NumberInput(attrs={'class': 'form-control'}),
            'ASTP': forms.NumberInput(attrs={'class': 'form-control'}),
            'TPA': forms.NumberInput(attrs={'class': 'form-control'}),
            'personal': forms.NumberInput(attrs={'class': 'form-control'}),
            'hrs_hombres': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ExcesosVelocidadAdminForm(forms.ModelForm):
    ANIOS_CHOICES = [(r, r) for r in range(2023, 2050)]
    MESES_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    SEMANAS_CHOICES = [(i, f'Semana {i}') for i in range(1, 6)]

    anio = forms.ChoiceField(choices=ANIOS_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    mes = forms.ChoiceField(choices=MESES_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    # semana = forms.ChoiceField(choices=SEMANAS_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = ExcesosVelocidad
        fields = ['cliente', 'anio', 'mes', 'excesos']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            # 'area': forms.Select(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'mes': forms.NumberInput(attrs={'class': 'form-control'}),
            # 'semana': forms.NumberInput(attrs={'class': 'form-control'}),
            'excesos': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['area'].queryset = Area.objects.none()

    #     if 'cliente' in self.data:
    #         try:
    #             cliente_id = int(self.data.get('cliente'))
    #             self.fields['area'].queryset = Area.objects.filter(cliente_id=cliente_id).order_by('nombre')
    #         except (ValueError, TypeError):
    #             pass
    #     elif self.instance.pk:
    #         self.fields['area'].queryset = self.instance.cliente.area_set.order_by('nombre')