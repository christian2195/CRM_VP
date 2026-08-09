from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Cliente, Vehiculo, Cotizacion, ItemCotizacion, Factura

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('identificacion', 'nombre_razon_social', 'tipo_documento', 'telefono')
    search_fields = ('identificacion', 'nombre_razon_social')
    list_filter = ('tipo_documento',)

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('marca', 'modelo', 'anio', 'placa', 'serial_carroceria_niv')
    search_fields = ('marca', 'modelo', 'placa', 'serial_carroceria_niv', 'serial_motor')
    list_filter = ('marca', 'anio', 'tipo', 'clase')

class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    # Añade 'usuario' a la lista
    list_display = ('id', 'cliente', 'estado', 'total', 'fecha_creacion', 'usuario')
    list_filter = ('estado', 'fecha_creacion', 'usuario') # Opcional: para filtrar por usuario
    search_fields = ('cliente__nombre_razon_social', 'cliente__identificacion')
    inlines = [ItemCotizacionInline]

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    # Añade 'usuario' a la lista
    list_display = ('numero_factura', 'numero_control', 'cotizacion', 'fecha_emision', 'total', 'usuario', 'boton_imprimir')
    list_filter = ('usuario', 'fecha_emision') # Opcional: para filtrar por usuario
    search_fields = ('numero_factura', 'numero_control', 'cotizacion__id')

    def boton_imprimir(self, obj):
        url = reverse('imprimir_factura', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank" style="background-color: #417690; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">🖨️ Imprimir</a>', url)
    boton_imprimir.short_description = 'Acción'