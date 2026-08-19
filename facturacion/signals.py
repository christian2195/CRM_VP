from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ItemCotizacion

@receiver(post_save, sender=ItemCotizacion)
@receiver(post_delete, sender=ItemCotizacion)
def recalcular_totales(sender, instance, **kwargs):
    # Si el ítem tiene una cotización asociada, le decimos que recalcule
    if instance.cotizacion:
        instance.cotizacion.actualizar_totales()