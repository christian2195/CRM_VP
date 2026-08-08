import openpyxl
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib import messages 

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from .models import Factura, Cotizacion, Vehiculo, ItemCotizacion, Cliente 
from .forms import CotizacionForm, FacturaForm, VehiculoForm, ClienteForm

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
        p.drawString(280, y_vehiculo-90, "SERIAL CARROCERÍA / NIV:")
        p.drawString(280, y_vehiculo-105, "SERIE/VERSIÓN:")
        
        # Valores - Columna Derecha
        p.setFont("Helvetica", 9)
        p.drawString(430, y_vehiculo, str(vehiculo_principal.tipo_combustible or ''))
        p.drawString(430, y_vehiculo-15, str(vehiculo_principal.num_puestos or ''))
        p.drawString(430, y_vehiculo-30, str(vehiculo_principal.num_ejes or ''))
        p.drawString(430, y_vehiculo-45, str(vehiculo_principal.peso_tara or ''))
        p.drawString(430, y_vehiculo-60, str(vehiculo_principal.capacidad_carga or ''))
        p.drawString(430, y_vehiculo-75, str(vehiculo_principal.serial_motor or ''))
        p.drawString(430, y_vehiculo-90, str(vehiculo_principal.serial_carroceria_niv or ''))
        p.drawString(430, y_vehiculo-105, str(vehiculo_principal.serie_version or ''))

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
    facturas_recientes = Factura.objects.select_related('cotizacion__cliente').order_by('-fecha_emision')[:5]
    cotizaciones_activas = Cotizacion.objects.exclude(estado__in=['F', 'A']).count()
    cotizaciones_pendientes = Cotizacion.objects.exclude(estado__in=['F', 'A']).order_by('-fecha_creacion')
    
    context = {
        'facturas': facturas_recientes,
        'cotizaciones_activas': cotizaciones_activas,
        'cotizaciones_pendientes': cotizaciones_pendientes,
    }
    return render(request, 'facturacion/dashboard.html', context)

def crear_cotizacion(request):
    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        if form.is_valid():
            cotizacion = form.save(commit=False)
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

def generar_factura(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    if hasattr(cotizacion, 'factura'):
        return redirect('dashboard')
        
    vehiculos_disponibles = Vehiculo.objects.all()

    if request.method == 'POST':
        form = FacturaForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cotizacion.items.all().delete()
                
                vehiculos_ids = request.POST.getlist('item_vehiculo[]')
                descripciones = request.POST.getlist('item_descripcion[]')
                cantidades = request.POST.getlist('item_cantidad[]')
                precios = request.POST.getlist('item_precio[]')
                ivas = request.POST.getlist('item_iva[]')
                
                for i in range(len(descripciones)):
                    vehiculo_id = vehiculos_ids[i] if vehiculos_ids[i] else None
                    if vehiculo_id:
                        vehiculo_obj = Vehiculo.objects.get(id=vehiculo_id)
                    else:
                        vehiculo_obj = None
                        
                    aplica_iva = True if ivas[i] == 'on' else False
                    
                    ItemCotizacion.objects.create(
                        cotizacion=cotizacion,
                        vehiculo=vehiculo_obj,
                        descripcion=descripciones[i],
                        cantidad=int(cantidades[i]),
                        precio_unitario=precios[i],
                        aplica_iva=aplica_iva
                    )
                
                cotizacion.refresh_from_db()

                factura = form.save(commit=False)
                factura.cotizacion = cotizacion
                factura.save()
                
            return redirect('imprimir_factura', factura_id=factura.id)
    else:
        form = FacturaForm(initial={'fecha_emision': timezone.now().date()})
        
    context = {
        'form': form,
        'cotizacion': cotizacion,
        'vehiculos_disponibles': vehiculos_disponibles,
    }
    return render(request, 'facturacion/generar_factura.html', context)

def lista_clientes(request):
    clientes = Cliente.objects.all().order_by('nombre_razon_social')
    return render(request, 'facturacion/lista_clientes.html', {'clientes': clientes})

def lista_vehiculos(request):
    vehiculos = Vehiculo.objects.all().order_by('-anio', 'marca')
    return render(request, 'facturacion/lista_vehiculos.html', {'vehiculos': vehiculos})

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

def imprimir_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Presupuesto_VP-{cotizacion.id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, 750, "EMVEPRO C.A. / VENEZUELA PRODUCTIVA C.A.")
    p.setFont("Helvetica", 8)
    p.drawString(50, 738, "RIF: G-20010522-4")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(380, 750, f"PRESUPUESTO: VP-{cotizacion.id}")
    p.drawString(380, 735, f"FECHA: {cotizacion.fecha_creacion.strftime('%d/%m/%Y')}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 710, "NOMBRE(S) Y APELLIDO(S) O RAZÓN SOCIAL:")
    p.setFont("Helvetica", 9)
    p.drawString(280, 710, f"{cliente.nombre_razon_social}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 695, "C.I. / R.I.F.:")
    p.setFont("Helvetica", 9)
    p.drawString(120, 695, f"{cliente.tipo_documento}-{cliente.identificacion}")
    
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 680, "DIRECCIÓN:")
    p.setFont("Helvetica", 7.5)
    p.drawString(120, 680, f"{cliente.direccion[:95]}")
    
    y_items = 640
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, y_items, "ITEM")
    p.drawString(85, y_items, "PRODUCTO / DESCRIPCIÓN")
    p.drawString(310, y_items, "PRECIO UNIT. ($)")
    p.drawString(410, y_items, "CANTIDAD")
    p.drawString(480, y_items, "SUBTOTAL ($)")
    
    y_items -= 15
    p.setFont("Helvetica", 8.5)
    
    cantidad_total_items = 0
    for index, item in enumerate(cotizacion.items.all(), start=1):
        subtotal_item = item.cantidad * item.precio_unitario
        cantidad_total_items += item.cantidad
        
        p.drawString(50, y_items, str(index))
        p.drawString(85, y_items, item.descripcion[:45])
        p.drawString(310, y_items, f"{item.precio_unitario:,.2f}")
        p.drawString(425, y_items, str(item.cantidad))
        p.drawString(480, y_items, f"{subtotal_item:,.2f}")
        y_items -= 18
        
    y_items -= 10
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(340, y_items, "CANTIDAD TOTAL:")
    p.drawString(480, y_items, str(cantidad_total_items))
    
    y_items -= 15
    p.drawString(340, y_items, "BASE IMPONIBLE:")
    p.drawString(480, y_items, f"{cotizacion.base_imponible:,.2f}")
    
    y_items -= 15
    p.drawString(340, y_items, "IVA (16%):")
    p.drawString(480, y_items, f"{cotizacion.impuesto_iva:,.2f}")
    
    y_items -= 15
    p.drawString(340, y_items, "TOTAL GENERAL:")
    p.drawString(480, y_items, f"{cotizacion.total:,.2f}")
    
    y_info = y_items - 30
    p.setFont("Helvetica-Bold", 7.5)
    p.drawString(50, y_info, "CONSIDERACIONES PARA LA VENTA:")
    p.setFont("Helvetica", 6.5)
    p.drawString(50, y_info - 10, "1. PRECIOS EXPRESADOS EN INCOTERM DAP (DELIVERY AT PLACE), incluye transporte y despacho hasta puerto destino.")
    p.drawString(50, y_info - 18, "2. PAGO INICIAL del 50% contra la cantidad de vehículos contenidos en cada Bill of Lading (BL).")
    p.drawString(50, y_info - 26, "3. PAGO DEL 50% RESTANTE según la cantidad parcial entregada en cada BL contra DAP.")
    p.drawString(50, y_info - 34, "4. GARANTÍA LIMITADA de un (1) año o 50.000 KM. Gestión ante División Vehicular Emvepro: (0412-6198651).")
    
    p.setFont("Helvetica-Bold", 7)
    p.drawString(50, y_info - 48, "Cuentas Bancarias: BANCO VENEZUELA: 0102-0762-2900-0001-9923 | TIPO: CORRIENTE")
    p.drawString(50, y_info - 56, "A NOMBRE DE: EMPRESA VENEZUELA PRODUCTIVA C.A. | RIF: G-20010522-4")
    
    y_firmas = y_info - 95
    p.setFont("Helvetica-Bold", 7)
    p.drawString(80, y_firmas, "REVISADO POR:")
    p.drawString(360, y_firmas, "AUTORIZADO POR:")
    
    p.drawString(70, y_firmas - 25, "Mercedes Varela")
    p.drawString(340, y_firmas - 25, "Jose Holberg Zambrano Gonzalez")
    p.setFont("Helvetica", 7)
    p.drawString(80, y_firmas - 33, "Gerente de Comercio")
    p.drawString(370, y_firmas - 33, "Presidente (E)")

    p.showPage()
    p.save()
    return response

def exportar_inventario_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="inventario_vehiculos_emvepro.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario"

    columns = [
        'Marca', 'Modelo', 'Anio', 'Color', 'Placa', 
        'Serial Carroceria NIV', 'Serial Motor', 'Tipo Combustible', 
        'Transmision', 'Clase', 'Tipo', 'Uso', 
        'Peso Tara', 'Capacidad Carga', 'Certificado Origen'
    ]
    ws.append(columns)

    for v in Vehiculo.objects.all():
        ws.append([
            v.marca, v.modelo, v.anio, v.color, v.placa, 
            v.serial_carroceria_niv, v.serial_motor, v.tipo_combustible, 
            v.transmision, v.clase, v.tipo, v.uso, 
            v.peso_tara, v.capacidad_carga, v.certificado_origen
        ])

    wb.save(response)
    return response

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
            for row in rows[1:]:
                if not row or not row[0]:
                    continue
                
                Vehiculo.objects.create(
                    marca=row[0] or '',
                    modelo=row[1] or '',
                    anio=int(row[2]) if row[2] else 2026,
                    color=row[3] or '',
                    placa=row[4] or '',
                    serial_carroceria_niv=row[5] or '',
                    serial_motor=row[6] or '',
                    tipo_combustible=row[7] or '',
                    transmision=row[8] or '',
                    clase=row[9] or '',
                    tipo=row[10] or '',
                    uso=row[11] or '',
                    peso_tara=float(row[12]) if row[12] else 0.0,
                    capacidad_carga=float(row[13]) if row[13] else 0.0,
                    certificado_origen=str(row[14]) if len(row) > 14 and row[14] else ''
                )
                count += 1
                
            messages.success(request, f'¡Carga masiva exitosa! Se importaron {count} vehículos al inventario.')
            return redirect('lista_vehiculos')
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {e}')
            return redirect('importar_inventario')
            
    return render(request, 'facturacion/importar_inventario.html')