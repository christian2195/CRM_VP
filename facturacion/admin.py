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
    # Actualizado para mostrar el NIV y otros datos nuevos
    list_display = ('marca', 'modelo', 'placa', 'serial_niv', 'cliente')
    search_fields = ('placa', 'serial_niv', 'serial_motor', 'cliente__nombre_razon_social')

class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    # Cambiamos 'vehiculo' por 'cliente'
    list_display = ('id', 'cliente', 'estado', 'total', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('cliente__nombre_razon_social', 'cliente__identificacion')
    inlines = [ItemCotizacionInline]

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    # Agregamos 'boton_imprimir' al final de la lista
    list_display = ('numero_factura', 'numero_control', 'cotizacion', 'fecha_emision', 'total', 'boton_imprimir')
    search_fields = ('numero_factura', 'numero_control', 'cotizacion__id')

    # Creamos la función que dibuja el botón
    def boton_imprimir(self, obj):
        # Genera la URL automáticamente buscando el nombre 'imprimir_factura'
        url = reverse('imprimir_factura', args=[obj.id])
        # Retorna un botón HTML que se abre en una pestaña nueva
        return format_html('<a class="button" href="{}" target="_blank" style="background-color: #417690; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">🖨️ Imprimir</a>', url)
    
    boton_imprimir.short_description = 'Acción'