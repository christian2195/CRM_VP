import os
import sys
import django
import openpyxl
from datetime import datetime

# 1. Configurar entorno
sys.path.append('/var/www/CRM_VP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_core.settings') 
django.setup()

from facturacion.models import Vehiculo

archivo_excel = 'BASE DE DATOS PARA FACTURACION 6 U-VANE AMBULANCIA R.xlsx'

print(f"Abriendo el archivo: {archivo_excel}...")
try:
    wb = openpyxl.load_workbook(archivo_excel, data_only=True)
    sheet = wb.active
except Exception as e:
    print(f"CRÍTICO: No se pudo abrir el Excel. Error: {e}")
    sys.exit(1)

exitos = 0
errores = 0

# Iteramos todas las filas
for idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
    # Truco de seguridad: Extendemos la fila con "Nones" para que nunca de "index out of range"
    fila_segura = list(row) + [None] * 10
    
    # Si la primera celda está vacía, saltamos la fila
    if not fila_segura[0]: 
        continue
        
    # Si la primera celda dice "MARCA" o "N°", sabemos que son los títulos, los saltamos
    if str(fila_segura[0]).strip().upper() in ['MARCA', 'N°', 'N']:
        continue

    print(f"--- Fila {idx} | Placa: {fila_segura[3]} | Motor: {fila_segura[14]} ---")

    try:
        # Volcado con los índices corregidos (-1 espacio a la izquierda)
        Vehiculo.objects.create(
            marca=fila_segura[0],
            modelo=fila_segura[1],
            color=fila_segura[2],
            placa=fila_segura[3],
            anio=fila_segura[4],
            clase=fila_segura[5],
            tipo=fila_segura[6],
            uso=fila_segura[7],
            transmision=fila_segura[8],
            tipo_combustible=fila_segura[9],
            num_puestos=fila_segura[10] if fila_segura[10] else 0,
            num_ejes=fila_segura[11] if fila_segura[11] else 0,
            peso_tara=fila_segura[12] if fila_segura[12] else 0,
            capacidad_carga=fila_segura[13] if fila_segura[13] else 0,
            serial_motor=fila_segura[14],
            serial_carroceria_niv=fila_segura[15],
            certificado_origen=fila_segura[16],
            servicio=fila_segura[17],
            puerto_entrada=fila_segura[18],
            fecha_liquidacion=fila_segura[19] if isinstance(fila_segura[19], datetime) else None,
            planilla_liquidacion=fila_segura[20],
            fecha_facturacion=fila_segura[21] if isinstance(fila_segura[21], datetime) else None,
            factura_adquisicion=fila_segura[22],
            refeciv=fila_segura[23],
            fecha_fin_convenio=fila_segura[24] if isinstance(fila_segura[24], datetime) else None
        )
        print("  [ÉXITO] Vehículo guardado correctamente.")
        exitos += 1
    except Exception as e:
        print(f"  [ERROR] Falló la inserción: {e}")
        errores += 1

print(f"\nRESUMEN FINAL: {exitos} guardados | {errores} errores.")
