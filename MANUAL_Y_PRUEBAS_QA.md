# MANUAL DE USUARIO Y PROTOCOLO DE PRUEBAS (QA)
**Sistema:** CRM de Facturación y Control de Inventario Automotriz  
**Organización:** EMVEPRO C.A. (Empresa Venezuela Productiva C.A.)  
**Elaborado por:** Coordinación de Infraestructura TI / Gerencia de Tecnología de la Información y Comunicación  
**Fecha:** Octubre 2026  

---

## PARTE 1: MANUAL OPERATIVO DE USUARIO

### 1. Acceso y Panel de Control (Dashboard)
Al iniciar sesión con sus credenciales institucionales, ingresará al **Panel de Control Operativo**, donde visualizará:
* **Métricas Rápidas:** Total de cotizaciones activas y presupuestos pendientes por facturar.
* **Bandeja de Acción Inmediata:** Listado de cotizaciones pendientes con acceso directo para descargar el PDF del presupuesto o convertirlo en factura fiscal.
* **Últimas Facturas Emitidas:** Historial reciente con selectores desplegables para imprimir en **Bolívares (Bs.)**, **Dólares (USD)** o emitir el **Certificado de Origen**.

---

### 2. Gestión de Clientes
* **Ubicación:** Menú superior / lateral $\rightarrow$ *Clientes*.
* **Crear Cliente:** Haga clic en **"+ Nuevo Cliente"**, seleccione el tipo de documento (`V`, `E`, `J`, `G`), ingrese el número de Cédula/RIF, Razón Social, Dirección Fiscal, Teléfono y Correo.
* **Expediente del Cliente:** En el listado general, haga clic en el botón amarillo del ojo (**Ver documentos asociados**) para abrir una ventana emergente con todas las cotizaciones, facturas y certificados emitidos a ese cliente. Use el botón del lápiz para actualizar sus datos.

---

### 3. Gestión de Inventario Vehicular
* **Ubicación:** *Inventario* $\rightarrow$ *Lista de Vehículos*.
* **Estados del Vehículo:**
  * **Disponible (Verde):** Unidad en stock lista para ser asociada a presupuestos o facturas.
  * **Apartado (Amarillo):** Unidad reservada temporalmente en una cotización.
  * **Vendido (Rojo/Gris):** Unidad facturada y descontada del stock disponible.
* **Carga y Exportación Masiva:**
  * Use **"Exportar Excel"** para descargar la sábana completa del parque automotor.
  * Use **"Importar Excel"** subiendo el formato `.xlsx` oficial. El sistema actualizará automáticamente los vehículos cuyo **Serial NIV** ya exista y creará los nuevos.

---

### 4. Emisión y Control de Cotizaciones (Presupuestos)
* **Ubicación:** *Cotizaciones* $\rightarrow$ **"+ Nueva Cotización"**.
* **Moneda Base:** Todos los presupuestos se cargan en **Dólares ($)**.
* **Pasos para emitir:**
  1. Seleccione el **Cliente**, la **Fecha de Emisión** y los **Días de Validez**.
  2. En el detalle, seleccione un **Vehículo Disponible** (la descripción se autocompletará con Marca, Modelo y Año) o escriba un servicio/ítem manual (ej. *Placas*, *Flete*).
  3. Ingrese la **Cantidad**, el **Precio Unitario ($)** y marque o desmarque la casilla **IVA (16%)** según corresponda (los ítems desmarcados se sumarán como *Monto Exento*).
  4. Verifique o edite las **Condiciones y Notas Legales** en la parte inferior izquierda.
  5. Presione **"Emitir Cotización"**.
* **Impresión y Anulación:**
  * Desde el *Historial de Cotizaciones*, presione el botón **PDF** para generar el presupuesto con hoja membretada oficial, código QR de validación y espacio para firmas (*Revisado por* / *Autorizado por*).
  * Si la venta no procede, presione **"Anular"**. El presupuesto pasará a la pestaña *Historial de Anuladas* y el vehículo volverá automáticamente a estado **Disponible**.

---

### 5. Emisión de Facturas Fiscales y Certificados de Origen
* **Paso previo:** Toda factura nace de una cotización aprobada. Vaya al *Dashboard* o a *Gestión de Cotizaciones* y presione el botón amarillo **"Facturar"**.
* **Pasos para facturar:**
  1. Ingrese el **N° de Factura**, **N° de Control** y la **Tasa de Cambio BCV (Bs./$)** del día.
  2. Verifique las líneas de detalle (puede ajustar precios, agregar ítems o cambiar unidades antes de emitir) y edite las **Coletillas Fiscales** si es necesario.
  3. Verifique en pantalla el cálculo automático convertido a Bolívares y presione **"Emitir Factura"**. Al hacerlo, los vehículos asociados pasan automáticamente a estado **Vendido**.
* **Formatos de Impresión (Blanco y Negro para Formas Preimpresas):**
  * **Menú Bs.:** *Forma Libre (Bs.)*, *Institucional Con SAP (Bs.)*, *Institucional Sin SAP (Bs.)*.
  * **Menú USD:** *Forma Libre ($)*, *Institucional Con SAP ($)*, *Institucional Sin SAP ($)*.
  * **Certificado de Origen (Ícono Verde):** Genera el documento con coordenadas milimétricas para imprimir sobre el formato físico de seguridad.

---

### 6. Estado Financiero y Control de Cobranza
* **Ubicación:** *Estado Financiero*.
* **Actualización de Pagos:**
  1. En la tabla de *Facturas Activas*, haga clic en el botón amarillo **"Cobro"**.
  2. Seleccione el estatus: **Por Pagar (0%)**, **Pago Parcial (1% - 99%)** o **Pagada (100%)** y guarde los cambios.
* **Anulación Fiscal de Facturas:**
  * Si dentro del modal de **"Cobro"** selecciona la opción **"Anular Factura"**, los montos fiscales de esa factura pasan a `0,00`, la factura se mueve a la pestaña *Historial de Anuladas*, **los vehículos regresan automáticamente a estado Disponible** y la cotización original vuelve a estado *Pendiente* por si requiere refacturarse.

---
---

## PARTE 2: CUESTIONARIO DE CHEQUEO Y VALIDACIÓN (CHECKLIST QA)

**Instrucciones para el Evaluador:** Ejecute cada una de las pruebas descritas a continuación en el entorno del sistema. Marque con una **X** si la prueba fue exitosa (**Cumple**) o si presentó algún inconveniente (**No Cumple**), y anote cualquier detalle en la columna de observaciones.

### Datos del Evaluador
* **Nombre y Apellido:** ____________________________________________________
* **Cargo / Departamento:** _________________________________________________
* **Fecha de Prueba:** ____ / ____ / 2026

---

### Módulo 1: Clientes e Inventario Vehicular
| ID | Caso de Prueba / Acción a Realizar | Resultado Esperado | Cumple | No Cumple | Observaciones |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **1.1** | Registrar un nuevo cliente Jurídico (`J` o `G`) y uno Natural (`V`). | El sistema guarda ambos registros y los muestra en el directorio sin errores. | [ ] | [ ] | |
| **1.2** | Editar el teléfono o dirección de un cliente existente. | Los cambios se actualizan y persisten correctamente. | [ ] | [ ] | |
| **1.3** | Registrar un vehículo manualmente con todos sus seriales (NIV, Motor) y datos de aduana. | El vehículo aparece en la lista con estatus inicial **Disponible**. | [ ] | [ ] | |
| **1.4** | Descargar el inventario en Excel y probar el buscador por placa o serial NIV. | El archivo `.xlsx` descarga completo y el buscador filtra en tiempo real. | [ ] | [ ] | |

---

### Módulo 2: Presupuestos y Cotizaciones
| ID | Caso de Prueba / Acción a Realizar | Resultado Esperado | Cumple | No Cumple | Observaciones |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **2.1** | Crear una cotización con 1 vehículo (con IVA) y 1 ítem adicional sin IVA (exento). | El resumen inferior calcula en vivo la Base Imponible, Exento, IVA (16%) y Total en `$` con formato `0.000,00`. | [ ] | [ ] | |
| **2.2** | Modificar el texto de "Condiciones y Notas Legales" antes de guardar la cotización. | La cotización se guarda y al abrir el PDF se muestran las condiciones personalizadas. | [ ] | [ ] | |
| **2.3** | Abrir el PDF de la cotización generada. | Se visualiza la hoja membretada a color, el código QR en el pie de página y el espacio libre para firmas en *Revisado por* y *Autorizado por*. | [ ] | [ ] | |
| **2.4** | Anular una cotización pendiente desde el listado. | La cotización pasa a la pestaña *Historial de Anuladas* y sus vehículos vuelven a estar **Disponibles**. | [ ] | [ ] | |

---

### Módulo 3: Facturación y Formatos de Impresión PDF
| ID | Caso de Prueba / Acción a Realizar | Resultado Esperado | Cumple | No Cumple | Observaciones |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **3.1** | Facturar una cotización ingresando N° de Factura, N° de Control y Tasa BCV. | El sistema convierte los montos a Bolívares exactamente a la tasa indicada y cambia el vehículo a **Vendido**. | [ ] | [ ] | |
| **3.2** | Imprimir **Factura Forma Libre (Bs. y USD)**. | Documento en blanco y negro, sin fondo, sin código QR, y con la descripción alineada sin pisar la columna de IVA. | [ ] | [ ] | |
| **3.3** | Imprimir **Factura Institucional Con SAP (Bs. y USD)**. | Cuadrícula en blanco y negro perfectamente encuadrada incluyendo la columna `CÓD. SAP` y todas las especificaciones del vehículo. | [ ] | [ ] | |
| **3.4** | Imprimir **Factura Institucional Sin SAP (Bs. y USD)**. | Cuadrícula en blanco y negro sin la columna SAP, con el texto de descripción completo dentro de su celda sin desbordarse. | [ ] | [ ] | |
| **3.5** | Imprimir **Certificado de Origen**. | Los datos del vehículo y del comprador coinciden con las casillas del formato físico preimpreso. | [ ] | [ ] | |

---

### Módulo 4: Estado Financiero, Cobranza y Auditoría
| ID | Caso de Prueba / Acción a Realizar | Resultado Esperado | Cumple | No Cumple | Observaciones |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **4.1** | Actualizar el cobro de una factura a **Pago Parcial (50%)** y luego a **Pagada (100%)**. | La barra de progreso y la etiqueta cambian de color y porcentaje correctamente. | [ ] | [ ] | |
| **4.2** | **Anular una Factura** desde el modal de Cobro. | La factura pasa a la pestaña *Anuladas* con monto `Bs. 0,00`, el vehículo regresa a **Disponible** en el inventario y la cotización vuelve a estar *Pendiente*. | [ ] | [ ] | |
| **4.3** | Descargar el **Consolidado Serie A en Excel** desde el Historial de Facturas. | El archivo `.xlsx` muestra todas las facturas, estatus de pago, montos formateados y usuario emisor. | [ ] | [ ] | |

---

### Conformidad de la Prueba

**Resultado General de la Evaluación:**  
[ ] APROBADO SIN OBSERVACIONES  
[ ] APROBADO CON OBSERVACIONES MENORES  
[ ] REQUIERE CORRECCIONES ANTES DE PASE DEFINITIVO  

**Comentarios Finales del Usuario Evaluador:**
____________________________________________________________________________________
____________________________________________________________________________________
____________________________________________________________________________________

<br><br>

_______________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; _______________________________  
**Firma del Usuario Evaluador** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Por Coordinación de Infraestructura TI**
