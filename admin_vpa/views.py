from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.db import connection, transaction
from django.shortcuts import render, get_object_or_404, redirect
from facturacion.models import Cliente, Vehiculo, Cotizacion, ItemCotizacion, Factura
from .forms import UsuarioForm


def es_admin_o_gerencia(user):
    """Permite acceso a Superusuarios TI y al rol de Gerencia y Presidencia."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name='Gerencia y Presidencia').exists()


@user_passes_test(es_admin_o_gerencia)
def home_admin(request):
    context = {
        'total_usuarios': User.objects.count(),
        'usuarios_activos': User.objects.filter(is_active=True).count(),
        'total_clientes': Cliente.objects.count(),
        'total_vehiculos': Vehiculo.objects.count(),
        'vehiculos_disponibles': Vehiculo.objects.filter(estado='Disponible').count(),
        'vehiculos_apartados': Vehiculo.objects.filter(estado='Apartado').count(),
        'vehiculos_vendidos': Vehiculo.objects.filter(estado='Vendido').count(),
        'total_cotizaciones': Cotizacion.objects.exclude(estado='A').count(),
        'cotizaciones_anuladas': Cotizacion.objects.filter(estado='A').count(),
        'total_facturas': Factura.objects.exclude(estado_pago='ANULADA').count(),
        'facturas_anuladas': Factura.objects.filter(estado_pago='ANULADA').count(),
        'total_grupos': Group.objects.count(),
        'ultimos_logs': LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')[:12],
    }
    return render(request, 'admin_vpa/dashboard.html', context)


@user_passes_test(es_admin_o_gerencia)
def lista_usuarios(request):
    usuarios = User.objects.prefetch_related('groups', 'user_permissions').all().order_by('-date_joined')
    grupos = Group.objects.prefetch_related('permissions').all()
    return render(request, 'admin_vpa/usuarios.html', {'usuarios': usuarios, 'grupos': grupos})


@user_passes_test(es_admin_o_gerencia)
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                nuevo_usuario = form.save(commit=False)
                nueva_clave = form.cleaned_data.get('nueva_password')
                if nueva_clave:
                    nuevo_usuario.set_password(nueva_clave)
                else:
                    nuevo_usuario.set_password('Emvepro2026*')
                nuevo_usuario.save()
                form.save_m2m()
            messages.success(request, f"¡Funcionario '{nuevo_usuario.username}' creado y asignado a su rol con éxito!")
            return redirect('admin_vpa:lista_usuarios')
        else:
            messages.error(request, "Error al crear el usuario. Verifique los datos ingresados.")
    else:
        form = UsuarioForm()
        
    return render(request, 'admin_vpa/editar_usuario.html', {'form': form, 'creando': True})


@user_passes_test(es_admin_o_gerencia)
def editar_usuario(request, user_id):
    usuario_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario_obj)
        if form.is_valid():
            with transaction.atomic():
                user_editado = form.save(commit=False)
                nueva_clave = form.cleaned_data.get('nueva_password')
                if nueva_clave and nueva_clave.strip():
                    user_editado.set_password(nueva_clave.strip())
                user_editado.save()
                form.save_m2m()
            messages.success(request, f"¡Permisos y rol del usuario '{usuario_obj.username}' actualizados correctamente!")
            return redirect('admin_vpa:lista_usuarios')
        else:
            messages.error(request, "Por favor revise los campos del formulario.")
    else:
        form = UsuarioForm(instance=usuario_obj)
        
    return render(request, 'admin_vpa/editar_usuario.html', {'form': form, 'usuario_obj': usuario_obj})


@user_passes_test(es_admin_o_gerencia)
def inicializar_roles(request):
    """Crea o sincroniza los 4 Roles Institucionales de EMVEPRO C.A. con sus permisos."""
    ct_cliente = ContentType.objects.get_for_model(Cliente)
    ct_vehiculo = ContentType.objects.get_for_model(Vehiculo)
    ct_cotizacion = ContentType.objects.get_for_model(Cotizacion)
    ct_item = ContentType.objects.get_for_model(ItemCotizacion)
    ct_factura = ContentType.objects.get_for_model(Factura)

    roles_config = {
        'Gerencia y Presidencia': Permission.objects.filter(
            content_type__in=[ct_cliente, ct_vehiculo, ct_cotizacion, ct_item, ct_factura]
        ),
        'Comercio y Ventas': Permission.objects.filter(
            content_type__in=[ct_cliente, ct_cotizacion, ct_item]
        ) | Permission.objects.filter(content_type=ct_vehiculo, codename__startswith='view_'),
        'Facturacion y Cobranza': Permission.objects.filter(
            content_type=ct_factura
        ) | Permission.objects.filter(
            content_type__in=[ct_cliente, ct_cotizacion, ct_vehiculo], codename__startswith='view_'
        ),
        'Logistica e Inventario': Permission.objects.filter(
            content_type=ct_vehiculo
        ),
    }

    for nombre_rol, permisos in roles_config.items():
        grupo, _ = Group.objects.get_or_create(name=nombre_rol)
        grupo.permissions.set(permisos)

    messages.success(request, "¡Matriz de Roles Institucionales (Gerencia, Comercio, Facturación y Logística) sincronizada con éxito!")
    return redirect('admin_vpa:lista_usuarios')


@user_passes_test(es_admin_o_gerencia)
def estado_base_datos(request):
    db_name = str(connection.settings_dict.get('NAME', 'N/A'))
    if connection.vendor == 'postgresql':
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database();")
                db_name = cursor.fetchone()[0]
        except Exception:
            pass
    
    context = {
        'db_engine': connection.vendor.upper(),
        'db_name': db_name,
        'tablas_registradas': connection.introspection.table_names(),
    }
    return render(request, 'admin_vpa/base_datos.html', context)
