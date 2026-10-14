from django import forms
from .models import Cotizacion, ItemCotizacion, Factura, Vehiculo, Cliente

class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['cliente', 'observaciones', 'fecha_emision', 'validez_dias', 'porcentaje_descuento', 'coletillas']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select select2-cliente'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Opcional...'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'validez_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'porcentaje_descuento': forms.NumberInput(attrs={'class': 'form-control text-end input-calc', 'min': '0', 'max': '100', 'step': '0.01'}),
            'coletillas': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Escriba las condiciones, garantías o notas de la venta...'}),
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
        fields = ['numero_factura', 'numero_control', 'fecha_emision', 'coletillas']
        widgets = {
            'numero_factura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 070887'}),
            'numero_control': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 00-000000'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'coletillas': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control form-control-sm'
            
        fechas = ['fecha_liquidacion', 'fecha_facturacion', 'fecha_fin_convenio']
        for fecha in fechas:
            if fecha in self.fields:
                self.fields[fecha].widget.attrs['type'] = 'date'

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
