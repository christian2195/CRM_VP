from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Redirigir la raíz (/) directamente a la pantalla de login
    path('', RedirectView.as_view(pattern_name='login', permanent=False), name='index'),

    path('admin/', admin.site.urls),
    path('panel-control/', include('admin_vpa.urls')),
    
    # Rutas de Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Rutas de tu App
    path('facturacion/', include('facturacion.urls')), 
    
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
