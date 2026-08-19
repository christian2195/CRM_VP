from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from facturacion.models import Cliente, Vehiculo, Cotizacion, Factura
from .forms import UsuarioForm


def es_superusuario(user):
    return user.is_authenticated and user.is_superuser


@user_passes_test(es_superusuario)
def home_admin(request):
    context = {
        'total_usuarios': User.objects.count(),
        'total_clientes': Cliente.objects.count(),
        'total_vehiculos': Vehiculo.objects.count(),
        'total_cotizaciones': Cotizacion.objects.count(),
        'total_facturas': Factura.objects.count(),
        'ultimos_logs': LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:10],
    }
    return render(request, 'admin_vpa/dashboard.html', context)


@user_passes_test(es_superusuario)
def lista_usuarios(request):
    usuarios = User.objects.prefetch_related('groups', 'user_permissions').all().order_by('-date_joined')
    grupos = Group.objects.all()
    return render(request, 'admin_vpa/usuarios.html', {'usuarios': usuarios, 'grupos': grupos})


@user_passes_test(es_superusuario)
def editar_usuario(request, user_id):
    usuario_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario_obj)
        if form.is_valid():
            form.save()
            form.save_m2m() # <--- IMPORTANTE: Guarda los permisos seleccionados
            messages.success(request, f"Usuario {usuario_obj.username} actualizado.")
            return redirect('admin_vpa:lista_usuarios')
    else:
        form = UsuarioForm(instance=usuario_obj)
        
    return render(request, 'admin_vpa/editar_usuario.html', {'form': form, 'usuario_obj': usuario_obj})


@user_passes_test(es_superusuario)
def estado_base_datos(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
    
    context = {
        'db_engine': connection.vendor,
        'db_name': db_name,
        'tablas_registradas': connection.introspection.table_names(),
    }
    return render(request, 'admin_vpa/base_datos.html', context)