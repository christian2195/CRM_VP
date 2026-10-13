# CONTEXT.md — Sistema de Facturación e Inventario Automotriz (CRM EMVEPRO C.A.)

**Organización:** EMVEPRO C.A. / VENEZUELA PRODUCTIVA C.A.  
**Departamento:** Gerencia de Tecnología de la Información y Comunicación  
**Stack Tecnológico:** Python 3.12+, Django 4.2+, ReportLab (Generación PDF), OpenPyXL (Procesamiento Excel), HTML5/Bootstrap 5 (Frontend), Gunicorn/Nginx.

## 1. Arquitectura Central y Lógica de Negocio
El sistema gestiona el ciclo de vida completo de la comercialización de vehículos institucionales, desde la cotización en divisas hasta la facturación fiscal bimonetaria y la emisión de certificados de origen sobre formatos preimpresos.

### 1.1 Lógica Bimonetaria (USD / VES)
* **Origen (Cotizaciones):** Los presupuestos y líneas de detalle se crean y almacenan utilizando el valor nominal en Dólares (USD).
* **Transición (Facturación):** Al convertir una cotización en factura, el usuario ingresa la Tasa de Cambio oficial (BCV). El sistema calcula y almacena matemáticamente los totales (Base Imponible, Exento, IVA, Total General) en Bolívares (VES).
* **Visualización:** Los reportes financieros y el historial de facturación muestran ambas monedas y estandarizan los montos al formato regional venezolano (`10.045.812,00`).

### 1.2 Máquina de Estados del Inventario
El modelo de `Vehiculo` opera bajo una transición de estados estricta para garantizar la integridad del stock:
1. **Disponible:** Unidad lista para la venta. Visible en los selectores de creación de cotizaciones.
2. **Apartado:** Estado asignado automáticamente al vincular la unidad a una Cotización guardada. Se oculta de nuevas cotizaciones para evitar doble venta.
3. **Vendido:** Estado definitivo asignado al emitir la Factura. La unidad se descuenta formalmente del inventario activo.
4. **Anulado:** Al anular una cotización, los vehículos apartados retornan automáticamente a estado *Disponible*.

---

## 2. Módulos del Sistema

### 2.1 Módulo de Cotizaciones
* Asignación de clientes y establecimiento de días de validez.
* Inclusión de ítems combinados (vehículos del inventario + servicios/ítems de texto libre).
* Generación de documento PDF formato "Presupuesto VP" con términos comerciales (Incoterm DAP, esquema de pagos 50/50, garantía) y código QR de verificación institucional.

### 2.2 Módulo de Facturación
* Generación de formatos de salida PDF (ReportLab) tanto en Bolívares (Bs.) como en Dólares ($):
  * **Factura Institucional (Con SAP):** Detalle completo incluyendo Código SAP y especificaciones vehiculares.
  * **Factura Institucional (Sin SAP):** Diseño alternativo sin la columna de código interno.
  * **Factura Forma Libre:** Formato fiscal estándar con desglose de alícuotas IVA.
* Inyección de coletillas dinámicas y condiciones legales.

### 2.3 Módulo de Gestión de Inventario (Vehículos)
* Registro detallado de especificaciones técnicas (Marca, Modelo, Año, NIV/Carrocería, Motor, Tara, Capacidad de Carga, Ejes, Puestos, Serie/Versión).
* Registro de datos de importación (Puerto, Planilla, Certificado de Origen).
* Sistema de Carga Masiva (Importación) y Exportación vía archivos Excel (`.xlsx`), actualizando unidades existentes basándose en el número de NIV.

### 2.4 Control Financiero y Cobranza
* Dashboard de conciliación con sumatorias globales de Base Imponible, IVA recaudado y monto pendiente por facturar.
* Control de estatus de pago por factura (Por Pagar, Pago Parcial, Pagada, Anulada) con actualización de porcentaje de progreso (0-100%).

### 2.5 Emisión de Certificados de Origen
* Motor de impresión preciso diseñado para papel de seguridad preimpreso.
* Mapeo de coordenadas estrictas en puntos (pt) basadas en dimensiones físicas para asegurar que los datos encajen exactamente en las casillas del formulario físico.

---

## 3. Comandos y Tareas Frecuentes

* **Reiniciar servicio Gunicorn:**
  ```bash
sudo systemctl restart gunicorn

Aplicar migraciones de base de datos:

Bash
python manage.py migrate
Recopilar archivos estáticos:

Bash
python manage.py collectstatic --noinput
  

