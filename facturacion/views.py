import openpyxl
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib import messages 
from django.db.models import Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.db.models import Sum, Prefetch
from .models import Factura, Cotizacion, Vehiculo, ItemCotizacion, Cliente 
from .forms import CotizacionForm, FacturaForm, VehiculoForm, ClienteForm
from decimal import Decimal

# --- IMPORTACIÓN DE SEGURIDAD ---
from django.contrib.auth.decorators import login_required

@login_required
def imprimir_factura_institucional(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_Institucional_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    
    # --- ENCABEZADO DERECHA ---
    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, 620, "FACTURA N°:")
    p.drawString(400, 600, "FECHA DE EMISIÓN:")
    
    p.setFont("Helvetica", 9)
    p.drawRightString(550, 620, str(factura.numero_factura))
    p.drawRightString(550, 600, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    # --- DATOS DEL CLIENTE ---
    p.setFont("Helvetica-Bold", 8)
    p.drawString(40, 540, "NOMBRE(S) Y APELLIDO (S) O RAZÓN SOCIAL:")
    p.drawString(40, 495, "C.I./R.I.F:")
    p.drawString(40, 475, "DIRECCIÓN:")
    p.drawString(40, 455, "TELÉFONO")
    
    p.setFont("Helvetica", 8)
    p.drawString(250, 540, str(cliente.nombre_razon_social))
    p.drawString(150, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(150, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(150, 455, str(cliente.telefono or ''))
    
    # --- TABLA DETALLADA ---
    y_line1 = 435
    p.setLineWidth(1.5)
    p.line(40, y_line1, 560, y_line1)
    
    p.setFont("Helvetica-Bold", 6.5)
    p.drawString(42, y_line1 - 12, "N°")
    p.drawString(57, y_line1 - 12, "CANT")
    p.drawString(85, y_line1 - 12, "COD.SAP")
    p.drawString(125, y_line1 - 12, "MARCA / MOD")
    p.drawString(185, y_line1 - 12, "PLACA")
    p.drawString(220, y_line1 - 12, "AÑO")
    p.drawString(245, y_line1 - 12, "COLOR")
    p.drawString(280, y_line1 - 12, "SERIAL MOTOR")
    p.drawString(365, y_line1 - 12, "SERIAL NIV / CARROCERIA")
    p.drawString(470, y_line1 - 12, "TRANS")
    p.drawRightString(555, y_line1 - 12, "PREC.Bs.")
    
    y_line2 = y_line1 - 18
    p.line(40, y_line2, 560, y_line2)
    
    y_items = y_line2 - 12
    p.setFont("Helvetica", 6.5)
    
    for index, item in enumerate(cotizacion.items.all(), start=1):
        v = item.vehiculo
        subtotal_item = item.cantidad * item.precio_unitario
        p.drawString(44, y_items, str(index))
        p.drawString(62, y_items, str(item.cantidad))
        p.drawString(85, y_items, "1124626")
        p.drawString(125, y_items, f"{v.marca if v else ''} {v.modelo if v else item.descripcion[:10]}"[:15])
        p.drawString(185, y_items, str(v.placa if v else 'S/P'))
        p.drawString(220, y_items, str(v.anio if v else '2026'))
        p.drawString(245, y_items, str(v.color if v else ''))
        p.drawString(280, y_items, str(v.serial_motor if v else ''))
        p.drawString(365, y_items, str(v.serial_carroceria_niv if v else ''))
        p.drawString(470, y_items, str(v.transmision if v else 'MANUAL')[:7])
        p.drawRightString(555, y_items, f"{subtotal_item:,.2f}")
        y_items -= 15

    p.setLineWidth(1)
    p.line(40, y_items + 4, 560, y_items + 4)
    
    # --- NOTAS LEGALES ---
    y_notas = y_items - 20
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(40, y_notas, "NOTA 1: El precio referencial del vehículo se corresponde con el convenio institucional.")
    p.drawString(40, y_notas - 10, "Es importante resaltar que para el momento del pago se tomará en cuenta la tasa oficial.")
    p.drawString(40, y_notas - 25, f"NOTA 2: Esta factura corresponde al respaldo administrativo de la cotización VP-{cotizacion.id}.")

    # --- PIE DE PÁGINA (TOTALES Y COLETILLAS) ---
    y_totales_start = y_notas - 40
    p.setLineWidth(1)
    p.line(320, y_totales_start + 15, 560, y_totales_start + 15)
    
    y_tot = y_totales_start
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7)
        p.drawString(40, y_tot, "Condiciones Adicionales:")
        p.setFont("Helvetica", 6.5)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(40, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    p.drawString(330, y_tot, "Base Imponible Bs.:")
    p.drawRightString(550, y_tot, f"{factura.base_imponible:,.2f}")
    y_tot -= 14
    p.drawString(330, y_tot, "Exento Bs.:")
    p.drawRightString(550, y_tot, f"{factura.monto_exento:,.2f}")
    y_tot -= 14
    p.drawString(330, y_tot, "Iva (16%) Bs.:")
    p.drawRightString(550, y_tot, f"{factura.impuesto_iva:,.2f}")
    p.line(320, y_tot - 4, 560, y_tot - 4)
    y_tot -= 14
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(330, y_tot, "TOTAL GENERAL Bs.:")
    p.drawRightString(550, y_tot, f"{factura.total:,.2f}")

    p.showPage()
    p.save()
    return response

@login_required
def imprimir_factura_institucional_sin_sap(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_Inst_Sin_SAP_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    
    # --- ENCABEZADO DERECHA (Bajado 1 cm) ---
    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, 590, "FACTURA N°:")
    p.drawString(400, 570, "FECHA DE EMISIÓN:")
    
    p.setFont("Helvetica", 9)
    p.drawRightString(550, 590, str(factura.numero_factura))
    p.drawRightString(550, 570, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    # --- DATOS DEL CLIENTE ---
    p.setFont("Helvetica-Bold", 8)
    p.drawString(40, 540, "NOMBRE(S) Y APELLIDO (S) O RAZÓN SOCIAL:")
    p.drawString(40, 495, "C.I./R.I.F:")
    p.drawString(40, 475, "DIRECCIÓN:")
    p.drawString(40, 455, "TELÉFONO")
    
    p.setFont("Helvetica", 8)
    p.drawString(250, 540, str(cliente.nombre_razon_social))
    p.drawString(150, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(150, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(150, 455, str(cliente.telefono or ''))
    
    # --- TABLA SIN CÓDIGO SAP ---
    y_line1 = 435
    p.setLineWidth(1.5)
    p.line(40, y_line1, 560, y_line1)
    
    p.setFont("Helvetica-Bold", 7)
    p.drawString(42, y_line1 - 12, "N°")
    p.drawString(60, y_line1 - 12, "CANT")
    p.drawString(110, y_line1 - 12, "MARCA / MOD")
    p.drawString(185, y_line1 - 12, "PLACA")
    p.drawString(230, y_line1 - 12, "AÑO")
    p.drawString(260, y_line1 - 12, "COLOR")
    p.drawString(300, y_line1 - 12, "SERIAL MOTOR")
    p.drawString(400, y_line1 - 12, "SERIAL NIV / CARROCERIA")
    p.drawString(500, y_line1 - 12, "PREC.Bs.")
    
    y_line2 = y_line1 - 18
    p.line(40, y_line2, 560, y_line2)
    
    y_items = y_line2 - 12
    p.setFont("Helvetica", 6.5)
    
    for index, item in enumerate(cotizacion.items.all(), start=1):
        v = item.vehiculo
        subtotal_item = item.cantidad * item.precio_unitario
        p.drawString(44, y_items, str(index))
        p.drawString(65, y_items, str(item.cantidad))
        p.drawString(110, y_items, f"{v.marca if v else ''} {v.modelo if v else item.descripcion[:10]}"[:20])
        p.drawString(185, y_items, str(v.placa if v else 'S/P'))
        p.drawString(230, y_items, str(v.anio if v else '2026'))
        p.drawString(260, y_items, str(v.color if v else ''))
        p.drawString(300, y_items, str(v.serial_motor if v else ''))
        p.drawString(400, y_items, str(v.serial_carroceria_niv if v else ''))
        p.drawRightString(540, y_items, f"{subtotal_item:,.2f}")
        y_items -= 15

    p.setLineWidth(1)
    p.line(40, y_items + 4, 560, y_items + 4)
    
    # --- NOTAS LEGALES ---
    y_notas = y_items - 20
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(40, y_notas, "NOTA 1: El precio referencial del vehículo se corresponde con el convenio institucional.")
    p.drawString(40, y_notas - 10, "Es importante resaltar que para el momento del pago se tomará en cuenta la tasa oficial.")
    p.drawString(40, y_notas - 25, f"NOTA 2: Esta factura corresponde al respaldo administrativo de la cotización VP-{cotizacion.id}.")

    # --- PIE DE PÁGINA (TOTALES Y COLETILLAS) ---
    y_totales_start = y_notas - 40
    p.setLineWidth(1)
    p.line(320, y_totales_start + 15, 560, y_totales_start + 15)
    
    y_tot = y_totales_start
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7)
        p.drawString(40, y_tot, "Condiciones Adicionales:")
        p.setFont("Helvetica", 6.5)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(40, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    p.drawString(330, y_tot, "Base Imponible Bs.:")
    p.drawRightString(550, y_tot, f"{factura.base_imponible:,.2f}")
    y_tot -= 14
    p.drawString(330, y_tot, "Exento Bs.:")
    p.drawRightString(550, y_tot, f"{factura.monto_exento:,.2f}")
    y_tot -= 14
    p.drawString(330, y_tot, "Iva (16%) Bs.:")
    p.drawRightString(550, y_tot, f"{factura.impuesto_iva:,.2f}")
    p.line(320, y_tot - 4, 560, y_tot - 4)
    y_tot -= 14
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(330, y_tot, "TOTAL GENERAL Bs.:")
    p.drawRightString(550, y_tot, f"{factura.total:,.2f}")

    p.showPage()
    p.save()
    return response

@login_required
def imprimir_factura_forma_libre(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(400, 620, "FACTURA N°:")
    p.drawString(400, 600, "FECHA DE EMISIÓN:")
    p.setFont("Helvetica", 9)
    p.drawRightString(550, 620, str(factura.numero_factura))
    p.drawRightString(550, 600, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(40, 540, "NOMBRE(S) Y APELLIDO (S) O RAZÓN SOCIAL:")
    p.drawString(40, 495, "C.I./R.I.F:")
    p.drawString(40, 475, "DIRECCIÓN:")
    p.drawString(40, 455, "TELÉFONO")
    p.setFont("Helvetica", 8)
    p.drawString(250, 540, str(cliente.nombre_razon_social))
    p.drawString(150, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(150, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(150, 455, str(cliente.telefono or ''))
    
    y_line1 = 435
    p.setLineWidth(1.5)
    p.line(40, y_line1, 560, y_line1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(55, y_line1 - 12, "CANTIDAD")
    p.drawString(130, y_line1 - 12, "DESCRIPCION")
    p.drawString(280, y_line1 - 12, "TIPO DE IVA")
    p.drawString(390, y_line1 - 12, "ALIC.%")
    p.drawRightString(550, y_line1 - 12, "PREC.Bs.")
    y_line2 = y_line1 - 18
    p.line(40, y_line2, 560, y_line2)
    
    y_items = y_line2 - 14
    p.setFont("Helvetica", 8)
    vehiculo_principal = None
    for item in cotizacion.items.all():
        if item.vehiculo and not vehiculo_principal:
            vehiculo_principal = item.vehiculo
        tipo_iva = "ALIC. GENER." if item.aplica_iva else "EXENTO"
        alic_porcentaje = "16,00%" if item.aplica_iva else "0.00%"
        subtotal_item = item.cantidad * item.precio_unitario
        p.drawString(75, y_items, str(item.cantidad))
        p.drawString(130, y_items, item.descripcion[:35])
        p.drawString(280, y_items, tipo_iva)
        p.drawString(390, y_items, alic_porcentaje)
        p.drawRightString(550, y_items, f"{subtotal_item:,.2f}")
        y_items -= 16

    p.setLineWidth(1)
    p.line(40, y_items + 4, 560, y_items + 4)
    
    y_veh = y_items - 12
    if vehiculo_principal:
        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, y_veh, "DESCRIPCIÓN DEL VEHÍCULO")
        y_veh -= 14
        
        # Estructura de dos columnas completa y alineada
        left_labels = [
            ("MARCA:", vehiculo_principal.marca),
            ("MODELO:", vehiculo_principal.modelo),
            ("COLOR:", vehiculo_principal.color),
            ("PLACA:", vehiculo_principal.placa or 'S/P'),
            ("AÑO:", vehiculo_principal.anio),
            ("CLASE:", vehiculo_principal.clase),
            ("TIPO:", vehiculo_principal.tipo),
            ("USO:", vehiculo_principal.uso),
            ("TRANSMISIÓN:", vehiculo_principal.transmision)
        ]
        right_labels = [
            ("TIPO DE COMBUSTIBLE:", vehiculo_principal.tipo_combustible),
            ("N° DE PUESTO:", vehiculo_principal.num_puestos),
            ("N° EJES:", vehiculo_principal.num_ejes),
            ("PESO (TARA):", vehiculo_principal.peso_tara),
            ("CAPACIDAD DE CARGA (KG.):", vehiculo_principal.capacidad_carga),
            ("SERIAL DE MOTOR:", vehiculo_principal.serial_motor),
            ("SERIAL DE CARROCERIA:", vehiculo_principal.serial_carroceria_niv),
            ("SERIAL NIV:", vehiculo_principal.serial_carroceria_niv)
        ]
        
        y_curr = y_veh
        for label, val in left_labels:
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(40, y_curr, label)
            p.setFont("Helvetica", 7.5)
            p.drawString(150, y_curr, str(val or ''))
            y_curr -= 11
            
        y_curr_r = y_veh
        for label, val in right_labels:
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(300, y_curr_r, label)
            p.setFont("Helvetica", 7.5)
            p.drawString(430, y_curr_r, str(val or ''))
            y_curr_r -= 11
            
        y_totales_start = min(y_curr, y_curr_r) - 15
    else:
        y_totales_start = y_veh - 10

    # --- PIE DE PÁGINA (TOTALES Y COLETILLAS) ---
    p.setLineWidth(1)
    p.line(40, y_totales_start + 15, 560, y_totales_start + 15)
    y_tot = y_totales_start
    
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7.5)
        p.drawString(40, y_tot, "Condiciones y Coletillas:")
        p.setFont("Helvetica", 7)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(40, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    p.drawRightString(440, y_tot, "BASE IMPONIBLE GRAVABLE")
    p.drawRightString(550, y_tot, f"{factura.base_imponible:,.2f}")
    y_tot -= 14
    p.drawRightString(440, y_tot, "I.V.A. (16%)")
    p.drawRightString(550, y_tot, f"{factura.impuesto_iva:,.2f}")
    y_tot -= 14
    p.drawRightString(440, y_tot, "EXENTO (E)")
    p.drawRightString(550, y_tot, f"{factura.monto_exento:,.2f}")
    p.line(320, y_tot - 4, 560, y_tot - 4)
    y_tot -= 14
    p.setFont("Helvetica-Bold", 9)
    p.drawRightString(440, y_tot, "TOTAL GENERAL")
    p.drawRightString(550, y_tot, f"{factura.total:,.2f}")

    p.showPage()
    p.save()
    return response
@login_required
def dashboard(request):
    facturas_recientes = Factura.objects.select_related('cotizacion__cliente').order_by('-fecha_emision')[:5]
    cotizaciones_activas = Cotizacion.objects.exclude(estado__in=['F', 'A']).count()
    cotizaciones_pendientes = Cotizacion.objects.exclude(estado__in=['F', 'A']).order_by('-fecha_creacion')
    
    context = {
        'facturas': facturas_recientes,
        'cotizaciones_activas': cotizaciones_activas,
        'cotizaciones_pendientes': cotizaciones_pendientes,
    }
    return render(request, 'facturacion/dashboard.html', context)

@login_required
def crear_cotizacion(request):
    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        if form.is_valid():
            cotizacion = form.save(commit=False)
            cotizacion.usuario = request.user
            cotizacion.save()
            
            descriptions = request.POST.getlist('item_descripcion[]')
            cantidades = request.POST.getlist('item_cantidad[]')
            precios = request.POST.getlist('item_precio[]')
            vehiculos = request.POST.getlist('item_vehiculo[]')
            
            base_imponible = 0
            
            for i in range(len(descriptions)):
                if not descriptions[i].strip():
                    continue 
                
                desc = descriptions[i]
                cant = int(cantidades[i]) if cantidades[i] else 1
                precio = float(precios[i]) if precios[i] else 0.0
                
                vehiculo_id = vehiculos[i] if i < len(vehiculos) and vehiculos[i] else None
                vehiculo = Vehiculo.objects.filter(id=vehiculo_id).first() if vehiculo_id else None
                
                subtotal_linea = cant * precio
                base_imponible += subtotal_linea
                
                ItemCotizacion.objects.create(
                    cotizacion=cotizacion,
                    vehiculo=vehiculo,
                    descripcion=desc,
                    cantidad=cant,
                    precio_unitario=precio
                )
            
            impuesto_iva = base_imponible * 0.16
            total_general = base_imponible + impuesto_iva
            
            cotizacion.base_imponible = base_imponible
            cotizacion.impuesto_iva = impuesto_iva
            cotizacion.total = total_general
            cotizacion.save()
            
            messages.success(request, f'¡Cotización VP-{cotizacion.id} guardada con éxito!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Por favor verifique los datos generales de la cotización.')
    else:
        form = CotizacionForm()
        
    vehiculos_disponibles = Vehiculo.objects.all()
    return render(request, 'facturacion/crear_cotizacion.html', {
        'form': form,
        'vehiculos_disponibles': vehiculos_disponibles
    })

@login_required
def eliminar_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Validación de seguridad: Si ya está facturada y activa, no se borra
    factura_previa = getattr(cotizacion, 'factura', None)
    if cotizacion.estado == 'F' and factura_previa and factura_previa.estado_pago != 'ANULADA':
        messages.error(request, f'No se puede eliminar la cotización VP-{cotizacion.id} porque tiene una factura activa asociada.')
        return redirect('lista_cotizaciones')
        
    with transaction.atomic():
        # Devolver los vehículos asociados a estado 'Disponible' si estaban apartados
        for item in cotizacion.items.all():
            if item.vehiculo and item.vehiculo.estado == 'Apartado':
                item.vehiculo.estado = 'Disponible'
                item.vehiculo.save()
                
        # Eliminar la cotización (los ítems se borran en cascada)
        cotizacion_id_str = cotizacion.id
        cotizacion.delete()
        
    messages.success(request, f'¡Cotización VP-{cotizacion_id_str} eliminada con éxito y vehículos liberados!')
    return redirect('lista_cotizaciones')

@login_required
def generar_factura(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    # Verificamos si existe una factura vinculada previamente
    factura_previa = getattr(cotizacion, 'factura', None)
    
    # Permitimos avanzar SOLO si no está facturada, o si la factura que tiene está ANULADA
    if cotizacion.estado == 'F' and (not factura_previa or factura_previa.estado_pago != 'ANULADA'):
        messages.warning(request, 'Esta cotización ya ha sido facturada previamente y está activa.')
        return redirect('dashboard')
        
    vehiculos_disponibles = Vehiculo.objects.filter(
        Q(estado='Disponible') | 
        Q(id__in=cotizacion.items.filter(vehiculo__isnull=False).values_list('vehiculo_id', flat=True))
    )

    if request.method == 'POST':
        # Si la estamos re-facturando sobre una anulada, usamos "instance" para reciclar el registro
        if factura_previa and factura_previa.estado_pago == 'ANULADA':
            form = FacturaForm(request.POST, instance=factura_previa)
        else:
            form = FacturaForm(request.POST)
            
        if form.is_valid():
            with transaction.atomic():
                for item in cotizacion.items.all():
                    if item.vehiculo:
                        item.vehiculo.estado = 'Disponible'
                        item.vehiculo.save()
                
                cotizacion.items.all().delete()
                
                vehiculos_ids = request.POST.getlist('item_vehiculo[]')
                descripciones = request.POST.getlist('item_descripcion[]')
                cantidades = request.POST.getlist('item_cantidad[]')
                precios = request.POST.getlist('item_precio[]')
                ivas = request.POST.getlist('item_iva[]')
                
                tasa_cambio_str = request.POST.get('tasa_cambio', '1.00')
                tasa_cambio = Decimal(tasa_cambio_str) if tasa_cambio_str else Decimal('1.00')
                
                base_imponible_usd = Decimal('0.00')
                monto_exento_usd = Decimal('0.00')
                
                for i in range(len(descripciones)):
                    vehiculo_id = vehiculos_ids[i] if vehiculos_ids[i] else None
                    vehiculo_obj = Vehiculo.objects.filter(id=vehiculo_id).first() if vehiculo_id else None
                        
                    aplica_iva = True if ivas[i] == 'on' else False
                    cant = int(cantidades[i])
                    precio_usd = Decimal(precios[i])
                    
                    if aplica_iva:
                        base_imponible_usd += (cant * precio_usd)
                    else:
                        monto_exento_usd += (cant * precio_usd)
                    
                    if vehiculo_obj:
                        vehiculo_obj.estado = 'Vendido'
                        vehiculo_obj.save()
                    
                    ItemCotizacion.objects.create(
                        cotizacion=cotizacion,
                        vehiculo=vehiculo_obj,
                        descripcion=descripciones[i],
                        cantidad=cant,
                        precio_unitario=precio_usd, 
                        aplica_iva=aplica_iva
                    )
                
                cotizacion.refresh_from_db()

                factura = form.save(commit=False)
                factura.cotizacion = cotizacion
                factura.usuario = request.user
                
                factura.base_imponible = base_imponible_usd * tasa_cambio
                factura.monto_exento = monto_exento_usd * tasa_cambio
                factura.impuesto_iva = factura.base_imponible * Decimal('0.16')
                factura.total = factura.base_imponible + factura.monto_exento + factura.impuesto_iva
                
                # Al re-facturar, nos aseguramos de que el estado vuelva a Pendiente de Pago
                factura.estado_pago = 'PENDIENTE' 
                factura.porcentaje_pago = 0
                factura.save()
                
                cotizacion.estado = 'F'
                cotizacion.save()
                
            messages.success(request, f'¡Factura N° {factura.numero_factura} emitida y vehículos rebajados del inventario!')
            return redirect('imprimir_factura', factura_id=factura.id)
    else:
        form = FacturaForm(initial={'fecha_emision': timezone.now().date()})
        
    context = {
        'form': form,
        'cotizacion': cotizacion,
        'vehiculos_disponibles': vehiculos_disponibles,
    }
    return render(request, 'facturacion/generar_factura.html', context)

@login_required
def exportar_inventario_excel(request):
    # 1. Creamos un libro de Excel en blanco
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario Vehículos"

    # 2. Definimos las 26 cabeceras EXACTAS que pide tu formato
    cabeceras = [
        'N°', 'MARCA', 'MODELO', 'COLOR', 'PLACA', 'AÑO', 'CLASE', 'TIPO', 
        'USO', 'TRANSMISION', 'TIPO DE COMBUSTIBLE', 'N° DE PUESTOS', 'N° DE EJES', 
        'PESO (TARA)', 'CAPACIDAD DE CARGA (KG)', 'SERIAL MOTOR', 'SERIAL CARROCERIA Y NIV', 
        'CERTIFICADO DE ORIGEN', 'SERVICIO', 'PUERTO DE ENTRADA', 'FECHA DE LIQUIDACIÓN', 
        'PLANILLA DE LIQUIDACIÓN', 'FECHA DE FACTURACIÓN', 'FACTURA DE ADQUISIÓN', 
        'REFECIV', 'FECHA FIN DEL CONVENIO'
    ]
    
    # Agregamos las cabeceras a la primera fila
    ws.append(cabeceras)

    # 3. Traemos todos los vehículos de la base de datos
    vehiculos = Vehiculo.objects.all().order_by('id')

    # 4. Llenamos las filas una por una
    for contador, v in enumerate(vehiculos, start=1):
        fila = [
            contador,  # N° autogenerado
            v.marca,
            v.modelo,
            v.color,
            v.placa,
            v.anio,
            v.clase,
            v.tipo,
            v.uso,
            v.transmision,
            v.tipo_combustible,
            v.num_puestos,
            v.num_ejes,
            v.peso_tara,
            v.capacidad_carga,
            v.serial_motor,
            v.serial_carroceria_niv,
            v.certificado_origen,
            v.servicio,
            v.puerto_entrada,
            # Formateamos las fechas a texto si existen para evitar conflictos en Excel
            v.fecha_liquidacion.strftime('%Y-%m-%d') if v.fecha_liquidacion else '',
            v.planilla_liquidacion,
            v.fecha_facturacion.strftime('%Y-%m-%d') if v.fecha_facturacion else '',
            v.factura_adquisicion,
            v.refeciv,
            v.fecha_fin_convenio.strftime('%Y-%m-%d') if v.fecha_fin_convenio else ''
        ]
        ws.append(fila)

    # 5. Preparamos la respuesta para que el navegador descargue el archivo
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=inventario_vehiculos_emvepro.xlsx'
    
    # Guardamos el Excel en la respuesta
    wb.save(response)
    
    return response

@login_required
def importar_inventario_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('archivo_excel')
        if not excel_file:
            messages.error(request, 'Por favor seleccione un archivo Excel válido.')
            return redirect('importar_inventario')

        try:
            wb = openpyxl.load_workbook(excel_file)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            
            count = 0
            importados = 0
            actualizados = 0
            
            for row in rows[1:]:
                if not row or not row[0]:
                    continue
                
                niv = str(row[5] if len(row) > 5 and row[5] else '').strip()
                
                datos_vehiculo = {
                    'marca': row[0] or '',
                    'modelo': row[1] or '',
                    'anio': int(row[2]) if row[2] else 2026,
                    'color': row[3] or '',
                    'placa': row[4] or '',
                    'serial_motor': row[6] if len(row) > 6 else '',
                    'tipo_combustible': row[7] if len(row) > 7 else '',
                    'transmision': row[8] if len(row) > 8 else '',
                    'clase': row[9] if len(row) > 9 else '',
                    'tipo': row[10] if len(row) > 10 else '',
                    'uso': row[11] if len(row) > 11 else '',
                    'peso_tara': float(row[12]) if len(row) > 12 and row[12] else 0.0,
                    'capacidad_carga': float(row[13]) if len(row) > 13 and row[13] else 0.0,
                    'certificado_origen': str(row[14]) if len(row) > 14 and row[14] else ''
                }
                
                if niv:
                    vehiculo, created = Vehiculo.objects.update_or_create(
                        serial_carroceria_niv=niv,
                        defaults=datos_vehiculo
                    )
                    if created:
                        importados += 1
                    else:
                        actualizados += 1
                else:
                    Vehiculo.objects.create(**datos_vehiculo, serial_carroceria_niv='')
                    importados += 1
                
                count += 1
                
            messages.success(request, f'¡Carga masiva completada! {importados} nuevos, {actualizados} actualizados por NIV.')
            return redirect('lista_vehiculos')
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {e}')
            return redirect('importar_inventario')
            
    return render(request, 'facturacion/importar_inventario.html')

@login_required
def lista_clientes(request):
    # Precargamos las cotizaciones y sus facturas asociadas para un rendimiento óptimo
    clientes = Cliente.objects.prefetch_related(
        Prefetch('cotizaciones', queryset=Cotizacion.objects.prefetch_related('factura', 'items__vehiculo'))
    ).order_by('-id')
    
    context = {
        'clientes': clientes,
    }
    return render(request, 'facturacion/lista_clientes.html', context)

@login_required
def lista_vehiculos(request):
    query = request.GET.get('q')
    vehiculos = Vehiculo.objects.all()
    if query:
        vehiculos = vehiculos.filter(
            Q(marca__icontains=query) |
            Q(modelo__icontains=query) |
            Q(placa__icontains=query) |
            Q(serial_carroceria_niv__icontains=query)
        )
    vehiculos = vehiculos.order_by('-anio', 'marca')
    return render(request, 'facturacion/lista_vehiculos.html', {'vehiculos': vehiculos})

@login_required
def crear_vehiculo(request):
    if request.method == 'POST':
        form = VehiculoForm(request.POST)
        if form.is_valid():
            vehiculo = form.save()
            messages.success(request, f'¡Vehículo {vehiculo.marca} {vehiculo.modelo} registrado con éxito!')
            return redirect('lista_vehiculos')
        else:
            messages.error(request, 'Ocurrió un error al guardar. Revisa los campos.')
    else:
        form = VehiculoForm()
        
    return render(request, 'facturacion/crear_vehiculo.html', {'form': form})

@login_required
def editar_vehiculo(request, vehiculo_id):
    vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)
    if request.method == 'POST':
        form = VehiculoForm(request.POST, instance=vehiculo)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Vehículo {vehiculo.marca} {vehiculo.modelo} actualizado con éxito!')
            return redirect('lista_vehiculos')
        else:
            messages.error(request, 'Ocurrió un error al actualizar. Revisa los campos.')
    else:
        form = VehiculoForm(instance=vehiculo)
        
    return render(request, 'facturacion/crear_vehiculo.html', {'form': form, 'editando': True})

@login_required
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f'¡Cliente {cliente.nombre_razon_social} registrado con éxito!')
            return redirect('lista_clientes')
        else:
            messages.error(request, 'Ocurrió un error al guardar el cliente. Revisa los campos.')
    else:
        form = ClienteForm()
        
    return render(request, 'facturacion/crear_cliente.html', {'form': form})

@login_required
def imprimir_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Presupuesto_VP-{cotizacion.id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    
    # --- COLORES INSTITUCIONALES ---
    COLOR_AZUL_MARINO = colors.HexColor('#273376')
    COLOR_AMARILLO_ORO = colors.HexColor('#FFC907')
    COLOR_ROJO_CARMESI = colors.HexColor('#A70336')
    COLOR_GRIS_OSCURO = colors.HexColor('#333333')

    # --- ENCABEZADO INSTITUCIONAL (CO-BRANDING / 3 BLOQUES SUPERIORES) ---
    p.setStrokeColor(colors.HexColor('#CCCCCC'))
    p.setFillColor(colors.HexColor('#F8F9FA'))
    p.rect(50, 735, 130, 35, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 6)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawCentredString(115, 750, "MINISTERIO DEL PODER POPULAR")

    p.rect(190, 735, 180, 35, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(280, 750, "EMPRESA VENEZUELA PRODUCTIVA, C.A.")

    p.rect(380, 735, 170, 35, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(465, 752, "EMVEPRO AUTOMOTRIZ")
    p.setFont("Helvetica", 6)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawCentredString(465, 742, "RIF: G-20010522-4")

    # Fecha segura
    fecha_str = cotizacion.fecha_creacion.strftime('%d/%m/%Y') if cotizacion.fecha_creacion else 'N/A'
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(550, 715, f"Fecha de Emisión: {fecha_str}")

    # --- TÍTULO Y DATOS DEL DOCUMENTO ---
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(50, 685, f"PRESUPUESTO / COTIZACIÓN N°: VP-{cotizacion.id}")

    # --- DATOS DEL CLIENTE ---
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 665, "DATOS DEL CLIENTE:")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(50, 650, f"Razón Social: {str(cliente.nombre_razon_social or '')}")
    p.drawString(50, 635, f"C.I. / R.I.F.: {str(cliente.tipo_documento or '')}-{str(cliente.identificacion or '')}")
    p.drawString(320, 650, f"Teléfono: {str(cliente.telefono or 'N/A')}")
    
    dir_cliente = str(cliente.direccion or 'N/A')
    p.drawString(320, 635, f"Dirección: {dir_cliente[:45]}")

    # --- TABLA DE ÍTEMS ---
    y_table = 605
    p.setFillColor(COLOR_AZUL_MARINO)
    p.rect(50, y_table, 510, 18, fill=1, stroke=0)
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(colors.white)
    p.drawString(55, y_table + 5, "ITEM")
    p.drawString(90, y_table + 5, "PRODUCTO / DESCRIPCIÓN")
    p.drawString(320, y_table + 5, "PRECIO UNIT. ($)")
    p.drawString(415, y_table + 5, "CANTIDAD")
    p.drawRightString(555, y_table + 5, "SUBTOTAL ($)")

    y_items = y_table - 18
    p.setFont("Helvetica", 8.5)
    p.setFillColor(COLOR_GRIS_OSCURO)
    
    cantidad_total_items = 0
    for index, item in enumerate(cotizacion.items.all(), start=1):
        cant = item.cantidad or 0
        precio = item.precio_unitario or Decimal('0.00')
        subtotal_item = cant * precio
        cantidad_total_items += cant
        
        desc = str(item.descripcion or '')[:45]
        
        p.drawString(55, y_items, str(index))
        p.drawString(90, y_items, desc)
        p.drawString(320, y_items, f"{precio:,.2f}")
        p.drawString(430, y_items, str(cant))
        p.drawRightString(555, y_items, f"{subtotal_item:,.2f}")
        y_items -= 18

    # Línea de separación de totales
    p.setStrokeColor(colors.HexColor('#CCCCCC'))
    p.setLineWidth(1)
    p.line(320, y_items + 10, 560, y_items + 10)

    y_items -= 5
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "CANTIDAD TOTAL:")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(555, y_items, str(cantidad_total_items))
    
    y_items -= 15
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "BASE IMPONIBLE:")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(555, y_items, f"{cotizacion.base_imponible or 0:,.2f}")
    
    y_items -= 15
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "IVA (16%):")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(555, y_items, f"{cotizacion.impuesto_iva or 0:,.2f}")
    
    y_items -= 15
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "TOTAL GENERAL:")
    p.drawRightString(555, y_items, f"{cotizacion.total or 0:,.2f}")

    # --- CONDICIONES Y CONSIDERACIONES ---
    y_info = y_items - 30
    p.setFont("Helvetica-Bold", 7.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(50, y_info, "CONSIDERACIONES PARA LA VENTA:")
    p.setFont("Helvetica", 6.5)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(50, y_info - 10, "1. PRECIOS EXPRESADOS EN INCOTERM DAP (DELIVERY AT PLACE), incluye transporte y despacho hasta puerto destino.")
    p.drawString(50, y_info - 18, "2. PAGO INICIAL del 50% contra la cantidad de vehículos contenidos en cada Bill of Lading (BL).")
    p.drawString(50, y_info - 26, "3. PAGO DEL 50% RESTANTE según la cantidad parcial entregada en cada BL contra DAP.")
    p.drawString(50, y_info - 34, "4. GARANTÍA LIMITADA de un (1) año o 50.000 KM. Gestión ante División Vehicular Emvepro: (0412-6198651).")

    # --- FIRMAS ---
    y_firmas = y_info - 85
    p.setFont("Helvetica-Bold", 7)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(80, y_firmas, "REVISADO POR:")
    p.drawString(360, y_firmas, "AUTORIZADO POR:")
    
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(70, y_firmas - 25, "Mercedes Varela")
    p.drawString(340, y_firmas - 25, "Jose Holberg Zambrano Gonzalez")
    p.setFont("Helvetica", 7)
    p.drawString(80, y_firmas - 33, "Gerente de Comercio")
    p.drawString(370, y_firmas - 33, "Presidente (E)")

    # --- PIE DE PÁGINA TRICOLOR INSTITUCIONAL ---
    p.setFillColor(COLOR_AZUL_MARINO)
    p.rect(0, 0, 612, 28, fill=1, stroke=0)
    p.setFillColor(COLOR_AMARILLO_ORO)
    p.rect(0, 0, 612, 10, fill=1, stroke=0)
    p.setFillColor(COLOR_ROJO_CARMESI)
    p.rect(0, 0, 612, 4, fill=1, stroke=0)

    p.setFont("Helvetica", 6)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(50, 42, "Teléfono: +58 212 802 8300 | Correo: contacto@emvepro.gob.ve")
    p.drawString(50, 34, "Final Av. Panteón, Diagonal al Panteón Nacional, Caracas, Distrito Capital - Venezuela.")

    p.showPage()
    p.save()
    return response
    
@login_required
def imprimir_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Presupuesto_VP-{cotizacion.id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    
    # --- COLORES INSTITUCIONALES ---
    COLOR_AZUL_MARINO = colors.HexColor('#273376')
    COLOR_AMARILLO_ORO = colors.HexColor('#FFC907')
    COLOR_ROJO_CARMESI = colors.HexColor('#A70336')
    COLOR_GRIS_OSCURO = colors.HexColor('#333333')

    # --- ENCABEZADO INSTITUCIONAL (CO-BRANDING / 3 BLOQUES SUPERIORES) ---
    # Bloque 1: Logo Ministerio / Órgano Rector
    p.setStrokeColor(colors.HexColor('#CCCCCC'))
    p.setFillColor(colors.HexColor('#F8F9FA'))
    p.rect(50, 735, 130, 35, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 6)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawCentredString(115, 750, "MINISTERIO DEL PODER POPULAR")

    # Bloque 2: Nombre del Ente
    p.rect(190, 735, 180, 35, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(280, 750, "EMPRESA VENEZUELA PRODUCTIVA, C.A.")

    # Bloque 3: Logo del Ente
    p.rect(380, 735, 170, 35, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(465, 752, "EMVEPRO AUTOMOTRIZ")
    p.setFont("Helvetica", 6)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawCentredString(465, 742, "RIF: G-20010522-4")

    # Fecha oficial alineada a la derecha
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(550, 715, f"Caracas, {cotizacion.fecha_creacion.strftime('%d de %B de %Y')}")

    # --- TÍTULO Y DATOS DEL DOCUMENTO ---
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(50, 685, f"PRESUPUESTO / COTIZACIÓN N°: VP-{cotizacion.id}")

    # --- DATOS DEL CLIENTE ---
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 665, "DATOS DEL CLIENTE:")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(50, 650, f"Razón Social: {cliente.nombre_razon_social}")
    p.drawString(50, 635, f"C.I. / R.I.F.: {cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(320, 650, f"Teléfono: {cliente.telefono or 'N/A'}")
    p.drawString(320, 635, f"Dirección: {cliente.direccion[:45] if cliente.direccion else 'N/A'}")

    # --- TABLA DE ÍTEMS ---
    y_table = 605
    p.setFillColor(COLOR_AZUL_MARINO)
    p.rect(50, y_table, 510, 18, fill=1, stroke=0)
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(colors.white)
    p.drawString(55, y_table + 5, "ITEM")
    p.drawString(90, y_table + 5, "PRODUCTO / DESCRIPCIÓN")
    p.drawString(320, y_table + 5, "PRECIO UNIT. ($)")
    p.drawString(415, y_table + 5, "CANTIDAD")
    p.drawRightString(555, y_table + 5, "SUBTOTAL ($)")

    y_items = y_table - 18
    p.setFont("Helvetica", 8.5)
    p.setFillColor(COLOR_GRIS_OSCURO)
    
    cantidad_total_items = 0
    for index, item in enumerate(cotizacion.items.all(), start=1):
        subtotal_item = item.cantidad * item.precio_unitario
        cantidad_total_items += item.cantidad
        
        p.drawString(55, y_items, str(index))
        p.drawString(90, y_items, item.descripcion[:45])
        p.drawString(320, y_items, f"{item.precio_unitario:,.2f}")
        p.drawString(430, y_items, str(item.cantidad))
        p.drawRightString(555, y_items, f"{subtotal_item:,.2f}")
        y_items -= 18

    # Línea de separación de totales
    p.setStrokeColor(colors.HexColor('#CCCCCC'))
    p.setLineWidth(1)
    p.line(320, y_items + 10, 560, y_items + 10)

    y_items -= 5
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "CANTIDAD TOTAL:")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(555, y_items, str(cantidad_total_items))
    
    y_items -= 15
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "BASE IMPONIBLE:")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(555, y_items, f"{cotizacion.base_imponible:,.2f}")
    
    y_items -= 15
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "IVA (16%):")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(555, y_items, f"{cotizacion.impuesto_iva:,.2f}")
    
    y_items -= 15
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(320, y_items, "TOTAL GENERAL:")
    p.drawRightString(555, y_items, f"{cotizacion.total:,.2f}")

    # --- CONDICIONES Y CONSIDERACIONES ---
    y_info = y_items - 30
    p.setFont("Helvetica-Bold", 7.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(50, y_info, "CONSIDERACIONES PARA LA VENTA:")
    p.setFont("Helvetica", 6.5)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(50, y_info - 10, "1. PRECIOS EXPRESADOS EN INCOTERM DAP (DELIVERY AT PLACE), incluye transporte y despacho hasta puerto destino.")
    p.drawString(50, y_info - 18, "2. PAGO INICIAL del 50% contra la cantidad de vehículos contenidos en cada Bill of Lading (BL).")
    p.drawString(50, y_info - 26, "3. PAGO DEL 50% RESTANTE según la cantidad parcial entregada en cada BL contra DAP.")
    p.drawString(50, y_info - 34, "4. GARANTÍA LIMITADA de un (1) año o 50.000 KM. Gestión ante División Vehicular Emvepro: (0412-6198651).")

    # --- FIRMAS ---
    y_firmas = y_info - 85
    p.setFont("Helvetica-Bold", 7)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(80, y_firmas, "REVISADO POR:")
    p.drawString(360, y_firmas, "AUTORIZADO POR:")
    
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(70, y_firmas - 25, "Mercedes Varela")
    p.drawString(340, y_firmas - 25, "Jose Holberg Zambrano Gonzalez")
    p.setFont("Helvetica", 7)
    p.drawString(80, y_firmas - 33, "Gerente de Comercio")
    p.drawString(370, y_firmas - 33, "Presidente (E)")

    # --- PIE DE PÁGINA TRICOLOR INSTITUCIONAL ---
    p.setFillColor(COLOR_AZUL_MARINO)
    p.rect(0, 0, 612, 28, fill=1, stroke=0)
    p.setFillColor(COLOR_AMARILLO_ORO)
    p.rect(0, 0, 612, 10, fill=1, stroke=0)
    p.setFillColor(COLOR_ROJO_CARMESI)
    p.rect(0, 0, 612, 4, fill=1, stroke=0)

    # Textos de contacto sobre el pie de página
    p.setFont("Helvetica", 6)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(50, 42, "Teléfono: +58 212 802 8300 | Correo: contacto@emvepro.gob.ve")
    p.drawString(50, 34, "Final Av. Panteón, Diagonal al Panteón Nacional, Caracas, Distrito Capital - Venezuela.")

    p.showPage()
    p.save()
    return response
    
def estado_financiero(request):
    # Consolidado general de facturas emitidas
    total_facturado = Factura.objects.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    total_base = Factura.objects.aggregate(Sum('base_imponible'))['base_imponible__sum'] or Decimal('0.00')
    total_iva = Factura.objects.aggregate(Sum('impuesto_iva'))['impuesto_iva__sum'] or Decimal('0.00')
    total_exento = Factura.objects.aggregate(Sum('monto_exento'))['monto_exento__sum'] or Decimal('0.00')
    
    # Listado detallado de facturas para la auditoría financiera
    facturas = Factura.objects.select_related('cotizacion__cliente').order_by('-fecha_emision')
    
    # Cotizaciones pendientes de cobro / facturación
    cotizaciones_pendientes = Cotizacion.objects.exclude(estado__in=['F', 'A'])
    monto_pendiente = cotizaciones_pendientes.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')

    context = {
        'total_facturado': total_facturado,
        'total_base': total_base,
        'total_iva': total_iva,
        'total_exento': total_exento,
        'monto_pendiente': monto_pendiente,
        'facturas': facturas,
        'cotizaciones_pendientes': cotizaciones_pendientes,
    }
    return render(request, 'facturacion/estado_financiero.html', context)

@login_required
def actualizar_pago_factura(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    if request.method == 'POST':
        estado = request.POST.get('estado_pago')
        porcentaje_str = request.POST.get('porcentaje_pago')
        
        if estado in dict(Factura.ESTADOS_PAGO).keys():
            factura.estado_pago = estado
            
            # Validación segura del porcentaje
            if porcentaje_str and str(porcentaje_str).strip():
                porcentaje = int(porcentaje_str)
            else:
                porcentaje = 0
                
            # =========================================================
            # LA ANULACIÓN TIENE PRIORIDAD ABSOLUTA
            # =========================================================
            if factura.estado_pago == 'ANULADA':
                factura.porcentaje_pago = 0
                
                # Llevar totales a cero para no sumar en Finanzas
                factura.base_imponible = Decimal('0.00')
                factura.impuesto_iva = Decimal('0.00')
                factura.monto_exento = Decimal('0.00')
                factura.total = Decimal('0.00')
                
                # Devolver vehículos a inventario (Disponible)
                for item in factura.cotizacion.items.all():
                    if item.vehiculo:
                        item.vehiculo.estado = 'Disponible'
                        item.vehiculo.save()
                
                # Pasar la cotización a Pendiente 
                cotizacion = factura.cotizacion
                cotizacion.estado = 'P' 
                cotizacion.save()
                
            else:
                # SI NO ES ANULACIÓN, ACTÚA LA LÓGICA AUTOMÁTICA
                factura.porcentaje_pago = porcentaje
                if factura.porcentaje_pago >= 100:
                    factura.estado_pago = 'PAGADA'
                    factura.porcentaje_pago = 100
                elif factura.porcentaje_pago == 0 and factura.estado_pago != 'PENDIENTE':
                    factura.estado_pago = 'PENDIENTE'
                
            factura.save()
            messages.success(request, f'Estatus de la factura {factura.numero_factura} actualizado con éxito.')
            
    # Redirección dinámica según dónde estés (Historial o Finanzas)
    referer = request.META.get('HTTP_REFERER')
    if referer and 'historial' in referer:
        return redirect('historial_facturas')
    return redirect('estado_financiero')

@login_required
def historial_facturas(request):
    query = request.GET.get('q')
    facturas = Factura.objects.select_related('cotizacion__cliente').all()
    
    if query:
        facturas = facturas.filter(
            Q(numero_factura__icontains=query) |
            Q(numero_control__icontains=query) |
            Q(cotizacion__cliente__nombre_razon_social__icontains=query) |
            Q(cotizacion__cliente__identificacion__icontains=query)
        )
        
    facturas = facturas.order_by('-fecha_emision', '-numero_factura')
    return render(request, 'facturacion/historial_facturas.html', {'facturas': facturas})

@login_required
def exportar_facturas_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="CONSOLIDADO_SERIE_A_FACTURACION.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Consolidado Serie A"

    # 1. Agregamos 'Emitido Por' al final de las cabeceras
    headers = [
        'Fecha Factura', 'Nro Factura', 'Nro Control', 'Estatus de Pago', 'Cliente', 
        'Cedula/Rif', 'Dirección', 'Telefonos', 'Descripción', 
        'Base Imponible', 'IVA 16%', 'EXENTO (E.)', 'Total General', 
        'Marca', 'Modelo', 'Color', 'Placa', 'Año', 'Clase', 'Tipo', 'Uso',
        'Serial Motor', 'Serial Carrocería NIV', 'Emitido Por'
    ]
    
    # Estilo básico para la cabecera
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")

    # 2. Agregamos 'usuario' a select_related para optimizar la consulta
    facturas = Factura.objects.select_related('cotizacion__cliente', 'usuario').prefetch_related('cotizacion__items__vehiculo').order_by('numero_factura')
    
    diccionario_estados = {
        'PENDIENTE': 'Por Pagar',
        'PARCIAL': 'Pago Parcial',
        'PAGADA': 'Pagada',
        'ANULADA': 'Anulada' # <--- Corrección a ANULADA
    }
    
    for f in facturas:
        cliente = f.cotizacion.cliente
        item = f.cotizacion.items.first()
        v = item.vehiculo if item else None
        
        estatus_texto = diccionario_estados.get(getattr(f, 'estado_pago', 'PENDIENTE'), 'Por Pagar')
        
        # 3. Extraemos el nombre del usuario, si existe
        nombre_usuario = f.usuario.username.title() if f.usuario else 'N/A'
        
        ws.append([
            f.fecha_emision.strftime('%d/%m/%Y'), f.numero_factura, getattr(f, 'numero_control', 'N/A'), estatus_texto, 
            cliente.nombre_razon_social, f"{cliente.tipo_documento}-{cliente.identificacion}", 
            cliente.direccion, cliente.telefono, item.descripcion if item else '',
            float(f.base_imponible), float(f.impuesto_iva), float(f.monto_exento), float(f.total),
            v.marca if v else '', v.modelo if v else '', v.color if v else '', v.placa if v else 'S/P', 
            v.anio if v else '', v.clase if v else '', v.tipo if v else '', v.uso if v else '',
            v.serial_motor if v else '', v.serial_carroceria_niv if v else '',
            nombre_usuario # <--- Añadimos el dato al Excel
        ])

    wb.save(response)
    return response

@login_required
def lista_cotizaciones(request):
    query = request.GET.get('q')
    # Traemos todas las cotizaciones ordenadas de la más reciente a la más antigua
    cotizaciones = Cotizacion.objects.select_related('cliente', 'usuario').all().order_by('-fecha_creacion', '-id')
    
    if query:
        cotizaciones = cotizaciones.filter(
            Q(id__icontains=query) |
            Q(cliente__nombre_razon_social__icontains=query) |
            Q(cliente__identificacion__icontains=query)
        )
        
    return render(request, 'facturacion/lista_cotizaciones.html', {'cotizaciones': cotizaciones})
