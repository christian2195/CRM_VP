from django.urls import path
from . import views

app_name = 'admin_vpa'

urlpatterns = [
    path('', views.home_admin, name='index'),
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('base-datos/', views.estado_base_datos, name='estado_base_datos'),
    path('usuarios/editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
]