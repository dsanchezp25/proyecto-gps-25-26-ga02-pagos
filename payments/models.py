from django.db import models
from django.conf import settings


class PaymentMethod(models.Model):
    """
    Representa un metdo  de pago tokenizado (tarjeta, etc.)
    de un usuario. No guardamos el CVV ni el PAN.
    """
    payment_method_id = models.CharField(max_length=100, unique=True, help_text="ID nuestro (ej. pm_abc)")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_methods")

    provider = models.CharField(max_length=50, default="stripe")

    # Referencia del PSP (ej. el 'pm_...' de Stripe)
    psp_ref = models.CharField(max_length=255, unique=True)

    brand = models.CharField(max_length=50, blank=True)
    last4 = models.CharField(max_length=4, blank=True)
    exp_mm = models.IntegerField(null=True, blank=True)
    exp_yy = models.IntegerField(null=True, blank=True)

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand} **** {self.last4} (Usuario: {self.user.username})"

    class Meta:
        ordering = ['-is_default', '-created_at']