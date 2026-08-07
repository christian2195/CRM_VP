from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from .models import Factura
from django.shortcuts import render
from .models import Factura, Cotizacion, Vehiculo, ItemCotizacion
from .forms import CotizacionForm
from django.utils import timezone
from .forms import FacturaForm
from django.db import transaction

def imprimir_factura_forma_libre(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    
    # --- CABECERA ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(420, 750, f"FACTURA N°: {factura.numero_factura}")
    p.drawString(420, 735, f"FECHA DE EMISIÓN: {factura.fecha_emision.strftime('%d/%m/%Y')}")
    
    p.drawString(50, 720, "NOMBRE(S) Y APELLIDO (S) O RAZÓN SOCIAL:")
    p.setFont("Helvetica", 10)
    p.drawString(300, 720, f"{cliente.nombre_razon_social}")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, 705, "C.I./R.I.F:")
    p.setFont("Helvetica", 10)
    p.drawString(120, 705, f"{cliente.tipo_documento}-{cliente.identificacion}")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(300, 705, "TELÉFONO:")
    p.setFont("Helvetica", 10)
    p.drawString(370, 705, f"{cliente.telefono or ''}")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, 690, "DIRECCIÓN:")
    p.setFont("Helvetica", 9)
    p.drawString(120, 690, f"{cliente.direccion[:100]}")
    
    # --- ITEMS ---
    # Imprimimos las cabeceras. Si la forma libre ya las trae preimpresas, puedes borrar estas 6 líneas
    y_items = 650
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, y_items, "CANTIDAD")
    p.drawString(110, y_items, "DESCRIPCION")
    p.drawString(300, y_items, "TIPO DE IVA")
    p.drawString(380, y_items, "ALIC%.")
    p.drawString(450, y_items, "PREC.Bs.")
    
    y_items -= 20
    p.setFont("Helvetica", 9)
    
    vehiculo_principal = None

    for item in cotizacion.items.all():
        # Capturamos el primer vehículo que encontremos para armar la ficha técnica más abajo
        if item.vehiculo and not vehiculo_principal:
            vehiculo_principal = item.vehiculo
            
        tipo_iva = "ALIC. GENER." if item.aplica_iva else "EXENTO"
        alic_porcentaje = "16,00%" if item.aplica_iva else "0,00%"
        
        p.drawString(65, y_items, str(item.cantidad))
        p.drawString(110, y_items, item.descripcion[:40])
        p.drawString(300, y_items, tipo_iva)
        p.drawString(385, y_items, alic_porcentaje)
        p.drawString(450, y_items, f"{item.precio_unitario:,.2f}")
        y_items -= 15

    # --- FICHA TÉCNICA DEL VEHÍCULO ---
    if vehiculo_principal:
        y_vehiculo = y_items - 30
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y_vehiculo, "DESCRIPCIÓN DEL VEHÍCULO")
        
        y_vehiculo -= 20
        p.setFont("Helvetica-Bold", 9)
        
        # Textos - Columna Izquierda
        p.drawString(50, y_vehiculo, "MARCA:")
        p.drawString(50, y_vehiculo-15, "MODELO:")
        p.drawString(50, y_vehiculo-30, "COLOR:")
        p.drawString(50, y_vehiculo-45, "PLACA:")
        p.drawString(50, y_vehiculo-60, "AÑO:")
        p.drawString(50, y_vehiculo-75, "CLASE:")
        p.drawString(50, y_vehiculo-90, "TIPO:")
        p.drawString(50, y_vehiculo-105, "USO:")
        p.drawString(50, y_vehiculo-120, "TRANSMISIÓN:")
        
        # Valores - Columna Izquierda
        p.setFont("Helvetica", 9)
        p.drawString(130, y_vehiculo, str(vehiculo_principal.marca))
        p.drawString(130, y_vehiculo-15, str(vehiculo_principal.modelo))
        p.drawString(130, y_vehiculo-30, str(vehiculo_principal.color))
        p.drawString(130, y_vehiculo-45, str(vehiculo_principal.placa or ''))
        p.drawString(130, y_vehiculo-60, str(vehiculo_principal.anio))
        p.drawString(130, y_vehiculo-75, str(vehiculo_principal.clase or ''))
        p.drawString(130, y_vehiculo-90, str(vehiculo_principal.tipo or ''))
        p.drawString(130, y_vehiculo-105, str(vehiculo_principal.uso or ''))
        p.drawString(130, y_vehiculo-120, str(vehiculo_principal.transmision or ''))

        # Textos - Columna Derecha
        p.setFont("Helvetica-Bold", 9)
        p.drawString(280, y_vehiculo, "TIPO DE COMBUSTIBLE:")
        p.drawString(280, y_vehiculo-15, "N° DE PUESTO:")
        p.drawString(280, y_vehiculo-30, "N° EJES :")
        p.drawString(280, y_vehiculo-45, "PESO (TARA):")
        p.drawString(280, y_vehiculo-60, "CAPACIDAD DE CARGA (KG.):")
        p.drawString(280, y_vehiculo-75, "SERIAL DE MOTOR:")
        p.drawString(280, y_vehiculo-90, "SERIAL DE CARROCERIA:")
        p.drawString(280, y_vehiculo-105, "SERIAL NIV:")
        p.drawString(280, y_vehiculo-120, "SERIE/VERSIÓN:")
        
        # Valores - Columna Derecha
        p.setFont("Helvetica", 9)
        p.drawString(430, y_vehiculo, str(vehiculo_principal.tipo_combustible or ''))
        p.drawString(430, y_vehiculo-15, str(vehiculo_principal.num_puestos or ''))
        p.drawString(430, y_vehiculo-30, str(vehiculo_principal.num_ejes or ''))
        p.drawString(430, y_vehiculo-45, str(vehiculo_principal.peso_tara or ''))
        p.drawString(430, y_vehiculo-60, str(vehiculo_principal.capacidad_carga or ''))
        p.drawString(430, y_vehiculo-75, str(vehiculo_principal.serial_motor or ''))
        p.drawString(430, y_vehiculo-90, str(vehiculo_principal.serial_carroceria or ''))
        p.drawString(430, y_vehiculo-105, str(vehiculo_principal.serial_niv or ''))
        p.drawString(430, y_vehiculo-120, str(vehiculo_principal.serie_version or ''))

    # --- PIE DE PÁGINA (TOTALES) ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(300, 150, "BASE IMPONIBLE GRAVABLE")
    p.drawString(500, 150, f"{factura.base_imponible:,.2f}")
    
    p.drawString(300, 130, "I.V.A. (16%)")
    p.drawString(500, 130, f"{factura.impuesto_iva:,.2f}")
    
    p.drawString(300, 110, "EXENTO (E)")
    p.drawString(500, 110, f"{factura.monto_exento:,.2f}")
    
    p.drawString(300, 90, "TOTAL GENERAL")
    p.drawString(500, 90, f"{factura.total:,.2f}")

    p.showPage()
    p.save()

    return response

def dashboard(request):
    # Últimas 5 facturas
    facturas_recientes = Factura.objects.select_related('cotizacion__cliente').order_by('-fecha_emision')[:5]
    
    # Conteo de cotizaciones activas
    cotizaciones_activas = Cotizacion.objects.exclude(estado__in=['F', 'A']).count()
    
    # NUEVO: Obtenemos las cotizaciones reales que están esperando ser facturadas
    cotizaciones_pendientes = Cotizacion.objects.exclude(estado__in=['F', 'A']).order_by('-fecha_creacion')
    
    context = {
        'facturas': facturas_recientes,
        'cotizaciones_activas': cotizaciones_activas,
        'cotizaciones_pendientes': cotizaciones_pendientes, # <-- Se lo enviamos al HTML
    }
    return render(request, 'facturacion/dashboard.html', context)

def crear_cotizacion(request):
    # Obtenemos todos los vehículos para el "select" del frontend
    vehiculos_disponibles = Vehiculo.objects.all()

    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        
        if form.is_valid():
            # Con 'transaction.atomic' aseguramos que si un ítem falla, no se guarde la cotización vacía
            with transaction.atomic():
                # 1. Guardamos la cabecera (La Cotización)
                cotizacion = form.save()
                
                # 2. Extraemos las listas de datos que envió el JavaScript
                vehiculos_ids = request.POST.getlist('item_vehiculo[]')
                descripciones = request.POST.getlist('item_descripcion[]')
                cantidades = request.POST.getlist('item_cantidad[]')
                precios = request.POST.getlist('item_precio[]')
                ivas = request.POST.getlist('item_iva[]')
                
                # 3. Iteramos según la cantidad de descripciones recibidas
                for i in range(len(descripciones)):
                    
                    # Verificamos si se seleccionó un vehículo (si no, es None)
                    vehiculo_id = vehiculos_ids[i] if vehiculos_ids[i] else None
                    if vehiculo_id:
                        vehiculo_obj = Vehiculo.objects.get(id=vehiculo_id)
                    else:
                        vehiculo_obj = None
                        
                    # Determinamos el estado del IVA
                    aplica_iva = True if ivas[i] == 'on' else False
                    
                    # Creamos el registro del Ítem en la base de datos
                    ItemCotizacion.objects.create(
                        cotizacion=cotizacion,
                        vehiculo=vehiculo_obj,
                        descripcion=descripciones[i],
                        cantidad=int(cantidades[i]),
                        precio_unitario=precios[i], # Django convierte automáticamente el texto a Decimal
                        aplica_iva=aplica_iva
                    )
                
                # Gracias a las "Señales (Signals)" que configuramos antes, 
                # la cotización ya se recalculó matemáticamente sola.
                
            return redirect('dashboard')
            
    else:
        form = CotizacionForm()
    
    context = {
        'form': form,
        'vehiculos_disponibles': vehiculos_disponibles, # <-- Enviamos los vehículos al HTML
    }
    return render(request, 'facturacion/crear_cotizacion.html', context)

def generar_factura(request, cotizacion_id):
    # Buscamos la cotización que queremos facturar
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Si la cotización ya tiene una factura asignada, evitamos que se duplique
    if hasattr(cotizacion, 'factura'):
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = FacturaForm(request.POST)
        if form.is_valid():
            factura = form.save(commit=False)
            factura.cotizacion = cotizacion
            # Recuerda que en nuestro models.py programamos el save() para que copie 
            # los totales de la cotización automáticamente y cambie el estado a 'F'.
            factura.save()
            return redirect('imprimir_factura', factura_id=factura.id)
    else:
        # Ponemos la fecha de hoy por defecto
        form = FacturaForm(initial={'fecha_emision': timezone.now().date()})
        
    context = {
        'form': form,
        'cotizacion': cotizacion
    }
    return render(request, 'facturacion/generar_factura.html', context)