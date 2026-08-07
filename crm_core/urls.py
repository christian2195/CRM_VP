from django.contrib import admin
from django.urls import path, include # <-- Importa 'include'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('facturacion/', include('facturacion.urls')), # <-- Agrega esta línea
]