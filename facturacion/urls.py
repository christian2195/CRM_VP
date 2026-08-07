from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cotizacion/nueva/', views.crear_cotizacion, name='crear_cotizacion'), # <-- Nueva ruta
    path('imprimir/<int:factura_id>/', views.imprimir_factura_forma_libre, name='imprimir_factura'),
    path('cotizacion/<int:cotizacion_id>/facturar/', views.generar_factura, name='generar_factura'),
]