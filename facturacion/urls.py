from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cotizacion/nueva/', views.crear_cotizacion, name='crear_cotizacion'), # <-- Nueva ruta
    path('cotizacion/imprimir/<int:cotizacion_id>/', views.imprimir_cotizacion, name='imprimir_cotizacion'),
    path('imprimir/<int:factura_id>/', views.imprimir_factura_forma_libre, name='imprimir_factura'),
    path('cotizacion/<int:cotizacion_id>/facturar/', views.generar_factura, name='generar_factura'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', views.crear_cliente, name='crear_cliente'),
    path('inventario/', views.lista_vehiculos, name='lista_vehiculos'),
    path('inventario/nuevo/', views.crear_vehiculo, name='crear_vehiculo'),
    path('inventario/editar/<int:vehiculo_id>/', views.editar_vehiculo, name='editar_vehiculo'),
    path('inventario/exportar/', views.exportar_inventario_excel, name='exportar_inventario'),
    path('inventario/importar/', views.importar_inventario_excel, name='importar_inventario'),
]