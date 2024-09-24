from django import forms
from .models import Movimientos

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
