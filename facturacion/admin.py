from django.contrib import admin
from django.utils.html import format_html
from decimal import Decimal
from .models import Cliente, Vehiculo, Cotizacion, ItemCotizacion, Factura

# --- TÍTULOS INSTITUCIONALES DEL PANEL ---
admin.site.site_header = "EMVEPRO C.A. — Administración Central CRM v3.0"
admin.site.site_title = "Panel Admin CRM EMVEPRO"
admin.site.index_title = "Gestión de Parque Automotor, Presupuestos y Facturación Fiscal"


def fmt_ve(valor):
    """Formatea números al estándar venezolano: 10.045.812,00"""
    if valor is None or valor == '':
        valor = Decimal('0.00')
    return f"{Decimal(str(valor)):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ==========================================
# 1. ADMINISTRACIÓN DE CLIENTES
# ==========================================
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('documento_completo', 'nombre_razon_social', 'telefono', 'email', 'total_cotizaciones')
    list_filter = ('tipo_documento',)
    search_fields = ('identificacion', 'nombre_razon_social', 'telefono', 'email')
    ordering = ('-id',)
    list_per_page = 25

    @admin.display(description='RIF / Cédula')
    def documento_completo(self, obj):
        return format_html('<strong style="color: #273376; font-family: monospace;">{}-{}</strong>', obj.tipo_documento, obj.identificacion)

    @admin.display(description='Cotizaciones')
    def total_cotizaciones(self, obj):
        cant = obj.cotizaciones.count()
        return format_html(
            '<span style="background:#eef2ff; color:#273376; padding:2px 10px; border-radius:12px; font-weight:bold;">{}</span>',
            cant
        )


# ==========================================
# 2. ADMINISTRACIÓN DE INVENTARIO VEHICULAR
# ==========================================
@admin.action(description="Marcar unidades seleccionadas como DISPONIBLES")
def marcar_disponible(modeladmin, request, queryset):
    queryset.update(estado='Disponible')

@admin.action(description="Marcar unidades seleccionadas como APARTADAS")
def marcar_apartado(modeladmin, request, queryset):
    queryset.update(estado='Apartado')

@admin.action(description="Marcar unidades seleccionadas como VENDIDAS")
def marcar_vendido(modeladmin, request, queryset):
    queryset.update(estado='Vendido')


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('placa_badge', 'marca', 'modelo', 'anio', 'color', 'serial_carroceria_niv', 'serial_motor', 'estado_badge')
    list_filter = ('estado', 'marca', 'anio', 'clase', 'tipo_combustible', 'puerto_entrada')
    search_fields = ('placa', 'serial_carroceria_niv', 'serial_motor', 'marca', 'modelo', 'certificado_origen')
    actions = [marcar_disponible, marcar_apartado, marcar_vendido]
    list_per_page = 30

    fieldsets = (
        ('Especificaciones Técnicas', {
            'fields': (
                ('marca', 'modelo', 'anio', 'color'),
                ('placa', 'clase', 'tipo', 'uso'),
                ('transmision', 'tipo_combustible', 'num_puestos', 'num_ejes'),
                ('peso_tara', 'capacidad_carga'),
            )
        }),
        ('Seriales de Identificación', {
            'fields': (('serial_carroceria_niv', 'serial_motor'),)
        }),
        ('Nacionalización, Aduana y Convenio', {
            'fields': (
                ('certificado_origen', 'servicio', 'puerto_entrada'),
                ('planilla_liquidacion', 'fecha_liquidacion'),
                ('factura_adquisicion', 'fecha_facturacion'),
                ('refeciv', 'fecha_fin_convenio'),
            )
        }),
        ('Control de Stock', {
            'fields': ('estado',)
        }),
    )

    @admin.display(description='Placa')
    def placa_badge(self, obj):
        placa = obj.placa or 'S/P'
        return format_html('<span style="font-family: monospace; font-weight: bold;">[{}]</span>', placa)

    @admin.display(description='Estatus Inventario')
    def estado_badge(self, obj):
        colores = {
            'Disponible': ('#d1e7dd', '#0f5132'),
            'Apartado': ('#fff3cd', '#664d03'),
            'Vendido': ('#f8d7da', '#842029'),
        }
        bg, fg = colores.get(obj.estado, ('#e2e3e5', '#41464b'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            bg, fg, obj.estado
        )


# ==========================================
# 3. ADMINISTRACIÓN DE COTIZACIONES + ÍTEMS
# ==========================================
class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 0
    autocomplete_fields = ['vehiculo']
    fields = ('vehiculo', 'descripcion', 'cantidad', 'precio_unitario', 'aplica_iva')


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('codigo_vp', 'cliente', 'fecha_emision', 'usuario', 'estado_badge', 'total_usd_fmt', 'ver_pdf')
    list_filter = ('estado', 'fecha_creacion', 'usuario')
    search_fields = ('id', 'cliente__nombre_razon_social', 'cliente__identificacion')
    autocomplete_fields = ['cliente']
    inlines = [ItemCotizacionInline]
    readonly_fields = ('fecha_creacion', 'monto_descuento', 'base_imponible', 'monto_exento', 'impuesto_iva', 'total')
    list_per_page = 25

    fieldsets = (
        ('Información General', {
            'fields': (('cliente', 'usuario', 'estado'), ('fecha_emision', 'validez_dias'))
        }),
        ('Descuentos y Condiciones Comerciales', {
            'fields': ('porcentaje_descuento', 'coletillas', 'observaciones')
        }),
        ('Totales Calculados (USD)', {
            'fields': (('base_imponible', 'monto_exento', ' monto_descuento' if False else 'monto_descuento'), ('impuesto_iva', 'total'))
        }),
    )

    @admin.display(description='N° Cotización')
    def codigo_vp(self, obj):
        return format_html('<strong style="color: #273376;">#VP-{}</strong>', obj.id)

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        mapa = {
            'B': ('Borrador', '#e2e3e5', '#41464b'),
            'P': ('Pendiente', '#fff3cd', '#664d03'),
            'E': ('Emitida', '#cff4fc', '#055160'),
            'F': ('Facturada', '#d1e7dd', '#0f5132'),
            'A': ('Anulada', '#f8d7da', '#842029'),
        }
        texto, bg, fg = mapa.get(obj.estado, ('Pendiente', '#fff3cd', '#664d03'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            bg, fg, texto
        )

    @admin.display(description='Total ($)')
    def total_usd_fmt(self, obj):
        return format_html('<strong style="font-family: monospace;">$ {}</strong>', fmt_ve(obj.total))

    @admin.display(description='Presupuesto')
    def ver_pdf(self, obj):
        return format_html(
            '<a href="/facturacion/cotizaciones/imprimir/{}/" target="_blank" style="background:#273376; color:white; padding:3px 10px; border-radius:8px; text-decoration:none; font-size:11px; font-weight:bold;">PDF</a>',
            obj.id
        )


# ==========================================
# 4. ADMINISTRACIÓN DE FACTURAS FISCALES
# ==========================================
@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'numero_control', 'cliente_nombre', 'fecha_emision', 'tasa_fmt', 'estado_pago_badge', 'porcentaje_barra', 'total_bs_fmt')
    list_filter = ('estado_pago', 'fecha_emision', 'usuario')
    search_fields = ('numero_factura', 'numero_control', 'cotizacion__cliente__nombre_razon_social', 'cotizacion__cliente__identificacion')
    readonly_fields = ('base_imponible', 'monto_exento', 'impuesto_iva', 'total')
    list_per_page = 25

    fieldsets = (
        ('Datos Fiscales Serie A', {
            'fields': (('numero_factura', 'numero_control'), ('fecha_emision', 'tasa_cambio'), ('cotizacion', 'usuario'))
        }),
        ('Control de Cobranza', {
            'fields': (('estado_pago', 'porcentaje_pago'),)
        }),
        ('Totales Fiscales (Bs.)', {
            'fields': (('base_imponible', 'monto_exento'), ('impuesto_iva', 'total'))
        }),
        ('Condiciones Legales', {
            'fields': ('coletillas',)
        }),
    )

    @admin.display(description='Cliente')
    def cliente_nombre(self, obj):
        return obj.cotizacion.cliente.nombre_razon_social

    @admin.display(description='Tasa BCV')
    def tasa_fmt(self, obj):
        return format_html('<span style="font-family: monospace;">Bs. {}</span>', fmt_ve(obj.tasa_cambio))

    @admin.display(description='Estatus Pago')
    def estado_pago_badge(self, obj):
        mapa = {
            'PAGADA': ('Pagada', '#d1e7dd', '#0f5132'),
            'PARCIAL': ('Pago Parcial', '#fff3cd', '#664d03'),
            'PENDIENTE': ('Por Pagar', '#e2e3e5', '#41464b'),
            'ANULADA': ('Anulada', '#f8d7da', '#842029'),
        }
        texto, bg, fg = mapa.get(obj.estado_pago, ('Por Pagar', '#e2e3e5', '#41464b'))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            bg, fg, texto
        )

    @admin.display(description='% Cobro')
    def porcentaje_barra(self, obj):
        color = '#198754' if obj.porcentaje_pago == 100 else ('#ffc107' if obj.porcentaje_pago > 0 else '#6c757d')
        return format_html(
            '<span style="font-family: monospace; font-weight: bold; color: {};">{}%</span>',
            color, obj.porcentaje_pago
        )

    @admin.display(description='Total (Bs.)')
    def total_bs_fmt(self, obj):
        return format_html('<strong style="font-family: monospace; color: #273376;">Bs. {}</strong>', fmt_ve(obj.total))
