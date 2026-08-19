from django.apps import AppConfig

class FacturacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facturacion'

    def ready(self):
        # Importamos las señales al arrancar la aplicación
        import facturacion.signals
