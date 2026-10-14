import os
import openpyxl
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib import messages 
from django.db.models import Q, Sum, Prefetch
from django.contrib.auth.decorators import login_required

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from .models import Factura, Cotizacion, Vehiculo, ItemCotizacion, Cliente 
from .forms import CotizacionForm, FacturaForm, VehiculoForm, ClienteForm

# ==========================================
# UTILIDADES Y HELPERS
# ==========================================

def fmt_moneda(valor):
    """Formatea números al estándar venezolano: 10.045.812,00"""
    if valor is None or valor == '':
        valor = Decimal('0.00')
    return f"{Decimal(str(valor)):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def obtener_factor_bs(factura, cotizacion):
    """Calcula el factor de tasa de cambio si los ítems están en USD y la factura en Bs."""
    suma_items = sum((item.cantidad * item.precio_unitario) for item in cotizacion.items.all())
    subtotal_factura = (factura.base_imponible or Decimal('0.00')) + (factura.monto_exento or Decimal('0.00'))
    if suma_items > 0 and subtotal_factura > 0:
        return subtotal_factura / suma_items
    return Decimal('1.00')

# ==========================================
# DASHBOARD E INFORMES GLOBALES
# ==========================================

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
def estado_financiero(request):
    total_facturado = Factura.objects.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    total_base = Factura.objects.aggregate(Sum('base_imponible'))['base_imponible__sum'] or Decimal('0.00')
    total_iva = Factura.objects.aggregate(Sum('impuesto_iva'))['impuesto_iva__sum'] or Decimal('0.00')
    total_exento = Factura.objects.aggregate(Sum('monto_exento'))['monto_exento__sum'] or Decimal('0.00')
    
    facturas = Factura.objects.select_related('cotizacion__cliente').order_by('-fecha_emision')
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

# ==========================================
# GESTIÓN DE CLIENTES
# ==========================================

@login_required
def lista_clientes(request):
    query = request.GET.get('q')
    clientes = Cliente.objects.prefetch_related(
        Prefetch('cotizaciones', queryset=Cotizacion.objects.prefetch_related('factura', 'items__vehiculo'))
    ).order_by('-id')
    
    if query:
        clientes = clientes.filter(
            Q(nombre_razon_social__icontains=query) |
            Q(identificacion__icontains=query)
        )
    
    return render(request, 'facturacion/lista_clientes.html', {'clientes': clientes})

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
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Datos del cliente {cliente.nombre_razon_social} actualizados con éxito!')
            return redirect('lista_clientes')
        else:
            messages.error(request, 'Ocurrió un error al actualizar el cliente. Revisa los campos.')
    else:
        form = ClienteForm(instance=cliente)
        
    return render(request, 'facturacion/crear_cliente.html', {'form': form, 'editando': True, 'cliente': cliente})

# ==========================================
# GESTIÓN DE INVENTARIO VEHICULAR
# ==========================================

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
def exportar_inventario_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario Vehículos"

    cabeceras = [
        'N°', 'MARCA', 'MODELO', 'COLOR', 'PLACA', 'AÑO', 'CLASE', 'TIPO', 
        'USO', 'TRANSMISION', 'TIPO DE COMBUSTIBLE', 'N° DE PUESTOS', 'N° DE EJES', 
        'PESO (TARA)', 'CAPACIDAD DE CARGA (KG)', 'SERIAL MOTOR', 'SERIAL CARROCERIA Y NIV', 
        'CERTIFICADO DE ORIGEN', 'SERVICIO', 'PUERTO DE ENTRADA', 'FECHA DE LIQUIDACIÓN', 
        'PLANILLA DE LIQUIDACIÓN', 'FECHA DE FACTURACIÓN', 'FACTURA DE ADQUISIÓN', 
        'REFECIV', 'FECHA FIN DEL CONVENIO'
    ]
    ws.append(cabeceras)

    vehiculos = Vehiculo.objects.all().order_by('id')

    for contador, v in enumerate(vehiculos, start=1):
        fila = [
            contador,
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
            v.fecha_liquidacion.strftime('%Y-%m-%d') if v.fecha_liquidacion else '',
            v.planilla_liquidacion,
            v.fecha_facturacion.strftime('%Y-%m-%d') if v.fecha_facturacion else '',
            v.factura_adquisicion,
            v.refeciv,
            v.fecha_fin_convenio.strftime('%Y-%m-%d') if v.fecha_fin_convenio else ''
        ]
        ws.append(fila)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=inventario_vehiculos_emvepro.xlsx'
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

# ==========================================
# GESTIÓN DE COTIZACIONES
# ==========================================

@login_required
def lista_cotizaciones(request):
    query = request.GET.get('q')
    cotizaciones = Cotizacion.objects.select_related('cliente', 'usuario').all().order_by('-fecha_creacion', '-id')
    
    if query:
        cotizaciones = cotizaciones.filter(
            Q(id__icontains=query) |
            Q(cliente__nombre_razon_social__icontains=query) |
            Q(cliente__identificacion__icontains=query)
        )
        
    return render(request, 'facturacion/lista_cotizaciones.html', {'cotizaciones': cotizaciones})

@login_required
def crear_cotizacion(request):
    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cotizacion = form.save(commit=False)
                cotizacion.usuario = request.user
                cotizacion.save()
                
                descriptions = request.POST.getlist('item_descripcion[]')
                cantidades = request.POST.getlist('item_cantidad[]')
                precios = request.POST.getlist('item_precio[]')
                vehiculos = request.POST.getlist('item_vehiculo[]')
                ivas = request.POST.getlist('item_iva[]')
                
                subtotal_base = Decimal('0.00')
                subtotal_exento = Decimal('0.00')
                
                for i in range(len(descriptions)):
                    if not descriptions[i].strip():
                        continue 
                    
                    desc = descriptions[i]
                    cant = int(cantidades[i]) if cantidades[i] else 1
                    precio = Decimal(precios[i]) if precios[i] else Decimal('0.00')
                    aplica_iva = True if (i < len(ivas) and ivas[i] == 'on') else False
                    
                    vehiculo_id = vehiculos[i] if i < len(vehiculos) and vehiculos[i] else None
                    vehiculo = Vehiculo.objects.filter(id=vehiculo_id).first() if vehiculo_id else None
                    
                    subtotal_linea = cant * precio
                    if aplica_iva:
                        subtotal_base += subtotal_linea
                    else:
                        subtotal_exento += subtotal_linea
                    
                    ItemCotizacion.objects.create(
                        cotizacion=cotizacion,
                        vehiculo=vehiculo,
                        descripcion=desc,
                        cantidad=cant,
                        precio_unitario=precio,
                        aplica_iva=aplica_iva
                    )
                
                porc_desc = cotizacion.porcentaje_descuento or Decimal('0.00')
                desc_base = subtotal_base * (porc_desc / Decimal('100.00'))
                desc_exento = subtotal_exento * (porc_desc / Decimal('100.00'))
                
                cotizacion.monto_descuento = desc_base + desc_exento
                base_imponible = subtotal_base - desc_base
                monto_exento = subtotal_exento - desc_exento
                
                impuesto_iva = base_imponible * Decimal('0.16')
                total_general = base_imponible + monto_exento + impuesto_iva
                
                cotizacion.base_imponible = base_imponible
                cotizacion.impuesto_iva = impuesto_iva
                cotizacion.total = total_general
                cotizacion.save()
                
            messages.success(request, f'¡Cotización VP-{cotizacion.id} guardada con éxito!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Por favor verifique los datos generales de la cotización.')
    else:
        texto_default = "1. PRECIOS EXPRESADOS EN INCOTERM DAP (DELIVERY AT PLACE), incluye transporte y despacho hasta puerto destino.\n2. PAGO INICIAL del 50% contra la cantidad de vehículos contenidos en cada Bill of Lading (BL).\n3. PAGO DEL 50% RESTANTE según la cantidad parcial entregada en cada BL contra DAP.\n4. GARANTÍA LIMITADA de un (1) año o 50.000 KM."
        form = CotizacionForm(initial={'coletillas': texto_default})
        
    vehiculos_disponibles = Vehiculo.objects.filter(estado='Disponible')
    return render(request, 'facturacion/crear_cotizacion.html', {
        'form': form,
        'vehiculos_disponibles': vehiculos_disponibles
    })

@login_required
def eliminar_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    
    factura_previa = getattr(cotizacion, 'factura', None)
    if cotizacion.estado == 'F' and factura_previa and factura_previa.estado_pago != 'ANULADA':
        messages.error(request, f'No se puede anular la cotización VP-{cotizacion.id} porque tiene una factura activa asociada.')
        return redirect('lista_cotizaciones')
        
    with transaction.atomic():
        for item in cotizacion.items.all():
            if item.vehiculo and item.vehiculo.estado == 'Apartado':
                item.vehiculo.estado = 'Disponible'
                item.vehiculo.save()
                
        cotizacion.estado = 'A'
        cotizacion.save()
        
    messages.success(request, f'¡Cotización VP-{cotizacion.id} anulada con éxito y vehículos liberados!')
    return redirect('lista_cotizaciones')

@login_required
def imprimir_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Presupuesto_VP-{cotizacion.id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    # Cotizaciones sí llevan hoja membretada
    ruta_fondo = os.path.join(settings.BASE_DIR, 'static', 'img', 'Plantilla_Hoja_Membretada2.png')
    if os.path.exists(ruta_fondo):
        p.drawImage(ruta_fondo, 0, 0, width=width, height=height, mask='auto')

    COLOR_AZUL_MARINO = colors.HexColor('#273376')
    COLOR_GRIS_OSCURO = colors.HexColor('#333333')
    COLOR_TEXTO_PIE = colors.HexColor('#3B2314')

    meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    f = cotizacion.fecha_emision if hasattr(cotizacion, 'fecha_emision') and cotizacion.fecha_emision else cotizacion.fecha_creacion
    fecha_str = f"Caracas, {f.day} de {meses.get(f.month, '')} de {f.year}" if f else "Caracas"

    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(width - 55, height - 135, fecha_str)

    y_pos = height - 165
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(55, y_pos, f"PRESUPUESTO / COTIZACIÓN N°: VP-{cotizacion.id}")

    y_pos -= 22
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(55, y_pos, "DATOS DEL CLIENTE:")
    
    y_pos -= 15
    p.setFont("Helvetica-Bold", 8)
    p.drawString(55, y_pos, "Razón Social:")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(118, y_pos, f"{str(cliente.nombre_razon_social or '')[:42]}")
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(340, y_pos, "Teléfono:")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(385, y_pos, f"{str(cliente.telefono or 'N/A')}")
    
    y_pos -= 14
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(55, y_pos, "C.I. / R.I.F.:")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(118, y_pos, f"{str(cliente.tipo_documento or '')}-{str(cliente.identificacion or '')}")
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(340, y_pos, "Dirección:")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawString(385, y_pos, f"{str(cliente.direccion or 'N/A')[:35]}")

    y_pos -= 28
    p.setFillColor(COLOR_AZUL_MARINO)
    p.rect(55, y_pos - 4, width - 110, 18, fill=1, stroke=0)
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(colors.white)
    p.drawString(60, y_pos, "ITEM")
    p.drawString(95, y_pos, "PRODUCTO / DESCRIPCIÓN")
    p.drawRightString(395, y_pos, "PRECIO UNIT. ($)")
    p.drawCentredString(445, y_pos, "CANT.")
    p.drawRightString(width - 60, y_pos, "SUBTOTAL ($)")

    y_pos -= 18
    p.setFont("Helvetica", 8.5)
    p.setFillColor(COLOR_GRIS_OSCURO)
    
    cantidad_total_items = 0
    subtotal_bruto = Decimal('0.00')
    
    for index, item in enumerate(cotizacion.items.all(), start=1):
        cant = item.cantidad or 0
        precio = item.precio_unitario or Decimal('0.00')
        subtotal_item = cant * precio
        cantidad_total_items += cant
        subtotal_bruto += subtotal_item
        
        desc = str(item.descripcion or '')
        if item.vehiculo:
            desc += f" - {item.vehiculo.marca} {item.vehiculo.modelo} [{item.vehiculo.placa or 'S/P'}]"
            
        p.drawString(60, y_pos, str(index))
        p.drawString(95, y_pos, desc[:48])
        p.drawRightString(395, y_pos, fmt_moneda(precio))
        p.drawCentredString(445, y_pos, str(cant))
        p.drawRightString(width - 60, y_pos, fmt_moneda(subtotal_item))
        y_pos -= 16

    p.setStrokeColor(COLOR_AZUL_MARINO)
    p.setLineWidth(0.8)
    p.line(320, y_pos + 6, width - 55, y_pos + 6)

    y_pos -= 8
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(330, y_pos, "CANTIDAD TOTAL:")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(width - 60, y_pos, str(cantidad_total_items))
    
    y_pos -= 14
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(330, y_pos, "SUBTOTAL:")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(width - 60, y_pos, fmt_moneda(subtotal_bruto))
    
    if getattr(cotizacion, 'monto_descuento', 0) > 0:
        y_pos -= 14
        p.setFillColor(COLOR_AZUL_MARINO)
        p.drawString(330, y_pos, f"DESCUENTO ({cotizacion.porcentaje_descuento}%):")
        p.setFillColor(COLOR_GRIS_OSCURO)
        p.drawRightString(width - 60, y_pos, f"- {fmt_moneda(cotizacion.monto_descuento)}")
    
    y_pos -= 14
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(330, y_pos, "BASE IMPONIBLE (GRAVABLE):")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(width - 60, y_pos, fmt_moneda(cotizacion.base_imponible))
    
    y_pos -= 14
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(330, y_pos, "IVA (16%):")
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawRightString(width - 60, y_pos, fmt_moneda(cotizacion.impuesto_iva))
    
    y_pos -= 15
    p.setFont("Helvetica-Bold", 9.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(330, y_pos, "TOTAL GENERAL ($):")
    p.drawRightString(width - 60, y_pos, fmt_moneda(cotizacion.total))

    y_pos -= 28
    p.setFont("Helvetica-Bold", 7.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(55, y_pos, "CONSIDERACIONES Y CONDICIONES:")
    p.setFont("Helvetica", 6.5)
    p.setFillColor(COLOR_GRIS_OSCURO)
    
    y_col = y_pos - 10
    if getattr(cotizacion, 'coletillas', None):
        for linea in str(cotizacion.coletillas).split('\n'):
            p.drawString(55, y_col, linea.strip())
            y_col -= 8
    else:
        p.drawString(55, y_col, "Condiciones estándar no especificadas.")
        
    p.setFont("Helvetica-Bold", 6.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawString(55, y_col - 12, "Cuentas Bancarias: BANCO DE VENEZUELA: 0102-0762-2900-0001-9923 | TIPO: CORRIENTE")
    p.drawString(55, y_col - 20, "A NOMBRE DE: EMPRESA VENEZUELA PRODUCTIVA C.A. | RIF: G-20010522-4")

    y_firmas = 190
    p.setStrokeColor(COLOR_AZUL_MARINO)
    p.setLineWidth(0.6)
    p.line(85, y_firmas, 245, y_firmas)
    p.line(365, y_firmas, 525, y_firmas)

    p.setFont("Helvetica-Bold", 7.5)
    p.setFillColor(COLOR_AZUL_MARINO)
    p.drawCentredString(165, y_firmas + 6, "REVISADO POR:")
    p.drawCentredString(445, y_firmas + 6, "AUTORIZADO POR:")
    
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_GRIS_OSCURO)
    p.drawCentredString(165, y_firmas - 12, "Mercedes Varela")
    p.drawCentredString(445, y_firmas - 12, "Jose Holberg Zambrano Gonzalez")
    
    p.setFont("Helvetica", 7)
    p.drawCentredString(165, y_firmas - 21, "Gerente de Comercio")
    p.drawCentredString(445, y_firmas - 21, "Presidente (E)")

    # Cotizaciones sí llevan QR
    tel_fijo = "+58 212 802 8300"
    tel_movil = "+58 412 619 8651"
    red_social = "@somosvenezuelaproductiva"
    web_url = "emvepro.gob.ve"
    dir_linea1 = "Final Av. Panteón, Diagonal al Panteón Nacional"
    dir_linea2 = "Caracas 1010, Distrito Capital - R.B. Venezuela"

    qr_texto = (f"EMVEPRO C.A. | RIF: G-20010522-4\nPresupuesto: VP-{cotizacion.id}\nCliente: {cliente.nombre_razon_social}\nTotal: ${fmt_moneda(cotizacion.total)}")
    qr_widget = qr.QrCodeWidget(qr_texto)
    qr_widget.barLevel = 'M'
    qr_widget.barFillColor = COLOR_TEXTO_PIE
    bounds = qr_widget.getBounds()
    qr_w = bounds[2] - bounds[0]
    qr_h = bounds[3] - bounds[1]
    size_qr = 52
    d = Drawing(size_qr, size_qr, transform=[size_qr / qr_w, 0, 0, size_qr / qr_h, 0, 0])
    d.add(qr_widget)
    x_qr = 68
    y_qr = 70
    d.drawOn(p, x_qr, y_qr)

    p.setFont("Helvetica-BoldOblique", 6.5)
    p.setFillColor(COLOR_TEXTO_PIE)
    p.drawCentredString(x_qr + (size_qr / 2), y_qr - 7, web_url)

    x_icon = 142
    x_text = 158
    p.setStrokeColor(COLOR_TEXTO_PIE)
    p.setFillColor(COLOR_TEXTO_PIE)
    p.setLineWidth(0.8)

    y_row1 = 112
    p.circle(x_icon + 4, y_row1 + 2.5, 4.2, stroke=1, fill=0)
    p.setFont("Helvetica-Bold", 5.5)
    p.drawCentredString(x_icon + 4, y_row1 + 0.5, "T")
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_text, y_row1, tel_fijo)

    y_row2 = 99
    p.circle(x_icon + 4, y_row2 + 2.5, 4.2, stroke=1, fill=0)
    p.setFont("Helvetica-Bold", 5)
    p.drawCentredString(x_icon + 4, y_row2 + 0.5, "W")
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_text, y_row2, tel_movil)

    y_row3 = 86
    p.roundRect(x_icon, y_row3 - 1, 8.2, 8.2, 2, stroke=1, fill=0)
    p.circle(x_icon + 4.1, y_row3 + 3.1, 2, stroke=1, fill=0)
    p.circle(x_icon + 6.5, y_row3 + 5.5, 0.4, stroke=0, fill=1)
    p.setFont("Helvetica-Oblique", 7.5)
    p.drawString(x_text, y_row3, red_social)

    y_row4 = 74
    p.circle(x_icon + 4.1, y_row4 + 1.5, 3.6, stroke=1, fill=0)
    p.circle(x_icon + 4.1, y_row4 + 1.5, 1.2, stroke=0, fill=1)
    p.line(x_icon + 1.2, y_row4 - 0.5, x_icon + 4.1, y_row4 - 5)
    p.line(x_icon + 7.0, y_row4 - 0.5, x_icon + 4.1, y_row4 - 5)
    
    p.setFont("Helvetica-Oblique", 6.5)
    p.drawString(x_text, y_row4, dir_linea1)
    p.drawString(x_text, y_row4 - 8, dir_linea2)

    p.showPage()
    p.save()
    return response

# ==========================================
# GESTIÓN DE FACTURAS Y COBRANZAS
# ==========================================

@login_required
def generar_factura(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    factura_previa = getattr(cotizacion, 'factura', None)
    
    if cotizacion.estado == 'F' and (not factura_previa or factura_previa.estado_pago != 'ANULADA'):
        messages.warning(request, 'Esta cotización ya ha sido facturada previamente y está activa.')
        return redirect('dashboard')
        
    vehiculos_disponibles = Vehiculo.objects.filter(
        Q(estado='Disponible') | 
        Q(id__in=cotizacion.items.filter(vehiculo__isnull=False).values_list('vehiculo_id', flat=True))
    )

    if request.method == 'POST':
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
                
                subtotal_base = Decimal('0.00')
                subtotal_exento = Decimal('0.00')
                
                for i in range(len(descripciones)):
                    vehiculo_id = vehiculos_ids[i] if vehiculos_ids[i] else None
                    vehiculo_obj = Vehiculo.objects.filter(id=vehiculo_id).first() if vehiculo_id else None
                        
                    aplica_iva = True if ivas[i] == 'on' else False
                    cant = int(cantidades[i])
                    precio_usd = Decimal(precios[i])
                    
                    subtotal_linea = cant * precio_usd
                    if aplica_iva:
                        subtotal_base += subtotal_linea
                    else:
                        subtotal_exento += subtotal_linea
                    
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
                
                porc_desc = cotizacion.porcentaje_descuento or Decimal('0.00')
                desc_base = subtotal_base * (porc_desc / Decimal('100.00'))
                desc_exento = subtotal_exento * (porc_desc / Decimal('100.00'))
                
                cotizacion.monto_descuento = desc_base + desc_exento
                base_imponible_usd = subtotal_base - desc_base
                monto_exento_usd = subtotal_exento - desc_exento

                cotizacion.base_imponible = base_imponible_usd
                cotizacion.monto_exento = monto_exento_usd
                cotizacion.impuesto_iva = base_imponible_usd * Decimal('0.16')
                cotizacion.total = cotizacion.base_imponible + cotizacion.monto_exento + cotizacion.impuesto_iva
                cotizacion.estado = 'F'
                cotizacion.save()

                factura = form.save(commit=False)
                factura.cotizacion = cotizacion
                factura.usuario = request.user
                
                factura.base_imponible = base_imponible_usd * tasa_cambio
                factura.monto_exento = monto_exento_usd * tasa_cambio
                factura.impuesto_iva = factura.base_imponible * Decimal('0.16')
                factura.total = factura.base_imponible + factura.monto_exento + factura.impuesto_iva
                
                factura.estado_pago = 'PENDIENTE' 
                factura.porcentaje_pago = 0
                factura.save()
                
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
def actualizar_pago_factura(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    if request.method == 'POST':
        estado = request.POST.get('estado_pago')
        porcentaje_str = request.POST.get('porcentaje_pago')
        
        if estado in dict(Factura.ESTADOS_PAGO).keys():
            factura.estado_pago = estado
            
            if porcentaje_str and str(porcentaje_str).strip():
                porcentaje = int(porcentaje_str)
            else:
                porcentaje = 0
                
            if factura.estado_pago == 'ANULADA':
                factura.porcentaje_pago = 0
                factura.base_imponible = Decimal('0.00')
                factura.impuesto_iva = Decimal('0.00')
                factura.monto_exento = Decimal('0.00')
                factura.total = Decimal('0.00')
                
                for item in factura.cotizacion.items.all():
                    if item.vehiculo:
                        item.vehiculo.estado = 'Disponible'
                        item.vehiculo.save()
                
                cotizacion = factura.cotizacion
                cotizacion.estado = 'P' 
                cotizacion.save()
            else:
                factura.porcentaje_pago = porcentaje
                if factura.porcentaje_pago >= 100:
                    factura.estado_pago = 'PAGADA'
                    factura.porcentaje_pago = 100
                elif factura.porcentaje_pago == 0 and factura.estado_pago != 'PENDIENTE':
                    factura.estado_pago = 'PENDIENTE'
                
            factura.save()
            messages.success(request, f'Estatus de la factura {factura.numero_factura} actualizado con éxito.')
            
    referer = request.META.get('HTTP_REFERER')
    if referer and 'historial' in referer:
        return redirect('historial_facturas')
    return redirect('estado_financiero')

# ==========================================
# IMPRESIONES PDF - FACTURAS BOLÍVARES (BLANCO Y NEGRO, SIN FONDO, SIN QR)
# ==========================================

@login_required
def imprimir_factura_forma_libre(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    COLOR_NEGRO = colors.black

    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(COLOR_NEGRO)
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
    p.setStrokeColor(COLOR_NEGRO)
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
    factor_bs = obtener_factor_bs(factura, cotizacion)
    
    for item in cotizacion.items.all():
        if item.vehiculo and not vehiculo_principal:
            vehiculo_principal = item.vehiculo
        tipo_iva = "ALIC. GENER." if item.aplica_iva else "EXENTO"
        alic_porcentaje = "16,00%" if item.aplica_iva else "0,00%"
        subtotal_item = (item.cantidad * item.precio_unitario) * factor_bs
        p.drawString(75, y_items, str(item.cantidad))
        # Ajustado a 30 caracteres para que no se superponga con TIPO DE IVA
        p.drawString(130, y_items, item.descripcion[:30]) 
        p.drawString(280, y_items, tipo_iva)
        p.drawString(390, y_items, alic_porcentaje)
        p.drawRightString(550, y_items, fmt_moneda(subtotal_item))
        y_items -= 16

    p.setLineWidth(1)
    p.line(40, y_items + 4, 560, y_items + 4)
    
    y_veh = y_items - 12
    if vehiculo_principal:
        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, y_veh, "DESCRIPCIÓN DEL VEHÍCULO")
        y_veh -= 14
        
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
            ("N° EJES :", vehiculo_principal.num_ejes),
            ("PESO (TARA):", vehiculo_principal.peso_tara),
            ("CAPACIDAD DE CARGA (KG.):", vehiculo_principal.capacidad_carga),
            ("SERIAL DE MOTOR:", vehiculo_principal.serial_motor),
            ("SERIAL DE CARROCERIA:", vehiculo_principal.serial_carroceria_niv),
            ("SERIAL NIV:", vehiculo_principal.serial_carroceria_niv),
            ("SERIE/VERSIÓN", getattr(vehiculo_principal, 'serie_version', '') or '')
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
    
    monto_descuento_cot = getattr(cotizacion, 'monto_descuento', 0)
    if monto_descuento_cot > 0:
        desc_bs = monto_descuento_cot * factor_bs
        subtotal_bruto_bs = factura.base_imponible + factura.monto_exento + desc_bs
        p.drawRightString(440, y_tot, "SUBTOTAL")
        p.drawRightString(550, y_tot, fmt_moneda(subtotal_bruto_bs))
        y_tot -= 14
        p.drawRightString(440, y_tot, f"DESCUENTO ({cotizacion.porcentaje_descuento}%)")
        p.drawRightString(550, y_tot, f"- {fmt_moneda(desc_bs)}")
        y_tot -= 14

    p.drawRightString(440, y_tot, "BASE IMPONIBLE GRAVABLE")
    p.drawRightString(550, y_tot, fmt_moneda(factura.base_imponible))
    y_tot -= 14
    p.drawRightString(440, y_tot, "I.V.A. (16%)")
    p.drawRightString(550, y_tot, fmt_moneda(factura.impuesto_iva))
    y_tot -= 14
    p.drawRightString(440, y_tot, "EXENTO (E)")
    p.drawRightString(550, y_tot, fmt_moneda(factura.monto_exento))
    p.line(320, y_tot - 4, 560, y_tot - 4)
    y_tot -= 14
    p.setFont("Helvetica-Bold", 9)
    p.drawRightString(440, y_tot, "TOTAL GENERAL")
    p.drawRightString(550, y_tot, fmt_moneda(factura.total))

    p.showPage()
    p.save()
    return response

@login_required
def imprimir_factura_institucional(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_Institucional_Bs_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    COLOR_NEGRO = colors.black

    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(COLOR_NEGRO)
    p.drawString(400, 630, "FACTURA N°:")
    p.drawString(400, 610, "N° DE CONTROL:")
    p.drawString(400, 590, "FECHA DE EMISIÓN:")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(550, 630, str(factura.numero_factura))
    p.drawRightString(550, 610, str(factura.numero_control))
    p.drawRightString(550, 590, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(46, 540, "RAZÓN SOCIAL:")
    p.drawString(46, 495, "C.I. / R.I.F.:")
    p.drawString(46, 475, "DIRECCIÓN:")
    p.drawString(330, 495, "TELÉFONO:")
    
    p.setFont("Helvetica", 8.5)
    p.drawString(130, 540, str(cliente.nombre_razon_social))
    p.drawString(130, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(130, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(390, 495, str(cliente.telefono or 'N/A'))
    
    # --- CUADRO DETALLADO (CON SAP EN Bs) ---
    data = [['CANT', 'CÓD. SAP', 'DESCRIPCIÓN', 'MARCA', 'MODELO', 'PLACA', 'AÑO', 'COLOR', 'S. MOTOR', 'S. CARROC./NIV', 'TRANS.', 'PRECIO']]
    col_widths = [20, 35, 75, 40, 40, 35, 20, 25, 55, 80, 35, 60] 
    
    factor_bs = obtener_factor_bs(factura, cotizacion)
    for item in cotizacion.items.all():
        v = item.vehiculo
        precio_item = item.precio_unitario * factor_bs
        data.append([
            str(item.cantidad),
            "1124626", 
            item.descripcion[:22],
            v.marca[:10] if v else '',
            v.modelo[:10] if v else '',
            v.placa if v else 'S/P',
            str(v.anio) if v else '',
            v.color[:7] if v else '',
            v.serial_motor[:15] if v else '',
            v.serial_carroceria_niv[:18] if v else '',
            v.transmision[:6] if v else '',
            fmt_moneda(precio_item)
        ])
    
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_NEGRO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),   
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 5.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_NEGRO),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    table.wrapOn(p, width, height)
    w_t, h_t = table.wrap(width, height)
    y_table_bottom = 435 - h_t
    table.drawOn(p, 46, y_table_bottom)

    y_tot = y_table_bottom - 20
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7)
        p.drawString(46, y_tot, "Condiciones y Coletillas:")
        p.setFont("Helvetica", 6.5)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(46, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    
    monto_descuento_cot = getattr(cotizacion, 'monto_descuento', 0)
    if monto_descuento_cot > 0:
        desc_bs = monto_descuento_cot * factor_bs
        subtotal_bruto_bs = factura.base_imponible + factura.monto_exento + desc_bs
        p.drawString(330, y_tot, "Subtotal Bs.:")
        p.drawRightString(566, y_tot, fmt_moneda(subtotal_bruto_bs))
        y_tot -= 14
        p.drawString(330, y_tot, f"Descuento ({cotizacion.porcentaje_descuento}%) Bs.:")
        p.drawRightString(566, y_tot, f"- {fmt_moneda(desc_bs)}")
        y_tot -= 14

    p.drawString(330, y_tot, "Base Imponible Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.base_imponible))
    y_tot -= 14
    p.drawString(330, y_tot, "Exento Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.monto_exento))
    y_tot -= 14
    p.drawString(330, y_tot, "I.V.A. (16%) Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.impuesto_iva))
    
    p.setStrokeColor(COLOR_NEGRO)
    p.setLineWidth(1)
    p.line(320, y_tot - 4, 566, y_tot - 4)
    y_tot -= 14
    
    p.setFont("Helvetica-Bold", 9.5)
    p.drawString(330, y_tot, "TOTAL GENERAL Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.total))

    p.showPage()
    p.save()
    return response


@login_required
def imprimir_factura_institucional_sin_sap(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_Inst_Sin_SAP_Bs_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    COLOR_NEGRO = colors.black

    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(COLOR_NEGRO)
    p.drawString(400, 630, "FACTURA N°:")
    p.drawString(400, 610, "N° DE CONTROL:")
    p.drawString(400, 590, "FECHA DE EMISIÓN:")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(550, 630, str(factura.numero_factura))
    p.drawRightString(550, 610, str(factura.numero_control))
    p.drawRightString(550, 590, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(46, 540, "RAZÓN SOCIAL:")
    p.drawString(46, 495, "C.I. / R.I.F.:")
    p.drawString(46, 475, "DIRECCIÓN:")
    p.drawString(330, 495, "TELÉFONO:")
    
    p.setFont("Helvetica", 8.5)
    p.drawString(130, 540, str(cliente.nombre_razon_social))
    p.drawString(130, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(130, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(390, 495, str(cliente.telefono or 'N/A'))
    
    # --- CUADRO DETALLADO (SIN SAP EN Bs) ---
    data = [['CANT', 'DESCRIPCIÓN', 'MARCA', 'MODELO', 'PLACA', 'AÑO', 'COLOR', 'S. MOTOR', 'S. CARROC./NIV', 'TRANS.', 'PRECIO']]
    col_widths = [20, 100, 45, 45, 35, 20, 25, 60, 75, 35, 60] 
    
    factor_bs = obtener_factor_bs(factura, cotizacion)
    for item in cotizacion.items.all():
        v = item.vehiculo
        precio_item = item.precio_unitario * factor_bs
        data.append([
            str(item.cantidad),
            item.descripcion[:26],
            v.marca[:10] if v else '',
            v.modelo[:10] if v else '',
            v.placa if v else 'S/P',
            str(v.anio) if v else '',
            v.color[:8] if v else '',
            v.serial_motor[:15] if v else '',
            v.serial_carroceria_niv[:18] if v else '',
            v.transmision[:6] if v else '',
            fmt_moneda(precio_item)
        ])
    
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_NEGRO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),   
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 5.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_NEGRO),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    table.wrapOn(p, width, height)
    w_t, h_t = table.wrap(width, height)
    y_table_bottom = 435 - h_t
    table.drawOn(p, 46, y_table_bottom)

    y_tot = y_table_bottom - 20
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7)
        p.drawString(46, y_tot, "Condiciones y Coletillas:")
        p.setFont("Helvetica", 6.5)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(46, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    
    monto_descuento_cot = getattr(cotizacion, 'monto_descuento', 0)
    if monto_descuento_cot > 0:
        desc_bs = monto_descuento_cot * factor_bs
        subtotal_bruto_bs = factura.base_imponible + factura.monto_exento + desc_bs
        p.drawString(330, y_tot, "Subtotal Bs.:")
        p.drawRightString(566, y_tot, fmt_moneda(subtotal_bruto_bs))
        y_tot -= 14
        p.drawString(330, y_tot, f"Descuento ({cotizacion.porcentaje_descuento}%) Bs.:")
        p.drawRightString(566, y_tot, f"- {fmt_moneda(desc_bs)}")
        y_tot -= 14

    p.drawString(330, y_tot, "Base Imponible Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.base_imponible))
    y_tot -= 14
    p.drawString(330, y_tot, "Exento Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.monto_exento))
    y_tot -= 14
    p.drawString(330, y_tot, "I.V.A. (16%) Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.impuesto_iva))
    
    p.setStrokeColor(COLOR_NEGRO)
    p.setLineWidth(1)
    p.line(320, y_tot - 4, 566, y_tot - 4)
    y_tot -= 14
    
    p.setFont("Helvetica-Bold", 9.5)
    p.drawString(330, y_tot, "TOTAL GENERAL Bs.:")
    p.drawRightString(566, y_tot, fmt_moneda(factura.total))

    p.showPage()
    p.save()
    return response

# ==========================================
# IMPRESIONES PDF - FACTURAS DÓLARES (BLANCO Y NEGRO, SIN FONDO, SIN QR)
# ==========================================

@login_required
def imprimir_factura_dolares(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_USD_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    COLOR_NEGRO = colors.black

    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(COLOR_NEGRO)
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
    p.setStrokeColor(COLOR_NEGRO)
    p.setLineWidth(1.5)
    p.line(40, y_line1, 560, y_line1)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(55, y_line1 - 12, "CANTIDAD")
    p.drawString(130, y_line1 - 12, "DESCRIPCION")
    p.drawString(280, y_line1 - 12, "TIPO DE IVA")
    p.drawString(390, y_line1 - 12, "ALIC.%")
    p.drawRightString(550, y_line1 - 12, "PREC. $")
    y_line2 = y_line1 - 18
    p.line(40, y_line2, 560, y_line2)
    
    y_items = y_line2 - 14
    p.setFont("Helvetica", 8)
    vehiculo_principal = None
    
    base_imponible_usd = Decimal('0.00')
    monto_exento_usd = Decimal('0.00')
    
    for item in cotizacion.items.all():
        if item.vehiculo and not vehiculo_principal:
            vehiculo_principal = item.vehiculo
        tipo_iva = "ALIC. GENER." if item.aplica_iva else "EXENTO"
        alic_porcentaje = "16,00%" if item.aplica_iva else "0,00%"
        
        subtotal_item = Decimal(str(item.cantidad)) * Decimal(str(item.precio_unitario))
        if item.aplica_iva:
            base_imponible_usd += subtotal_item
        else:
            monto_exento_usd += subtotal_item
            
        p.drawString(75, y_items, str(item.cantidad))
        # Ajustado a 30 caracteres para que no se superponga con TIPO DE IVA
        p.drawString(130, y_items, item.descripcion[:30])
        p.drawString(280, y_items, tipo_iva)
        p.drawString(390, y_items, alic_porcentaje)
        p.drawRightString(550, y_items, fmt_moneda(subtotal_item))
        y_items -= 16

    impuesto_iva_usd = base_imponible_usd * Decimal('0.16')
    total_usd = base_imponible_usd + monto_exento_usd + impuesto_iva_usd

    p.setLineWidth(1)
    p.line(40, y_items + 4, 560, y_items + 4)
    
    y_veh = y_items - 12
    if vehiculo_principal:
        p.setFont("Helvetica-Bold", 8)
        p.drawString(40, y_veh, "DESCRIPCIÓN DEL VEHÍCULO")
        y_veh -= 14
        
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
            ("N° EJES :", vehiculo_principal.num_ejes),
            ("PESO (TARA):", vehiculo_principal.peso_tara),
            ("CAPACIDAD DE CARGA (KG.):", vehiculo_principal.capacidad_carga),
            ("SERIAL DE MOTOR:", vehiculo_principal.serial_motor),
            ("SERIAL DE CARROCERIA:", vehiculo_principal.serial_carroceria_niv),
            ("SERIAL NIV:", vehiculo_principal.serial_carroceria_niv),
            ("SERIE/VERSIÓN:", getattr(vehiculo_principal, 'serie_version', '') or '')
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
    
    monto_descuento_cot = getattr(cotizacion, 'monto_descuento', 0)
    if monto_descuento_cot > 0:
        subtotal_bruto_usd = cotizacion.base_imponible + cotizacion.monto_exento + cotizacion.monto_descuento
        p.drawRightString(440, y_tot, "SUBTOTAL ($)")
        p.drawRightString(550, y_tot, fmt_moneda(subtotal_bruto_usd))
        y_tot -= 14
        p.drawRightString(440, y_tot, f"DESCUENTO ({cotizacion.porcentaje_descuento}%) ($)")
        p.drawRightString(550, y_tot, f"- {fmt_moneda(monto_descuento_cot)}")
        y_tot -= 14

    p.drawRightString(440, y_tot, "BASE IMPONIBLE GRAVABLE ($)")
    p.drawRightString(550, y_tot, fmt_moneda(base_imponible_usd))
    y_tot -= 14
    p.drawRightString(440, y_tot, "I.V.A. (16%) ($)")
    p.drawRightString(550, y_tot, fmt_moneda(impuesto_iva_usd))
    y_tot -= 14
    p.drawRightString(440, y_tot, "EXENTO (E) ($)")
    p.drawRightString(550, y_tot, fmt_moneda(monto_exento_usd))
    p.line(320, y_tot - 4, 560, y_tot - 4)
    y_tot -= 14
    p.setFont("Helvetica-Bold", 9)
    p.drawRightString(440, y_tot, "TOTAL GENERAL ($)")
    p.drawRightString(550, y_tot, fmt_moneda(total_usd))

    p.showPage()
    p.save()
    return response

@login_required
def imprimir_factura_institucional_dolares(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_Institucional_USD_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    COLOR_NEGRO = colors.black

    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(COLOR_NEGRO)
    p.drawString(400, 630, "FACTURA N°:")
    p.drawString(400, 610, "N° DE CONTROL:")
    p.drawString(400, 590, "FECHA DE EMISIÓN:")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(550, 630, str(factura.numero_factura))
    p.drawRightString(550, 610, str(factura.numero_control))
    p.drawRightString(550, 590, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(46, 540, "RAZÓN SOCIAL:")
    p.drawString(46, 495, "C.I. / R.I.F.:")
    p.drawString(46, 475, "DIRECCIÓN:")
    p.drawString(330, 495, "TELÉFONO:")
    
    p.setFont("Helvetica", 8.5)
    p.drawString(130, 540, str(cliente.nombre_razon_social))
    p.drawString(130, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(130, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(390, 495, str(cliente.telefono or 'N/A'))
    
    data = [['CANT', 'CÓD. SAP', 'DESCRIPCIÓN', 'MARCA', 'MODELO', 'PLACA', 'AÑO', 'COLOR', 'S. MOTOR', 'S. CARROC./NIV', 'TRANS.', 'PRECIO']]
    col_widths = [20, 35, 75, 40, 40, 35, 20, 25, 55, 80, 35, 60] 

    for item in cotizacion.items.all():
        v = item.vehiculo
        precio_item = item.precio_unitario
        data.append([
            str(item.cantidad),
            "1124626", 
            item.descripcion[:22],
            v.marca[:10] if v else '',
            v.modelo[:10] if v else '',
            v.placa if v else 'S/P',
            str(v.anio) if v else '',
            v.color[:7] if v else '',
            v.serial_motor[:15] if v else '',
            v.serial_carroceria_niv[:18] if v else '',
            v.transmision[:6] if v else '',
            fmt_moneda(precio_item)
        ])
    
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_NEGRO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),   
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 5.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_NEGRO),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    table.wrapOn(p, width, height)
    w_t, h_t = table.wrap(width, height)
    y_table_bottom = 435 - h_t
    table.drawOn(p, 46, y_table_bottom)

    y_tot = y_table_bottom - 20
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7)
        p.drawString(46, y_tot, "Condiciones y Coletillas:")
        p.setFont("Helvetica", 6.5)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(46, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    
    monto_descuento_cot = getattr(cotizacion, 'monto_descuento', 0)
    if monto_descuento_cot > 0:
        subtotal_bruto_usd = cotizacion.base_imponible + cotizacion.monto_exento + cotizacion.monto_descuento
        p.drawString(330, y_tot, "Subtotal $:")
        p.drawRightString(566, y_tot, fmt_moneda(subtotal_bruto_usd))
        y_tot -= 14
        p.drawString(330, y_tot, f"Descuento ({cotizacion.porcentaje_descuento}%) $:")
        p.drawRightString(566, y_tot, f"- {fmt_moneda(monto_descuento_cot)}")
        y_tot -= 14

    p.drawString(330, y_tot, "Base Imponible $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.base_imponible))
    y_tot -= 14
    p.drawString(330, y_tot, "Exento $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.monto_exento))
    y_tot -= 14
    p.drawString(330, y_tot, "I.V.A. (16%) $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.impuesto_iva))
    
    p.setStrokeColor(COLOR_NEGRO)
    p.setLineWidth(1)
    p.line(320, y_tot - 4, 566, y_tot - 4)
    y_tot -= 14
    
    p.setFont("Helvetica-Bold", 9.5)
    p.drawString(330, y_tot, "TOTAL GENERAL $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.total))

    p.showPage()
    p.save()
    return response

@login_required
def imprimir_factura_institucional_sin_sap_dolares(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Factura_Inst_Sin_SAP_USD_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    COLOR_NEGRO = colors.black

    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(COLOR_NEGRO)
    p.drawString(400, 630, "FACTURA N°:")
    p.drawString(400, 610, "N° DE CONTROL:")
    p.drawString(400, 590, "FECHA DE EMISIÓN:")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(550, 630, str(factura.numero_factura))
    p.drawRightString(550, 610, str(factura.numero_control))
    p.drawRightString(550, 590, factura.fecha_emision.strftime('%d/%m/%Y'))
    
    p.setFont("Helvetica-Bold", 8.5)
    p.drawString(46, 540, "RAZÓN SOCIAL:")
    p.drawString(46, 495, "C.I. / R.I.F.:")
    p.drawString(46, 475, "DIRECCIÓN:")
    p.drawString(330, 495, "TELÉFONO:")
    
    p.setFont("Helvetica", 8.5)
    p.drawString(130, 540, str(cliente.nombre_razon_social))
    p.drawString(130, 495, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(130, 475, str(cliente.direccion[:85] if cliente.direccion else ''))
    p.drawString(390, 495, str(cliente.telefono or 'N/A'))
    
    data = [['CANT', 'DESCRIPCIÓN', 'MARCA', 'MODELO', 'PLACA', 'AÑO', 'COLOR', 'S. MOTOR', 'S. CARROC./NIV', 'TRANS.', 'PRECIO']]
    col_widths = [20, 100, 45, 45, 35, 20, 25, 60, 75, 35, 60] 

    for item in cotizacion.items.all():
        v = item.vehiculo
        precio_item = item.precio_unitario
        data.append([
            str(item.cantidad),
            item.descripcion[:26],
            v.marca[:10] if v else '',
            v.modelo[:10] if v else '',
            v.placa if v else 'S/P',
            str(v.anio) if v else '',
            v.color[:8] if v else '',
            v.serial_motor[:15] if v else '',
            v.serial_carroceria_niv[:18] if v else '',
            v.transmision[:6] if v else '',
            fmt_moneda(precio_item)
        ])
    
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_NEGRO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),   
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 5.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_NEGRO),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    table.wrapOn(p, width, height)
    w_t, h_t = table.wrap(width, height)
    y_table_bottom = 435 - h_t
    table.drawOn(p, 46, y_table_bottom)

    y_tot = y_table_bottom - 20
    if factura.coletillas:
        p.setFont("Helvetica-Bold", 7)
        p.drawString(46, y_tot, "Condiciones y Coletillas:")
        p.setFont("Helvetica", 6.5)
        y_col = y_tot - 10
        for linea in str(factura.coletillas).split('\n'):
            p.drawString(46, y_col, linea.strip())
            y_col -= 9
            
    p.setFont("Helvetica-Bold", 8)
    
    monto_descuento_cot = getattr(cotizacion, 'monto_descuento', 0)
    if monto_descuento_cot > 0:
        subtotal_bruto_usd = cotizacion.base_imponible + cotizacion.monto_exento + cotizacion.monto_descuento
        p.drawString(330, y_tot, "Subtotal $:")
        p.drawRightString(566, y_tot, fmt_moneda(subtotal_bruto_usd))
        y_tot -= 14
        p.drawString(330, y_tot, f"Descuento ({cotizacion.porcentaje_descuento}%) $:")
        p.drawRightString(566, y_tot, f"- {fmt_moneda(monto_descuento_cot)}")
        y_tot -= 14

    p.drawString(330, y_tot, "Base Imponible $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.base_imponible))
    y_tot -= 14
    p.drawString(330, y_tot, "Exento $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.monto_exento))
    y_tot -= 14
    p.drawString(330, y_tot, "I.V.A. (16%) $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.impuesto_iva))
    
    p.setStrokeColor(COLOR_NEGRO)
    p.setLineWidth(1)
    p.line(320, y_tot - 4, 566, y_tot - 4)
    y_tot -= 14
    
    p.setFont("Helvetica-Bold", 9.5)
    p.drawString(330, y_tot, "TOTAL GENERAL $:")
    p.drawRightString(566, y_tot, fmt_moneda(cotizacion.total))

    p.showPage()
    p.save()
    return response
# ==========================================
# CERTIFICADO DE ORIGEN
# ==========================================

@login_required
def imprimir_certificado_origen(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente
    
    vehiculo = None
    for item in cotizacion.items.all():
        if item.vehiculo:
            vehiculo = item.vehiculo
            break

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Certificado_Origen_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica", 8)

    p.drawCentredString(306, 750, 'EMPRESA DE DISTRIBUCION DE PRODUCTOS E INSUMOS "VENEZUELA PRODUCTIVA, C.A."')
    p.drawString(140, 715, factura.fecha_emision.strftime('%d/%m/%Y'))

    if vehiculo:
        p.drawString(50, 680, str(vehiculo.tipo or ''))
        p.drawString(180, 680, str(vehiculo.marca))
        p.drawString(380, 680, str(getattr(vehiculo, 'serie_version', '') or vehiculo.modelo))
        
        p.drawString(140, 650, str(vehiculo.anio))
        p.drawString(380, 650, str(vehiculo.serial_carroceria_niv or ''))
        
        p.drawString(140, 622, str(vehiculo.anio))
        p.drawString(380, 622, str(vehiculo.serial_carroceria_niv or ''))
        
        p.drawString(140, 595, str(vehiculo.serial_motor or ''))
        p.drawString(380, 595, str(vehiculo.serial_carroceria_niv or ''))
        
        p.drawString(120, 568, str(vehiculo.clase))
        p.drawString(280, 568, str(vehiculo.tipo))
        p.drawString(450, 568, str(vehiculo.uso))
        
        p.drawString(120, 542, str(vehiculo.uso))
        p.drawString(280, 542, str(vehiculo.color or ''))
        
        p.drawString(120, 515, str(vehiculo.num_puestos or ''))
        p.drawString(280, 515, str(vehiculo.num_ejes or ''))
        p.drawString(380, 515, str(vehiculo.peso_tara or ''))
        p.drawString(500, 515, str(vehiculo.capacidad_carga or ''))
        
        p.drawString(140, 488, str(vehiculo.puerto_entrada or 'LA GUAIRA'))
        p.drawString(380, 488, str(vehiculo.planilla_liquidacion or ''))
        
        p.drawString(180, 460, str(vehiculo.certificado_origen or ''))
        p.drawString(380, 460, str(vehiculo.factura_adquisicion or ''))
        
        p.drawString(380, 435, str(vehiculo.fecha_fin_convenio.strftime('%d/%m/%Y') if vehiculo.fecha_fin_convenio else '31/12/2026'))

    p.drawString(140, 355, "VENEZUELA PRODUCTIVA C.A.")
    p.drawString(450, 355, "G-20010522-4")
    
    p.drawString(140, 315, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(140, 290, str(cliente.nombre_razon_social))
    
    dir_texto = str(cliente.direccion or '')
    p.drawString(140, 265, dir_texto[:55])
    if len(dir_texto) > 55:
        p.drawString(140, 240, dir_texto[55:110])
        
    p.drawString(380, 190, "CARABOBO")
    p.drawString(520, 190, str(cliente.telefono or ''))

    p.showPage()
    p.save()
    return response

# ==========================================
# GESTIÓN DE FACTURAS Y COBRANZAS
# ==========================================

@login_required
def generar_factura(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    factura_previa = getattr(cotizacion, 'factura', None)
    
    if cotizacion.estado == 'F' and (not factura_previa or factura_previa.estado_pago != 'ANULADA'):
        messages.warning(request, 'Esta cotización ya ha sido facturada previamente y está activa.')
        return redirect('dashboard')
        
    vehiculos_disponibles = Vehiculo.objects.filter(
        Q(estado='Disponible') | 
        Q(id__in=cotizacion.items.filter(vehiculo__isnull=False).values_list('vehiculo_id', flat=True))
    )

    if request.method == 'POST':
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
                
                subtotal_base = Decimal('0.00')
                subtotal_exento = Decimal('0.00')
                
                for i in range(len(descripciones)):
                    vehiculo_id = vehiculos_ids[i] if vehiculos_ids[i] else None
                    vehiculo_obj = Vehiculo.objects.filter(id=vehiculo_id).first() if vehiculo_id else None
                        
                    aplica_iva = True if ivas[i] == 'on' else False
                    cant = int(cantidades[i])
                    precio_usd = Decimal(precios[i])
                    
                    subtotal_linea = cant * precio_usd
                    if aplica_iva:
                        subtotal_base += subtotal_linea
                    else:
                        subtotal_exento += subtotal_linea
                    
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
                
                porc_desc = cotizacion.porcentaje_descuento or Decimal('0.00')
                desc_base = subtotal_base * (porc_desc / Decimal('100.00'))
                desc_exento = subtotal_exento * (porc_desc / Decimal('100.00'))
                
                cotizacion.monto_descuento = desc_base + desc_exento
                base_imponible_usd = subtotal_base - desc_base
                monto_exento_usd = subtotal_exento - desc_exento

                cotizacion.base_imponible = base_imponible_usd
                cotizacion.monto_exento = monto_exento_usd
                cotizacion.impuesto_iva = base_imponible_usd * Decimal('0.16')
                cotizacion.total = cotizacion.base_imponible + cotizacion.monto_exento + cotizacion.impuesto_iva
                cotizacion.estado = 'F'
                cotizacion.save()

                factura = form.save(commit=False)
                factura.cotizacion = cotizacion
                factura.usuario = request.user
                
                factura.base_imponible = base_imponible_usd * tasa_cambio
                factura.monto_exento = monto_exento_usd * tasa_cambio
                factura.impuesto_iva = factura.base_imponible * Decimal('0.16')
                factura.total = factura.base_imponible + factura.monto_exento + factura.impuesto_iva
                
                factura.estado_pago = 'PENDIENTE' 
                factura.porcentaje_pago = 0
                factura.save()
                
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
def actualizar_pago_factura(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    if request.method == 'POST':
        estado = request.POST.get('estado_pago')
        porcentaje_str = request.POST.get('porcentaje_pago')
        
        if estado in dict(Factura.ESTADOS_PAGO).keys():
            factura.estado_pago = estado
            
            if porcentaje_str and str(porcentaje_str).strip():
                porcentaje = int(porcentaje_str)
            else:
                porcentaje = 0
                
            if factura.estado_pago == 'ANULADA':
                factura.porcentaje_pago = 0
                factura.base_imponible = Decimal('0.00')
                factura.impuesto_iva = Decimal('0.00')
                factura.monto_exento = Decimal('0.00')
                factura.total = Decimal('0.00')
                
                for item in factura.cotizacion.items.all():
                    if item.vehiculo:
                        item.vehiculo.estado = 'Disponible'
                        item.vehiculo.save()
                
                cotizacion = factura.cotizacion
                cotizacion.estado = 'P' 
                cotizacion.save()
            else:
                factura.porcentaje_pago = porcentaje
                if factura.porcentaje_pago >= 100:
                    factura.estado_pago = 'PAGADA'
                    factura.porcentaje_pago = 100
                elif factura.porcentaje_pago == 0 and factura.estado_pago != 'PENDIENTE':
                    factura.estado_pago = 'PENDIENTE'
                
            factura.save()
            messages.success(request, f'Estatus de la factura {factura.numero_factura} actualizado con éxito.')
            
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

    headers = [
        'Fecha Factura', 'Nro Factura', 'Nro Control', 'Estatus de Pago', 'Cliente', 
        'Cedula/Rif', 'Dirección', 'Telefonos', 'Descripción', 
        'Base Imponible', 'IVA 16%', 'EXENTO (E.)', 'Total General', 
        'Marca', 'Modelo', 'Color', 'Placa', 'Año', 'Clase', 'Tipo', 'Uso',
        'Serial Motor', 'Serial Carrocería NIV', 'Emitido Por'
    ]
    
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")

    facturas = Factura.objects.select_related('cotizacion__cliente', 'usuario').prefetch_related('cotizacion__items__vehiculo').order_by('numero_factura')
    
    diccionario_estados = {
        'PENDIENTE': 'Por Pagar',
        'PARCIAL': 'Pago Parcial',
        'PAGADA': 'Pagada',
        'ANULADA': 'Anulada'
    }
    
    for f in facturas:
        cliente = f.cotizacion.cliente
        item = f.cotizacion.items.first()
        v = item.vehiculo if item else None
        
        estatus_texto = diccionario_estados.get(getattr(f, 'estado_pago', 'PENDIENTE'), 'Por Pagar')
        nombre_usuario = f.usuario.username.title() if f.usuario else 'N/A'
        
        ws.append([
            f.fecha_emision.strftime('%d/%m/%Y'), f.numero_factura, getattr(f, 'numero_control', 'N/A'), estatus_texto, 
            cliente.nombre_razon_social, f"{cliente.tipo_documento}-{cliente.identificacion}", 
            cliente.direccion, cliente.telefono, item.descripcion if item else '',
             fmt_moneda(f.base_imponible), fmt_moneda(f.impuesto_iva), fmt_moneda(f.monto_exento), fmt_moneda(f.total),
            v.marca if v else '', v.modelo if v else '', v.color if v else '', v.placa if v else 'S/P', 
            v.anio if v else '', v.clase if v else '', v.tipo if v else '', v.uso if v else '',
            v.serial_motor if v else '', v.serial_carroceria_niv if v else '',
            nombre_usuario
        ])

    wb.save(response)
    return response

# ==========================================
# CERTIFICADO DE ORIGEN
# ==========================================

@login_required
def imprimir_certificado_origen(request, factura_id):
    factura = get_object_or_404(Factura, id=factura_id)
    cotizacion = factura.cotizacion
    cliente = cotizacion.cliente
    
    vehiculo = None
    for item in cotizacion.items.all():
        if item.vehiculo:
            vehiculo = item.vehiculo
            break

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Certificado_Origen_{factura.numero_factura}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica", 8)

    p.drawCentredString(306, 750, 'EMPRESA DE DISTRIBUCION DE PRODUCTOS E INSUMOS "VENEZUELA PRODUCTIVA, C.A."')
    p.drawString(140, 715, factura.fecha_emision.strftime('%d/%m/%Y'))

    if vehiculo:
        p.drawString(50, 680, str(vehiculo.tipo or ''))
        p.drawString(180, 680, str(vehiculo.marca))
        p.drawString(380, 680, str(getattr(vehiculo, 'serie_version', '') or vehiculo.modelo))
        
        p.drawString(140, 650, str(vehiculo.anio))
        p.drawString(380, 650, str(vehiculo.serial_carroceria_niv or ''))
        
        p.drawString(140, 622, str(vehiculo.anio))
        p.drawString(380, 622, str(vehiculo.serial_carroceria_niv or ''))
        
        p.drawString(140, 595, str(vehiculo.serial_motor or ''))
        p.drawString(380, 595, str(vehiculo.serial_carroceria_niv or ''))
        
        p.drawString(120, 568, str(vehiculo.clase))
        p.drawString(280, 568, str(vehiculo.tipo))
        p.drawString(450, 568, str(vehiculo.uso))
        
        p.drawString(120, 542, str(vehiculo.uso))
        p.drawString(280, 542, str(vehiculo.color or ''))
        
        p.drawString(120, 515, str(vehiculo.num_puestos or ''))
        p.drawString(280, 515, str(vehiculo.num_ejes or ''))
        p.drawString(380, 515, str(vehiculo.peso_tara or ''))
        p.drawString(500, 515, str(vehiculo.capacidad_carga or ''))
        
        p.drawString(140, 488, str(vehiculo.puerto_entrada or 'LA GUAIRA'))
        p.drawString(380, 488, str(vehiculo.planilla_liquidacion or ''))
        
        p.drawString(180, 460, str(vehiculo.certificado_origen or ''))
        p.drawString(380, 460, str(vehiculo.factura_adquisicion or ''))
        
        p.drawString(380, 435, str(vehiculo.fecha_fin_convenio.strftime('%d/%m/%Y') if vehiculo.fecha_fin_convenio else '31/12/2026'))

    p.drawString(140, 355, "VENEZUELA PRODUCTIVA C.A.")
    p.drawString(450, 355, "G-20010522-4")
    
    p.drawString(140, 315, f"{cliente.tipo_documento}-{cliente.identificacion}")
    p.drawString(140, 290, str(cliente.nombre_razon_social))
    
    dir_texto = str(cliente.direccion or '')
    p.drawString(140, 265, dir_texto[:55])
    if len(dir_texto) > 55:
        p.drawString(140, 240, dir_texto[55:110])
        
    p.drawString(380, 190, "CARABOBO")
    p.drawString(520, 190, str(cliente.telefono or ''))

    p.showPage()
    p.save()
    return response
