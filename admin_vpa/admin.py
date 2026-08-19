import os
from django.shortcuts import render

def dashboard_admin(request):
    # Verificamos si estamos en Docker basándonos en variables de entorno comunes
    is_docker = os.path.exists('/.dockerenv')
    
    context = {
        'sistema': 'EMVEPRO Admin',
        'entorno': 'Docker' if is_docker else 'Local',
        'usuarios_activos': User.objects.filter(is_active=True).count(),
        # Aquí puedes agregar lógica para leer logs o métricas de Docker
    }
    return render(request, 'admin_vpa/index.html', context)