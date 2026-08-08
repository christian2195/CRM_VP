from django import forms
from .models import Cotizacion, ItemCotizacion, Factura, Vehiculo, Cliente

class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['cliente', 'observaciones']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Opcional...'}),
        }

class ItemCotizacionForm(forms.ModelForm):
    class Meta:
        model = ItemCotizacion
        fields = ['vehiculo', 'descripcion', 'cantidad', 'precio_unitario', 'aplica_iva']
        widgets = {
            'vehiculo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aplica_iva': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['numero_factura', 'numero_control', 'fecha_emision']
        widgets = {
            'numero_factura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 070887'}),
            'numero_control': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 00-000000'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = '__all__' # Queremos todos los campos para las ambulancias
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le ponemos estilo Bootstrap a todas las cajas de texto automáticamente
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control form-control-sm'
            
        # Algunas cajas específicas necesitan ser tipo 'date' (calendario)
        fechas = ['fecha_liquidacion', 'fecha_facturacion', 'fecha_fin_convenio']
        for fecha in fechas:
            if fecha in self.fields:
                self.fields[fecha].widget.attrs['type'] = 'date'

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__' # Traemos todos los campos del cliente
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicamos el estilo de Bootstrap a todas las cajas de texto
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control form-control-sm'