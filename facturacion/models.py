from django.db import models
from decimal import Decimal

class Cliente(models.Model):
    TIPO_DOCUMENTO = [
        ('V', 'Venezolano'),
        ('E', 'Extranjero'),
        ('J', 'Jurídico'),
        ('G', 'Gubernamental'),
    ]
    tipo_documento = models.CharField(max_length=1, choices=TIPO_DOCUMENTO, default='V')
    identificacion = models.CharField(max_length=15, unique=True, verbose_name="Cédula/RIF")
    nombre_razon_social = models.CharField(max_length=150)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.tipo_documento}-{self.identificacion} | {self.nombre_razon_social}"

class Vehiculo(models.Model):
    # Datos Básicos
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='vehiculos')
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    placa = models.CharField(max_length=15, blank=True, null=True) # Puede estar en blanco si es nuevo
    anio = models.PositiveIntegerField(verbose_name="Año")
    color = models.CharField(max_length=30)
    
    # Ficha Técnica para Trámites
    clase = models.CharField(max_length=50, blank=True, null=True) 
    tipo = models.CharField(max_length=50, blank=True, null=True) 
    uso = models.CharField(max_length=50, blank=True, null=True)
    tipo_combustible = models.CharField(max_length=20, default='GASOLINA')
    transmision = models.CharField(max_length=20, blank=True, null=True)
    num_puestos = models.PositiveIntegerField(default=5)
    num_ejes = models.PositiveIntegerField(default=2)
    peso_tara = models.PositiveIntegerField(help_text="Peso en KG", blank=True, null=True)
    capacidad_carga = models.PositiveIntegerField(help_text="Capacidad en KG", blank=True, null=True)
    
    # Seriales (Únicos)
    serial_motor = models.CharField(max_length=100, unique=True)
    serial_carroceria = models.CharField(max_length=100, unique=True)
    serial_niv = models.CharField(max_length=100, unique=True)
    serie_version = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.marca} {self.modelo} - NIV: {self.serial_niv[-6:]}"

class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        ('B', 'Borrador'),
        ('E', 'Emitida'),
        ('F', 'Facturada'),
        ('A', 'Anulada'),
    ]
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Ahora la cotización se amarra al cliente, no a un solo vehículo
    cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, related_name='cotizaciones')
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='B')
    observaciones = models.TextField(blank=True, null=True)
    
    # Desglose de totales contables actualizados
    monto_exento = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    base_imponible = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    impuesto_iva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    def actualizar_totales(self):
        items = self.items.all()
        calc_exento = Decimal('0.00')
        calc_imponible = Decimal('0.00')
        tasa_iva = Decimal('0.16')
        
        for item in items:
            monto_item = item.cantidad * item.precio_unitario
            if item.aplica_iva:
                calc_imponible += monto_item
            else:
                calc_exento += monto_item
                
        calc_iva = calc_imponible * tasa_iva
        
        self.monto_exento = calc_exento
        self.base_imponible = calc_imponible
        self.impuesto_iva = calc_iva
        self.total = calc_exento + calc_imponible + calc_iva
        
        self.save(update_fields=['monto_exento', 'base_imponible', 'impuesto_iva', 'total'])

    def __str__(self):
        return f"Cotización #{self.id} - {self.cliente.nombre_razon_social}"

class ItemCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='items')
    # Permite asociar un vehículo específico a esta línea de la factura
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    aplica_iva = models.BooleanField(default=True)

class Factura(models.Model):
    cotizacion = models.OneToOneField(Cotizacion, on_delete=models.RESTRICT, related_name='factura')
    numero_factura = models.CharField(max_length=20, unique=True)
    numero_control = models.CharField(max_length=20, unique=True)
    fecha_emision = models.DateField()
    
    # Totales congelados
    monto_exento = models.DecimalField(max_digits=15, decimal_places=2)
    base_imponible = models.DecimalField(max_digits=15, decimal_places=2)
    impuesto_iva = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
    def save(self, *args, **kwargs):
        if self._state.adding:
            self.cotizacion.estado = 'F'
            self.cotizacion.save()
            # Congelar montos desde la cotización
            self.monto_exento = self.cotizacion.monto_exento
            self.base_imponible = self.cotizacion.base_imponible
            self.impuesto_iva = self.cotizacion.impuesto_iva
            self.total = self.cotizacion.total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Factura {self.numero_factura} (Control: {self.numero_control})"