from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cotizacion/nueva/', views.crear_cotizacion, name='crear_cotizacion'), # <-- Nueva ruta
    path('cotizacion/imprimir/<int:cotizacion_id>/', views.imprimir_cotizacion, name='imprimir_cotizacion'),
    path('imprimir/<int:factura_id>/', views.imprimir_factura_forma_libre, name='imprimir_factura'),
    path('facturacion/imprimir-institucional/<int:factura_id>/', views.imprimir_factura_institucional, name='imprimir_factura_institucional'),
    path('cotizacion/<int:cotizacion_id>/facturar/', views.generar_factura, name='generar_factura'),
    path('cotizaciones/', views.lista_cotizaciones, name='lista_cotizaciones'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', views.crear_cliente, name='crear_cliente'),
    path('inventario/', views.lista_vehiculos, name='lista_vehiculos'),
    path('inventario/nuevo/', views.crear_vehiculo, name='crear_vehiculo'),
    path('inventario/editar/<int:vehiculo_id>/', views.editar_vehiculo, name='editar_vehiculo'),
    path('inventario/exportar/', views.exportar_inventario_excel, name='exportar_inventario'),
    path('inventario/importar/', views.importar_inventario_excel, name='importar_inventario'),
    path('facturacion/certificado/<int:factura_id>/', views.imprimir_certificado_origen, name='imprimir_certificado'),
    path('finanzas/', views.estado_financiero, name='estado_financiero'),
    path('factura/<int:factura_id>/actualizar-pago/', views.actualizar_pago_factura, name='actualizar_pago_factura'),
    path('facturas/historial/', views.historial_facturas, name='historial_facturas'),
    path('facturas/exportar-excel/', views.exportar_facturas_excel, name='exportar_facturas_excel'),
    path('facturacion/imprimir-institucional-sin-sap/<int:factura_id>/', views.imprimir_factura_institucional_sin_sap, name='imprimir_factura_institucional_sin_sap'),
]